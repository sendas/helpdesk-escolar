"""Test setup: a fresh SQLite database per test session and the app started with its real startup code
(migrations, default roles…). Run with:  pip install -r requirements-dev.txt && pytest"""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="helpdesk-tests-")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp}/test.db"
os.environ.setdefault("AZURE_SYNC_INTERVAL_MINUTES", "0")
os.environ.setdefault("APP_SECRET_KEY", "test-" + "x" * 40)

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def client():
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def people(client):
    """Admin, docente, técnico, técnico 2 and Direção, with their session tokens."""
    from app.database import AsyncSessionLocal
    from app.models.user import User, UserRole
    from app.services.jwt_service import create_access_token
    specs = [
        ("adm", "Ana Admin", UserRole.ADMIN, None, False),
        ("prof", "Maria Serra Docente-510 - Física e Química", UserRole.TEACHER, None, False),
        ("tec", "Tiago Costa", UserRole.TECHNICIAN, None, True),
        ("tec2", "Rui Técnico", UserRole.TECHNICIAN, None, True),
        ("dir", "Diana Diretora", UserRole.TEACHER, "direcao", False),
    ]
    out = {}
    async with AsyncSessionLocal() as db:
        for username, name, role, role_key, tech in specs:
            u = User(username=username, email=f"{username}@escola.pt", display_name=name, role=role,
                     role_key=role_key, is_technician=tech, auth_provider="local")
            db.add(u)
            await db.flush()
            out[username] = {"id": u.id, "h": {"Authorization": "Bearer " + create_access_token({"sub": str(u.id), "role": role.value})}}
        await db.commit()
    return out


@pytest.fixture
def api():
    return "/api/v1"
