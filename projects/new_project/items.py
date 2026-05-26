from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import select, func
from database import get_session
from schemas import ItemCreate, ItemUpdate

async def get_db():
    db = get_session()
    try:
        yield db
    finally:
        db.close()

async def get_item(db, item_id: int):
    query = select(Item).where(Item.id == item_id)
    return (await db.execute(query)).scalar()

async def create_item(db, item: ItemCreate):
    query = Item.insert().values(**item.dict())
    await db.execute(query)
    return item

async def update_item(db, item_id: int, updated_item: ItemUpdate):
    query = Item.update().where(Item.id == item_id).values(**updated_item.dict())
    await db.execute(query)
    return updated_item