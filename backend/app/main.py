from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.database import Base, engine
from app import models
from app.migrations import upgrade_legacy_parcel_table
from app.routers.auth import router as auth_router
from app.routers.parcels import router as parcels_router
from app.routers.scheduling import router as scheduling_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    upgrade_legacy_parcel_table()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.4.0",
    description="Backend API for the TimeDrop delivery scheduling pilot.",
    lifespan=lifespan,
)

app.include_router(auth_router)
app.include_router(parcels_router)
app.include_router(scheduling_router)


@app.get("/", tags=["General"])
def root() -> dict[str, str]:
    return {
        "message": "Welcome to TimeDrop API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["General"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "timedrop-api"}
