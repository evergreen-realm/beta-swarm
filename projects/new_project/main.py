from fastapi import FastAPI
from contextlib import asynccontextmanager

from database import create_all_tables
from routers import items

# Define an asynchronous context manager for application lifecycle events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager for application startup and shutdown events.
    On startup, it ensures all database tables are created.
    """
    print("Application startup: Creating database tables...")
    create_all_tables()
    print("Application startup complete.")
    yield
    print("Application shutdown: No specific shutdown tasks.")

# Initialize the FastAPI application with the lifespan context manager
app = FastAPI(
    title="Generic FastAPI Backend",
    description="A production-ready FastAPI backend with SQLAlchemy and PostgreSQL, demonstrating basic CRUD operations for an 'Item' resource.",
    version="1.0.0",
    lifespan=lifespan,
)

# Include the API router for items
app.include_router(items.router)

@app.get("/", tags=["root"])
async def read_root():
    """
    Root endpoint to verify the API is running.
    """
    return {"message": "Welcome to the Generic FastAPI Backend! Visit /docs for API documentation."}

# To run this application locally:
# 1. Ensure you have PostgreSQL running and accessible.
# 2. Create a database, e.g., 'fastapi_db'.
# 3. Set the SQLALCHEMY_DATABASE_URL environment variable (e.g., in a .env file or directly).
#    Example: export SQLALCHEMY_DATABASE_URL="postgresql://user:password@localhost:5432/fastapi_db"
# 4. Install dependencies: pip install -r requirements.txt
# 5. Run Uvicorn: uvicorn main:app --reload --host 0.0.0.0 --port 8000
# 6. Access the API at http://localhost:8000 and documentation at http://localhost:8000/docs