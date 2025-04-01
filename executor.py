from fastapi import APIRouter, HTTPException, Depends, Body, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, Optional
import time
import json
from datetime import datetime
import asyncio

# Import dependencies
from main import get_db, Function
from docker_manager import DockerManager

router = APIRouter()
docker_manager = DockerManager()

class FunctionExecutionRequest(BaseModel):
    event: Dict[str, Any]

class FunctionExecutionResponse(BaseModel):
    function_id: int
    execution_id: str
    start_time: datetime
    end_time: datetime
    duration_ms: int
    result: Dict[str, Any]
    error: bool
    logs: Optional[str] = None

async def execute_with_timeout(func_coro, timeout: int):
    """Helper function to enforce execution timeout using asyncio"""
    try:
        return await asyncio.wait_for(func_coro, timeout=timeout / 1000)
    except asyncio.TimeoutError:
        return {"error": True, "logs": "Function execution timed out"}

@router.post("/api/functions/{route_path:path}/execute", response_model=FunctionExecutionResponse)
async def execute_function(
    route_path: str, 
    execution_request: FunctionExecutionRequest = Body(...),
    db: Session = Depends(get_db)
):
    # Ensure route_path starts with "/"
    if not route_path.startswith('/'):
        route_path = '/' + route_path
    
    # Find function in the database
    function = db.query(Function).filter(Function.route == route_path).first()
    if function is None:
        raise HTTPException(status_code=404, detail="Function not found")
    
    if not function.active:
        raise HTTPException(status_code=400, detail="Function is not active")
    
    start_time = datetime.utcnow()
    execution_id = f"exec-{int(time.time())}"
    
    # Run function with timeout handling
    result = await execute_with_timeout(
        docker_manager.execute_function(
            function_id=str(function.id),
            function_name=function.name,
            language=function.language,
            code=function.code,
            event=execution_request.event,
            timeout=function.timeout
        ),
        timeout=function.timeout
    )

    end_time = datetime.utcnow()
    duration_ms = int((end_time - start_time).total_seconds() * 1000)
    
    return FunctionExecutionResponse(
        function_id=function.id,
        execution_id=execution_id,
        start_time=start_time,
        end_time=end_time,
        duration_ms=duration_ms,
        result=result.get("result", {}),
        error=result.get("error", False),
        logs=result.get("logs", None)
    )
