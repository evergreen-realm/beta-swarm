import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database connection URL from environment variable
# Example: "postgresql://user:password@host:port/database_name"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/mydatabase")

# Create a SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create a SessionLocal class
# Each instance of SessionLocal will be a database session
# The 'autocommit=False' means that the session will not commit changes automatically
# The 'autoflush=False' means that the session will not flush changes to the database automatically
# The 'bind=engine' connects the session to the database engine
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models
Base = declarative_base()

# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()