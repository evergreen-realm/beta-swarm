from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Item as DBItem
from schemas import Item, ItemCreate, ItemUpdate

router = APIRouter(
    prefix="/items",
    tags=["items"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=Item, status_code=status.HTTP_201_CREATED)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    """
    Create a new item in the database.
    """
    db_item = DBItem(
        name=item.name,
        description=item.description,
        price=item.price,
        is_available=item.is_available
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.get("/", response_model=List[Item])
def read_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieve a list of all items from the database.
    Supports pagination with 'skip' and 'limit' parameters.
    """
    items = db.query(DBItem).offset(skip).limit(limit).all()
    return items

@router.get("/{item_id}", response_model=Item)
def read_item(item_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a single item by its unique ID.
    Raises a 404 error if the item is not found.
    """
    item = db.query(DBItem).filter(DBItem.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item

@router.put("/{item_id}", response_model=Item)
def update_item(item_id: int, item_update: ItemUpdate, db: Session = Depends(get_db)):
    """
    Update an existing item identified by its ID.
    Allows partial updates (only provided fields will be changed).
    Raises a 404 error if the item is not found.
    """
    db_item = db.query(DBItem).filter(DBItem.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    # Update only the fields that are provided in the request body
    update_data = item_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_item, key, value)

    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    """
    Delete an item by its unique ID.
    Raises a 404 error if the item is not found.
    """
    db_item = db.query(DBItem).filter(DBItem.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    db.delete(db_item)
    db.commit()
    return