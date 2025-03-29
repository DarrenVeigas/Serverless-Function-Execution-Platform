import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

# Read DB credentials from .env
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = os.getenv("MYSQL_PORT")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

# MySQL Database URL
DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"

# Create the engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class FunctionModel(Base):
    __tablename__ = "functions"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    route = Column(String(255), unique=True, nullable=False)
    language = Column(String(50), nullable=False)
    timeout = Column(Float, default=5.0)  # Default timeout 5 seconds

# Create tables in MySQL
Base.metadata.create_all(bind=engine)
