import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, Integer, String, Enum, DateTime, func, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class TaskStatus(str, PyEnum):
    PENDING = "pending"
    COMPLETED = "completed"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.PENDING)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Task(id={self.id}, title='{self.title}', status='{self.status}')>"