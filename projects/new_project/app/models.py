from sqlalchemy import Column, Integer, String
from .database import Base

class User(Base):
    """
    A simple User model to demonstrate SQLAlchemy integration.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)