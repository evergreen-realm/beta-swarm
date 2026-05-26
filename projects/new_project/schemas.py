import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from models import TaskStatus


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, example="Buy groceries")
    description: Optional[str] = Field(None, max_length=1000, example="Milk, eggs, bread, fruits")
    status: TaskStatus = Field(TaskStatus.PENDING, example=TaskStatus.PENDING)


class TaskCreate(TaskBase):
    # For creation, status can be specified, but defaults to PENDING
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255, example="Buy organic groceries")
    description: Optional[str] = Field(None, max_length=1000, example="Organic milk, eggs, bread, fruits")
    status: Optional[TaskStatus] = Field(None, example=TaskStatus.COMPLETED)


class TaskResponse(TaskBase):
    id: int = Field(..., example=1)
    created_at: datetime.datetime = Field(..., example="2023-10-27T10:00:00Z")
    updated_at: datetime.datetime = Field(..., example="2023-10-27T10:30:00Z")

    class Config:
        from_attributes = True # Formerly orm_mode = True for Pydantic v1


class PaginatedTasksResponse(BaseModel):
    total: int = Field(..., example=100)
    page: int = Field(..., example=1)
    page_size: int = Field(..., example=10)
    items: List[TaskResponse]