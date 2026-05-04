from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from app.config import settings
from app.api.v1.router import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup (no Alembic needed for simple deployments)
    from app.database import engine, Base
    import app.models  # noqa: F401 — registers all models with Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    from app.database import AsyncSessionLocal
    from app.services.bootstrap import ensure_defaults
    async with AsyncSessionLocal() as db:
        await ensure_defaults(db)
    yield


app = FastAPI(
    title="Teacher Ticket System",
    description="Sistema de tickets para professores autenticados via Active Directory",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware, secret_key=settings.app_secret_key)

app.include_router(router)
os.makedirs("/app/data/uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="/app/data/uploads"), name="uploads")


@app.get("/health")
async def health():
    return {"status": "ok"}
