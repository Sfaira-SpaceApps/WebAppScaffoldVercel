from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.connection import get_db
from app.schemas.example import ExampleCreate, ExampleRead
from app.services import example_service

router = APIRouter()


@router.get("/")
def root() -> dict[str, str]:
    return {"message": "FastAPI + PostgreSQL scaffold"}


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/db-health")
def db_health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@router.post("/examples", response_model=ExampleRead, status_code=status.HTTP_201_CREATED)
def create_example(
    payload: ExampleCreate,
    db: Session = Depends(get_db),
) -> ExampleRead:
    return example_service.create_example(db, payload)


@router.get("/examples", response_model=list[ExampleRead])
def list_examples(db: Session = Depends(get_db)) -> list[ExampleRead]:
    return example_service.list_examples(db)


@router.get("/examples/{example_id}", response_model=ExampleRead)
def get_example(example_id: int, db: Session = Depends(get_db)) -> ExampleRead:
    example = example_service.get_example(db, example_id)
    if example is None:
        raise HTTPException(status_code=404, detail="Example not found")
    return example
