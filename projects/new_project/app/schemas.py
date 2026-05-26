from pydantic import BaseModel, EmailStr

# Base Pydantic model for User properties
class UserBase(BaseModel):
    name: str
    email: EmailStr

# Pydantic model for creating a User (inherits from UserBase)
class UserCreate(UserBase):
    pass

# Pydantic model for updating a User (inherits from UserBase, all fields optional)
class UserUpdate(UserBase):
    name: str | None = None
    email: EmailStr | None = None

# Pydantic model for reading a User (includes id, and config for ORM mode)
class User(UserBase):
    id: int

    class Config:
        orm_mode = True # Enable ORM mode