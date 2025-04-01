
import sys
import json
import importlib.util
import time
import os
import traceback

def load_function(code_path):
    # Load the function module
    try:
        spec = importlib.util.spec_from_file_location("function_module", code_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.handler
    except Exception as e:
        error_message = f"Error loading function: {str(e)}\n{traceback.format_exc()}"
        sys.stderr.write(error_message)
        raise

def main():
    try:
        # Get event data from stdin
        raw_input = sys.stdin.read()
        if not raw_input:
            sys.stderr.write("No input received from stdin")
            sys.exit(1)
            
        event_data = json.loads(raw_input)
        
        # Create a simple context object
        context = {
            "function_name": os.environ.get("FUNCTION_NAME", "unknown"),
            "request_id": os.environ.get("REQUEST_ID", "unknown"),
            "start_time": time.time()
        }
        
        # Handle sleep parameter for long timeout tests
        if 'sleep' in event_data and isinstance(event_data['sleep'], (int, float)):
            time.sleep(float(event_data['sleep']))
        
        # Load and execute the function
        try:
        # Check if function.py exists in the expected location
            if not os.path.exists("/function/function.py"):
                    error_message = "Error: /function/function.py not found. Directory contents: " + str(os.listdir("/function"))
                    sys.stderr.write(error_message)
                    sys.exit(1)
                    
            handler = load_function("/function/function.py")
            result = handler(event_data, context)
                            
                            # Output the result as JSON
            sys.stdout.write(json.dumps(result))
        except Exception as e:
            error_message = f"Error executing function: {str(e)}\n{traceback.format_exc()}"
            sys.stderr.write(error_message)
            sys.exit(1)
    except Exception as e:
        # Catch any uncaught exceptions
        error_message = f"Unhandled error in entrypoint: {str(e)}\n{traceback.format_exc()}"
        sys.stderr.write(error_message)
        sys.exit(1)

if __name__ == "__main__":
    main()
