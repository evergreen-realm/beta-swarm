from fastapi import FastAPI
from app.routers import router

app = FastAPI(title="Test App", version="1.0")

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.0"}

app.include_router(router)
