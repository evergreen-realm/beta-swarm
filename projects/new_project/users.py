from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import select
from database import get_session
from schemas import UserCreate, UserUpdate

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_db():
    db = get_session()
    try:
        yield db
    finally:
        db.close()

async def get_user(db, user_id: int):
    query = select(User).where(User.id == user_id)
    return (await db.execute(query)).scalar()

async def authenticate_user(db, username: str, password: str):
    query = select(User).where(User.username == username)
    user = (await db.execute(query)).scalar()
    if not user or not user.password == password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

async def create_user(db, user: UserCreate):
    query = User.insert().values(**user.dict())
    await db.execute(query)
    return user

async def update_user(db, user_id: int, updated_user: UserUpdate):
    query = User.update().where(User.id == user_id).values(**updated_user.dict())
    await db.execute(query)
    return updated_user