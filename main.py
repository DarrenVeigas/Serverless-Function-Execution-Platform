from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import Optional, Dict, List
import os
from datetime import datetime
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
print(DATABASE_URL)
# SQLAlchemy setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Function Model
class Function(Base):
    __tablename__ = "functions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    route = Column(String(200), unique=True, index=True, nullable=False)
    language = Column(String(50), nullable=False)
    code = Column(Text, nullable=False)
    timeout = Column(Integer, default=30000)  # 30 seconds in milliseconds
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    active = Column(Boolean, default=True)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic models for API
class FunctionBase(BaseModel):
    name: str
    route: str
    language: str
    code: str
    timeout: Optional[int] = 30000
    active: Optional[bool] = True

class FunctionCreate(FunctionBase):
    pass

class FunctionUpdate(BaseModel):
    name: Optional[str] = None
    route: Optional[str] = None
    language: Optional[str] = None
    code: Optional[str] = None
    timeout: Optional[int] = None
    active: Optional[bool] = None

class FunctionInDB(FunctionBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize FastAPI
app = FastAPI(title="Serverless Function Execution Platform")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Serverless Function Execution Platform API"}

# CRUD API Endpoints
@app.get("/api/functions/", response_model=List[FunctionInDB])
def get_all_functions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    functions = db.query(Function).offset(skip).limit(limit).all()
    return functions

@app.get("/api/functions/{function_id}", response_model=FunctionInDB)
def get_function_by_id(function_id: int, db: Session = Depends(get_db)):
    function = db.query(Function).filter(Function.id == function_id).first()
    if function is None:
        raise HTTPException(status_code=404, detail="Function not found")
    return function

@app.get("/api/functions/route/{route:path}", response_model=FunctionInDB)
def get_function_by_route(route: str, db: Session = Depends(get_db)):
    # Ensure route starts with /
    if not route.startswith('/'):
        route = '/' + route
    
    function = db.query(Function).filter(Function.route == route).first()
    if function is None:
        raise HTTPException(status_code=404, detail="Function not found")
    return function

@app.post("/api/functions/", response_model=FunctionInDB, status_code=201)
def create_function(function: FunctionCreate, db: Session = Depends(get_db)):
    # Check if function with same name or route already exists
    existing_function = db.query(Function).filter(
        (Function.name == function.name) | (Function.route == function.route)
    ).first()
    
    if existing_function:
        raise HTTPException(
            status_code=400, 
            detail="A function with this name or route already exists"
        )
    
    # Ensure route starts with /
    if not function.route.startswith('/'):
        function.route = '/' + function.route
    
    db_function = Function(**function.dict())
    db.add(db_function)
    db.commit()
    db.refresh(db_function)
    return db_function

@app.put("/api/functions/{function_id}", response_model=FunctionInDB)
def update_function(function_id: int, function: FunctionUpdate, db: Session = Depends(get_db)):
    db_function = db.query(Function).filter(Function.id == function_id).first()
    if db_function is None:
        raise HTTPException(status_code=404, detail="Function not found")
    
    # Check for name/route conflicts if those fields are being updated
    if function.name or function.route:
        conflict_query = db.query(Function).filter(Function.id != function_id)
        
        if function.name:
            conflict_query = conflict_query.filter(Function.name == function.name)
        
        if function.route:
            # Ensure route starts with /
            if function.route and not function.route.startswith('/'):
                function.route = '/' + function.route
            
            conflict_query = conflict_query.filter(Function.route == function.route)
        
        if conflict_query.first():
            raise HTTPException(
                status_code=400, 
                detail="The new name or route conflicts with an existing function"
            )
    
    # Update function fields
    function_data = function.dict(exclude_unset=True)
    for key, value in function_data.items():
        setattr(db_function, key, value)
    
    db_function.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_function)
    return db_function

@app.delete("/api/functions/{function_id}", status_code=204)
def delete_function(function_id: int, db: Session = Depends(get_db)):
    db_function = db.query(Function).filter(Function.id == function_id).first()
    if db_function is None:
        raise HTTPException(status_code=404, detail="Function not found")
    
    db.delete(db_function)
    db.commit()
    return None

# Import the executor router
from executor import router as executor_router

# Include the executor router
app.include_router(executor_router)

# Shutdown event to clean up resources
@app.on_event("shutdown")
def shutdown_event():
    from executor import docker_manager
    docker_manager.cleanup()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)