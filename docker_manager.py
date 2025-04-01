import docker
import os
import json
import tempfile
import uuid
from typing import Dict, Any, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DockerManager:
    def __init__(self):
        """Initialize Docker client and ensure base images exist"""
        self.client = docker.from_env()
        self.containers = {}  # Track running containers
        
        # Ensure base images exist
        self._ensure_base_images()
    
    def _ensure_base_images(self):
        """Ensure necessary base images exist, build them if they don't"""
        # Define supported languages and their base images
        self.supported_languages = {
            "python": "python-runner",
            "javascript": "node-runner"
        }
        
        # Check if images exist, build if they don't
        for lang, image_name in self.supported_languages.items():
            try:
                self.client.images.get(image_name)
                logger.info(f"Base image for {lang} ({image_name}) already exists")
            except docker.errors.ImageNotFound:
                logger.info(f"Building base image for {lang} ({image_name})")
                self._build_base_image(lang, image_name)
    
    def _build_base_image(self, language: str, image_name: str):
        """Build a base Docker image for a specific language"""
        # Use a persistent directory for Docker build context
        base_dir = os.path.dirname(os.path.abspath(__file__))
        runners_dir = os.path.join(base_dir, "docker-runners")
        
        if language == "python":
            # Build Python runner image
            runner_dir = os.path.join(runners_dir, "python-runner")
            self.client.images.build(path=runner_dir, tag=image_name)
            logger.info(f"Built Python base image: {image_name}")
            
        elif language == "javascript":
            # Build JavaScript runner image
            runner_dir = os.path.join(runners_dir, "javascript-runner")
            self.client.images.build(path=runner_dir, tag=image_name)
            logger.info(f"Built JavaScript base image: {image_name}")
    
    async def execute_function(
        self, 
        function_id: str, 
        function_name: str, 
        language: str, 
        code: str, 
        event: Dict[str, Any], 
        timeout: int = 30000  # Timeout in milliseconds
    ) -> Dict[str, Any]:
        """
        Execute a serverless function in a Docker container
        
        Args:
            function_id: Unique identifier for the function
            function_name: Name of the function
            language: Programming language (python, javascript)
            code: Function code as a string
            event: Event data to pass to the function
            timeout: Function timeout in milliseconds
        
        Returns:
            Function execution result
        """
        if language not in self.supported_languages:
            raise ValueError(f"Unsupported language: {language}")
        
        # Create a unique container name
        container_id = str(uuid.uuid4())
        container_name = f"function-{function_id}-{container_id[:8]}"
        
        # Create a temporary directory for function code
        with tempfile.TemporaryDirectory() as temp_dir:
            # Write function code to file
            if language == "python":
                code_file = os.path.join(temp_dir, "function.py")
            elif language == "javascript":
                code_file = os.path.join(temp_dir, "function.js")
            
            with open(code_file, "w") as f:
                f.write(code)
            
            # Convert timeout to seconds for Docker
            timeout_seconds = timeout / 1000
            
            try:
                # Run the container with the function
                logger.info(f"Executing function {function_name} in container {container_name}")
                
                # Convert event data to JSON
                event_json = json.dumps(event)
                
                # Run the container with appropriate environment variables
                container = self.client.containers.run(
                    image=self.supported_languages[language],
                    name=container_name,
                    detach=True,  # Run in background
                    environment={
                        "FUNCTION_NAME": function_name,
                        "REQUEST_ID": container_id,
                    },
                    volumes={
                        temp_dir: {'bind': '/function', 'mode': 'rw'}
                    },
                    stdin_open=True,
                    mem_limit="512m",  # Limit memory usage
                    cpu_count=4,  # Limit CPU usage
                )
                
                # Keep track of the container
                self.containers[container_id] = container
                
                # Send input data to container
                socket = container.attach_socket(
                    params={'stdin': 1, 'stream': 1}
                )
                os.write(socket.fileno(), event_json.encode('utf-8'))
                socket.close()
                
                # Wait for container to finish with timeout
                result = container.wait(timeout=timeout_seconds)
                
                # Get container logs (function output)
                logs = container.logs(stdout=True, stderr=False).decode('utf-8')
                stderr_logs = container.logs(stdout=False, stderr=True).decode('utf-8')
                
                # Check exit code
                exit_code = result['StatusCode']
                if exit_code != 0:
                    logger.error(f"Function execution failed with exit code {exit_code}")
                    logger.error(f"Error logs: {stderr_logs}")
                    return {
                        "error": True,
                        "message": f"Function execution failed with exit code {exit_code}",
                        "logs": stderr_logs
                    }
                
                # Parse output
                try:
                    output = json.loads(logs)
                    return {
                        "error": False,
                        "result": output
                    }
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse function output as JSON: {logs}")
                    return {
                        "error": True,
                        "message": "Function did not return valid JSON",
                        "logs": logs
                    }
                
            except docker.errors.ContainerError as e:
                logger.error(f"Container error: {str(e)}")
                return {
                    "error": True,
                    "message": f"Container error: {str(e)}"
                }
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                logger.error(f"Execution error: {str(e)}\n{error_trace}")
                return {
                    "error": True,
                    "message": f"Execution error: {str(e)}",
                    "logs": error_trace
                }
            finally:
                # Clean up container
                try:
                    if container_id in self.containers:
                        container = self.containers[container_id]
                        container.remove(force=True)
                        del self.containers[container_id]
                        logger.info(f"Removed container {container_name}")
                except Exception as e:
                    logger.error(f"Failed to remove container: {str(e)}")
    
    def cleanup(self):
        """Clean up all containers"""
        for container_id, container in self.containers.items():
            try:
                container.remove(force=True)
                logger.info(f"Removed container {container.name}")
            except Exception as e:
                logger.error(f"Failed to remove container {container.name}: {str(e)}")
        
        self.containers = {}