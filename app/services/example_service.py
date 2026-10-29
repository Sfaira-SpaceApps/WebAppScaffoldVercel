from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Example
from app.schemas.example import ExampleCreate


def create_example(db: Session, payload: ExampleCreate) -> Example:
    example = Example(name=payload.name)
    db.add(example)
    db.commit()
    db.refresh(example)
    return example


def list_examples(db: Session) -> list[Example]:
    return list(db.scalars(select(Example).order_by(Example.id)).all())


def get_example(db: Session, example_id: int) -> Example | None:
    return db.get(Example, example_id)
