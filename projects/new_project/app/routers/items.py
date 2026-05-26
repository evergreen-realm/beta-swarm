from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app import crud, schemas, models
from app.database import get_db, engine, Base

# Create tables in the database (for development purposes, remove in production if using migrations)
# Base.metadata.create_all(bind=engine)

router = APIRouter(
    prefix="/items",
    tags=["items"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=schemas.ItemInDB, status_code=status.HTTP_201_CREATED)
def create_item(item: schemas.ItemCreate, db: Session = Depends(get_db)):
    """
    Create a new item.
    """
    return crud.create_item(db=db, item=item)

@router.get("/", response_model=List[schemas.ItemInDB])
def read_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieve a list of items.
    """
    items = crud.get_items(db, skip=skip, limit=limit)
    return items

@router.get("/{item_id}", response_model=schemas.ItemInDB)
def read_item(item_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a single item by its ID.
    """
    db_item = crud.get_item(db, item_id=item_id)
    if db_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return db_item

@router.put("/{item_id}", response_model=schemas.ItemInDB)
def update_item(item_id: int, item: schemas.ItemUpdate, db: Session = Depends(get_db)):
    """
    Update an existing item by its ID.
    """
    db_item = crud.update_item(db, item_id=item_id, item=item)
    if db_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return db_item

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    """
    Delete an item by its ID.
    """
    db_item = crud.delete_item(db, item_id=item_id)
    if db_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    # FastAPI automatically handles 204 No Content for responses with no return body.
    # We return None explicitly for clarity.
    return None