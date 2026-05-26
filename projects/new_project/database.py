from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

from config import settings

# Determine the database URL based on the environment
# For testing, we might use an in-memory SQLite database
# For development/production, use the configured PostgreSQL URL
if settings.ENVIRONMENT == "testing":
    SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool, # Required for in-memory SQLite to keep it alive
    )
else:
    SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()