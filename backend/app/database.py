import os
import unicodedata
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


engine = create_async_engine(settings.database_url, echo=settings.app_debug)


def fold_text(value):
    """Lower-case and strip accents, so searching "acao" finds "Ação" (SQLite's LIKE only folds ASCII)."""
    if value is None:
        return None
    return "".join(c for c in unicodedata.normalize("NFKD", str(value)) if not unicodedata.combining(c)).casefold()


@event.listens_for(engine.sync_engine, "connect")
def _register_sqlite_functions(dbapi_connection, _record):
    if engine.dialect.name == "sqlite":
        dbapi_connection.create_function("hd_fold", 1, fold_text, deterministic=True)
        cursor = dbapi_connection.cursor()
        # WAL lets readers and the writer work at the same time (no "database is locked" at busy moments);
        # foreign keys make the schema's ON DELETE rules actually run
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=15000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def sqlite_path() -> str | None:
    """Filesystem path of the SQLite database, or None for another database / in-memory."""
    url = engine.url
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        return None
    return os.path.abspath(url.database)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
