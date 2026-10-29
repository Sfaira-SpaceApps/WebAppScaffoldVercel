from fastapi import FastAPI

from app.api.routes import router
from app.logging_config import configure_logging

configure_logging()

app = FastAPI(title="FastAPI Postgres Scaffold")
app.include_router(router)
