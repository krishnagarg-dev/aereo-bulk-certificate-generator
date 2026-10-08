from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.api.routes import router
from app.core.config import settings
from app.db.session import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    Path(settings.certificate_output_dir).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Bulk certificate generation backend for the AEREO software development assignment.",
    lifespan=lifespan,
)
app.include_router(router)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}
