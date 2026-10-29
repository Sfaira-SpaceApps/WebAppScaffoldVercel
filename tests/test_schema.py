import pytest
from pydantic import ValidationError

from app.schemas.example import ExampleCreate


def test_example_name_is_required() -> None:
    with pytest.raises(ValidationError):
        ExampleCreate(name="")


def test_example_name_accepts_nonempty_value() -> None:
    payload = ExampleCreate(name="demo")
    assert payload.name == "demo"
