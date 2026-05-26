from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import select, desc

import models, schemas


def create_task(db: Session, task: schemas.TaskCreate) -> models.Task:
    db_task = models.Task(
        title=task.title,
        description=task.description,
        status=task.status
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def get_task(db: Session, task_id: int) -> Optional[models.Task]:
    return db.query(models.Task).filter(models.Task.id == task_id).first()


def get_tasks(
    db: Session,
    status: Optional[schemas.TaskStatus] = None,
    skip: int = 0,
    limit: int = 100
) -> List[models.Task]:
    query = select(models.Task)
    if status:
        query = query.where(models.Task.status == status)
    
    # Order by creation date descending to show newer tasks first
    query = query.order_by(desc(models.Task.created_at))

    return db.scalars(query.offset(skip).limit(limit)).all()


def get_tasks_count(db: Session, status: Optional[schemas.TaskStatus] = None) -> int:
    query = select(func.count()).select_from(models.Task)
    if status:
        query = query.where(models.Task.status == status)
    return db.scalar(query)


def update_task(db: Session, task_id: int, task_update: schemas.TaskUpdate) -> Optional[models.Task]:
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if db_task:
        update_data = task_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_task, key, value)
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
    return db_task


def delete_task(db: Session, task_id: int) -> Optional[models.Task]:
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if db_task:
        db.delete(db_task)
        db.commit()
    return db_task