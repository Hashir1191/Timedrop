from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers.auth import router as auth_router
from app.routers.parcels import router as parcels_router
from app.routers.scheduling import router as scheduling_router
from app.routers.delivery import router as delivery_router
from app.routers.notifications import router as notifications_router
from app.routers.phone_verification import router as phone_verification_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_for_startup()
    yield


app = FastAPI(title=settings.app_name, version="0.9.0", description="Backend API for the TimeDrop delivery scheduling pilot.", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth_router)
app.include_router(parcels_router)
app.include_router(scheduling_router)
app.include_router(delivery_router)
app.include_router(notifications_router)
app.include_router(phone_verification_router)


@app.get("/", tags=["General"])
def root() -> dict[str, str]:
    return {"message": "Welcome to TimeDrop API", "docs": "/docs", "health": "/health"}


@app.get("/health", tags=["General"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "timedrop-api"}
