from fastapi import APIRouter, HTTPException
from typing import List
from app.models import Item

router = APIRouter(prefix="/api/v1/items", tags=["items"])

# In-memory store (replace with a real DB in production)
items_db: dict = {}


@router.get("/", response_model=List[Item])
async def list_items():
    return list(items_db.values())


@router.post("/", response_model=Item)
async def create_item(item: Item):
    items_db[item.id] = item
    return item


@router.get("/{item_id}", response_model=Item)
async def get_item(item_id: str):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    return items_db[item_id]


@router.put("/{item_id}", response_model=Item)
async def update_item(item_id: str, item: Item):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    items_db[item_id] = item
    return item


@router.delete("/{item_id}")
async def delete_item(item_id: str):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    del items_db[item_id]
    return {"status": "deleted"}
