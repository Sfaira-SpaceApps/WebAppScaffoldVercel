from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.connection import get_db
from app.schemas.example import ExampleCreate, ExampleRead
from app.services import example_service
from app.services import spherex_service

router = APIRouter()


@router.get(
    "/spherex",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}}},
)
def get_spherex(
    ra_deg: float = Query(..., ge=0, lt=360, allow_inf_nan=False),
    dec_deg: float = Query(..., ge=-90, le=90, allow_inf_nan=False),
    cutout_size_i: float = Query(0.05, gt=0, le=1, allow_inf_nan=False),
    fake_color_theme: str = Query("gray", max_length=64),
) -> Response:
    """Return the earliest overlapping SPHEREx spectral image as a PNG."""
    try:
        png = spherex_service.query_spherex(ra_deg, dec_deg, cutout_size_i, fake_color_theme)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except spherex_service.SpherexNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except spherex_service.SpherexUpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return Response(content=png, media_type="image/png")


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
