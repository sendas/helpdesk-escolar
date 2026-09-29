import enum
import json
import logging
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, Enum as SAEnum, select, text
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401 — every table registered on Base
from app.config import settings
from app.database import Base
from app.services.jsonfile import write_json_atomic

logger = logging.getLogger(__name__)


DATA_DIR = Path("/app/data")
CONFIG_PATH = DATA_DIR / "backup_config.json"
HISTORY_PATH = DATA_DIR / "backup_history.json"
MAX_HISTORY = 100

_RESTORE_INSTRUCTIONS = """\
RESTAURO DO HELPDESK ESCOLAR
==============================

Este arquivo ZIP contém os dados do helpdesk:

  data/
    tickets.db          — base de dados SQLite completa (tickets, utilizadores, papéis, chat, etc.)
    uploads/            — ficheiros anexados aos tickets e logótipos
    app_settings.json   — configurações da aplicação (nome, fornecedor, etc.)
    backup_config.json  — configurações de backup automático

As palavras-passe e chaves (app.env) NÃO estão incluídas: guarde-as à parte.

RESTAURAR NA MESMA INSTALAÇÃO
-----------------------------
Administração → Cópias de segurança → Importar / Restaurar → escolher este ZIP.

RESTAURAR NUMA INSTALAÇÃO NOVA
------------------------------
1. Instale o helpdesk (git clone + app.env com as mesmas credenciais).
2. Com os contentores parados, extraia este ZIP para a pasta da aplicação:
     unzip helpdesk-full-*.zip -d /mnt/cache/appdata/helpdesk
   (a pasta data/ do ZIP substitui a pasta data/ da instalação)
3. Inicie: docker compose -f docker-compose.unraid.yml up -d
4. Verifique que os tickets, utilizadores e anexos estão presentes.
"""

# Tables left out of the JSON export: access statistics only, they can be very large
_JSON_SKIP_TABLES = {"access_logs"}
# Tables the old (v1) JSON export contained
_LEGACY_TABLES = ("schools", "categories", "users", "tickets", "comments", "attachments")
# Tables that only make sense with their tickets: replaced too when restoring an old export
_TICKET_TABLES = ("ticket_events", "ticket_watchers", "ticket_assignees", "ticket_reminders", "ticket_views", "processed_emails")


def default_config() -> dict[str, Any]:
    return {
        "enabled": settings.backup_auto_enabled,
        "interval_hours": settings.backup_interval_hours,
        "directory": settings.backup_directory,
        "retention": settings.backup_retention,
        "secondary_directory": "",
        "full_zip_enabled": False,
        "full_zip_retention": 7,
        "onedrive_enabled": False,
        "onedrive_user": "",
        "onedrive_folder": "Backups/Helpdesk",
        "onedrive_retention": 14,
    }


def load_config() -> dict[str, Any]:
    config = default_config()
    try:
        if CONFIG_PATH.exists():
            saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                config.update({k: saved[k] for k in config.keys() & saved.keys()})
    except Exception:
        pass
    config["enabled"] = bool(config.get("enabled"))
    config["interval_hours"] = max(1, int(config.get("interval_hours") or 24))
    config["directory"] = str(config.get("directory") or settings.backup_directory)
    config["retention"] = max(1, int(config.get("retention") or 14))
    config["secondary_directory"] = str(config.get("secondary_directory") or "").strip()
    config["full_zip_enabled"] = bool(config.get("full_zip_enabled", False))
    config["full_zip_retention"] = max(1, int(config.get("full_zip_retention") or 7))
    config["onedrive_enabled"] = bool(config.get("onedrive_enabled", False))
    config["onedrive_user"] = str(config.get("onedrive_user") or "").strip()
    config["onedrive_folder"] = str(config.get("onedrive_folder") or "Backups/Helpdesk").strip()
    config["onedrive_retention"] = max(1, int(config.get("onedrive_retention") or 14))
    return config


def save_config(data: dict[str, Any]) -> dict[str, Any]:
    config = load_config()
    for key in ("enabled", "interval_hours", "directory", "retention", "secondary_directory",
                "full_zip_enabled", "full_zip_retention",
                "onedrive_enabled", "onedrive_user", "onedrive_folder", "onedrive_retention"):
        if key in data:
            config[key] = data[key]
    config["enabled"] = bool(config["enabled"])
    config["interval_hours"] = max(1, int(config["interval_hours"]))
    config["directory"] = str(config["directory"]).strip() or settings.backup_directory
    config["retention"] = max(1, int(config["retention"]))
    config["secondary_directory"] = str(config.get("secondary_directory") or "").strip()
    config["full_zip_enabled"] = bool(config.get("full_zip_enabled", False))
    config["full_zip_retention"] = max(1, int(config.get("full_zip_retention") or 7))
    config["onedrive_enabled"] = bool(config.get("onedrive_enabled", False))
    config["onedrive_user"] = str(config.get("onedrive_user") or "").strip()
    config["onedrive_folder"] = str(config.get("onedrive_folder") or "Backups/Helpdesk").strip()
    config["onedrive_retention"] = max(1, int(config.get("onedrive_retention") or 14))
    write_json_atomic(CONFIG_PATH, config)
    return config


def load_history() -> list[dict[str, Any]]:
    try:
        if HISTORY_PATH.exists():
            data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def _append_history(entry: dict[str, Any]) -> None:
    history = load_history()
    history.insert(0, entry)
    history = history[:MAX_HISTORY]
    try:
        write_json_atomic(HISTORY_PATH, history)
    except Exception:
        logger.exception("Não foi possível gravar o registo de cópias")


def record_failure(kind: str, exc: BaseException) -> None:
    """Show a failed automatic backup in "Registo de cópias" (it used to fail silently)."""
    _append_history({
        "id": int(datetime.utcnow().timestamp() * 1000) + (1 if kind == "zip" else 0),
        "filename": "Cópia automática falhou" + (" (ZIP completo)" if kind == "zip" else " (JSON)"),
        "path": "",
        "locations": [],
        "date": datetime.utcnow().isoformat(),
        "ok": False,
        "source": "auto",
        "backup_type": kind,
        "error": str(exc) or exc.__class__.__name__,
    })


def _json_value(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, enum.Enum):
        return value.value
    return value


async def build_backup(db: AsyncSession) -> dict[str, Any]:
    """Every table of the database (except access statistics), without the attachment files."""
    data: dict[str, Any] = {"format": 2, "exported_at": datetime.utcnow().isoformat()}
    for table in Base.metadata.sorted_tables:
        if table.name in _JSON_SKIP_TABLES:
            continue
        rows = (await db.execute(select(table))).mappings().all()
        data[table.name] = [{k: _json_value(v) for k, v in row.items()} for row in rows]
    return data


async def _write_backup_inner(db: AsyncSession, source: str) -> dict[str, Any]:
    config = load_config()
    directory = Path(config["directory"])
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"helpdesk-backup-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
    path = directory / filename
    data = await build_backup(db)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    cleanup_old_backups(directory, config["retention"])

    locations = [str(path)]
    secondary_error: str | None = None
    secondary_dir = config.get("secondary_directory", "").strip()
    if secondary_dir:
        try:
            sec_path = Path(secondary_dir)
            sec_path.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, sec_path / filename)
            locations.append(str(sec_path / filename))
            cleanup_old_backups(sec_path, config["retention"])
        except Exception as exc:
            secondary_error = str(exc)

    # OneDrive upload
    onedrive_error: str | None = None
    if config.get("onedrive_enabled") and config.get("onedrive_user"):
        import asyncio
        from app.services import onedrive_service
        od_user = config["onedrive_user"]
        od_folder = config["onedrive_folder"]
        od_retention = config["onedrive_retention"]
        def _od_upload_json() -> None:
            onedrive_service.upload_file(str(path), od_user, od_folder)
            onedrive_service.cleanup_remote(od_user, od_folder, "helpdesk-backup-", od_retention)
        try:
            await asyncio.get_event_loop().run_in_executor(None, _od_upload_json)
            locations.append(f"onedrive:{od_folder}/{filename}")
        except Exception as exc:
            onedrive_error = str(exc)

    entry: dict[str, Any] = {
        "id": int(datetime.utcnow().timestamp() * 1000),
        "filename": filename,
        "path": str(path),
        "locations": locations,
        "date": datetime.utcnow().isoformat(),
        "ok": secondary_error is None and onedrive_error is None,
        "source": source,
    }
    if secondary_error:
        entry["secondary_error"] = secondary_error
    if onedrive_error:
        entry["onedrive_error"] = onedrive_error
    _append_history(entry)
    return {"filename": filename, "path": str(path), "locations": locations, "secondary_error": secondary_error}


async def write_backup(db: AsyncSession) -> dict[str, Any]:
    return await _write_backup_inner(db, source="manual")


async def write_backup_auto(db: AsyncSession) -> None:
    await _write_backup_inner(db, source="auto")


def cleanup_old_backups(directory: Path, retention: int) -> None:
    try:
        backups = sorted(
            directory.glob("helpdesk-backup-*.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for old_file in backups[retention:]:
            old_file.unlink(missing_ok=True)
    except Exception:
        pass


def cleanup_old_full_zips(directory: Path, retention: int) -> None:
    try:
        zips = sorted(
            directory.glob("helpdesk-full-*.zip"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for old_file in zips[retention:]:
            old_file.unlink(missing_ok=True)
    except Exception:
        pass


def write_full_zip_auto() -> None:
    """Build a full ZIP and save to primary + secondary directories. Called by the scheduler."""
    config = load_config()
    primary_dir = Path(config["directory"]) / "full_zips"
    primary_dir.mkdir(parents=True, exist_ok=True)

    tmp_path, filename = build_full_zip()
    dest = primary_dir / filename
    shutil.move(tmp_path, dest)
    cleanup_old_full_zips(primary_dir, config["full_zip_retention"])

    locations = [str(dest)]
    secondary_error: str | None = None
    secondary_dir = config.get("secondary_directory", "").strip()
    if secondary_dir:
        try:
            sec_path = Path(secondary_dir) / "full_zips"
            sec_path.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, sec_path / filename)
            locations.append(str(sec_path / filename))
            cleanup_old_full_zips(sec_path, config["full_zip_retention"])
        except Exception as exc:
            secondary_error = str(exc)

    # OneDrive upload
    onedrive_error: str | None = None
    if config.get("onedrive_enabled") and config.get("onedrive_user"):
        from app.services import onedrive_service
        od_user = config["onedrive_user"]
        od_zip_folder = config["onedrive_folder"].rstrip("/") + "/full_zips"
        od_retention = config.get("full_zip_retention", 7)
        try:
            onedrive_service.upload_file(str(dest), od_user, od_zip_folder)
            onedrive_service.cleanup_remote(od_user, od_zip_folder, "helpdesk-full-", od_retention)
            locations.append(f"onedrive:{od_zip_folder}/{filename}")
        except Exception as exc:
            onedrive_error = str(exc)

    entry: dict[str, Any] = {
        "id": int(datetime.utcnow().timestamp() * 1000) + 1,
        "filename": filename,
        "path": str(dest),
        "locations": locations,
        "date": datetime.utcnow().isoformat(),
        "ok": secondary_error is None and onedrive_error is None,
        "source": "auto",
        "backup_type": "zip",
    }
    if secondary_error:
        entry["secondary_error"] = secondary_error
    if onedrive_error:
        entry["onedrive_error"] = onedrive_error
    _append_history(entry)


# Never in the ZIP: the live database files (a consistent snapshot is added instead), the session signing key,
# older copies and snapshots
_ZIP_SKIP_DIRS = {"backups", "full_zips", "snapshots"}
_ZIP_SKIP_FILES = {"tickets.db", "tickets.db-wal", "tickets.db-shm", "tickets.db-journal", ".secret_key"}


def build_full_zip() -> tuple[str, str]:
    """Write a full ZIP to a temp file and return (tmp_path, filename).

    Uses a temp file instead of BytesIO so large attachment collections
    don't exhaust container memory.
    """
    from app.services.db_maintenance import snapshot_to

    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    filename = f"helpdesk-full-{timestamp}.zip"

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp.close()
    work_dir = tempfile.mkdtemp(prefix="helpdesk-zip-")
    try:
        db_copy = snapshot_to(Path(work_dir) / "tickets.db")
        with zipfile.ZipFile(tmp.name, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
            zf.writestr("RESTAURO.txt", _RESTORE_INSTRUCTIONS)
            if db_copy:
                zf.write(db_copy, "data/tickets.db")
            if DATA_DIR.exists():
                for path in sorted(DATA_DIR.rglob("*")):
                    if not path.is_file():
                        continue
                    try:
                        rel = path.relative_to(DATA_DIR)
                    except ValueError:
                        continue
                    if rel.parts and rel.parts[0] in _ZIP_SKIP_DIRS:
                        continue
                    if len(rel.parts) == 1 and (rel.name in _ZIP_SKIP_FILES or ".bak" in rel.name or rel.name.endswith(".tmp")):
                        continue
                    try:
                        zf.write(path, str(Path("data") / rel))
                    except Exception:
                        logger.warning("Ficheiro não incluído no ZIP: %s", path, exc_info=True)
    except BaseException:
        Path(tmp.name).unlink(missing_ok=True)
        raise
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    return tmp.name, filename


def write_full_zip_to_disk(target_dir: str | None = None) -> dict[str, str]:
    config = load_config()
    directory = Path(target_dir or config.get("secondary_directory") or config["directory"])
    directory.mkdir(parents=True, exist_ok=True)
    tmp_path, filename = build_full_zip()
    dest = directory / filename
    shutil.move(tmp_path, dest)
    return {"filename": filename, "path": str(dest)}


def _column_value(column, value: Any) -> Any:
    if value is None:
        return None
    if isinstance(column.type, DateTime) and isinstance(value, str):
        return datetime.fromisoformat(value)
    if isinstance(column.type, SAEnum) and column.type.enum_class is not None and not isinstance(value, enum.Enum):
        enum_class = column.type.enum_class
        try:
            return enum_class(value)
        except ValueError:
            return enum_class[value]
    return value


async def restore_backup(db: AsyncSession, data: dict[str, Any]) -> dict[str, int]:
    """Replace the database content with a JSON export. Everything happens in one transaction: if anything does
    not fit, nothing is changed."""
    tables = {t.name: t for t in Base.metadata.sorted_tables}
    if data.get("format") == 2:
        replaced = [name for name in tables if name not in _JSON_SKIP_TABLES]
    else:
        # Old export (only 6 tables): also clear what hangs off the old tickets, keep the rest
        replaced = [name for name in tables if name in _LEGACY_TABLES or name in _TICKET_TABLES]
    order = [t for t in Base.metadata.sorted_tables if t.name in replaced]

    # Foreign keys are checked once, at commit, instead of after every row
    await db.execute(text("PRAGMA defer_foreign_keys=ON"))
    if data.get("format") != 2:
        await db.execute(text("DELETE FROM reactions WHERE target_type IN ('comment', 'ticket')"))
    for table in reversed(order):
        await db.execute(table.delete())

    counts: dict[str, int] = {}
    for table in order:
        rows = data.get(table.name) or []
        if not isinstance(rows, list):
            continue
        prepared = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            prepared.append({c.name: _column_value(c, row[c.name]) for c in table.columns if c.name in row})
        # executemany needs the same keys in every row
        groups: dict[tuple, list[dict]] = {}
        for row in prepared:
            groups.setdefault(tuple(sorted(row)), []).append(row)
        for group in groups.values():
            await db.execute(table.insert(), group)
        counts[table.name] = len(prepared)

    await _fix_dangling_references(db, set(replaced))
    await db.commit()
    await _after_restore(db)
    return counts


async def _fix_dangling_references(db: AsyncSession, replaced: set[str]) -> None:
    """Rows that were kept but point at a replaced row that no longer exists: clear the link, or drop the row
    when the link is mandatory."""
    for table in Base.metadata.sorted_tables:
        if table.name in replaced:
            continue
        for fk in table.foreign_keys:
            parent = fk.column.table
            if parent.name not in replaced:
                continue
            col = fk.parent
            missing = f"{col.name} IS NOT NULL AND {col.name} NOT IN (SELECT {fk.column.name} FROM {parent.name})"
            if col.nullable and not col.primary_key:
                await db.execute(text(f"UPDATE {table.name} SET {col.name} = NULL WHERE {missing}"))
            else:
                await db.execute(text(f"DELETE FROM {table.name} WHERE {missing}"))


async def _after_restore(db: AsyncSession) -> None:
    from app.services.permissions import load_roles
    try:
        await load_roles(db)
    except Exception:
        logger.exception("Não foi possível recarregar os papéis depois do restauro")


def _check_sqlite_file(path: Path) -> None:
    con = sqlite3.connect(path)
    try:
        ok = con.execute("PRAGMA integrity_check").fetchone()
        if not ok or ok[0] != "ok":
            raise ValueError("A base de dados do ZIP está danificada")
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"tickets", "users"} <= tables:
            raise ValueError("O ZIP não contém uma base de dados do helpdesk")
    finally:
        con.close()


def _copy_database_into_live(source: Path) -> None:
    """Replace the live database content with `source`, page by page, through SQLite (safe with WAL and with
    other connections open, unlike swapping the file)."""
    from app.database import sqlite_path

    live = sqlite_path()
    if not live:
        raise RuntimeError("O restauro por ZIP só é possível com SQLite")
    dst = sqlite3.connect(live, timeout=30)
    try:
        page_size = dst.execute("PRAGMA page_size").fetchone()[0]
        src = sqlite3.connect(source)
        try:
            if src.execute("PRAGMA page_size").fetchone()[0] != page_size:
                # A WAL database cannot change page size, so the copy is converted first
                src.execute("PRAGMA journal_mode=DELETE")
                src.execute(f"PRAGMA page_size={int(page_size)}")
                src.execute("VACUUM")
            src.backup(dst)
        finally:
            src.close()
    finally:
        dst.close()


def _zip_member_target(name: str, prefix: str, base: Path) -> Path | None:
    if not name.startswith(prefix) or name.endswith("/"):
        return None
    rel = Path(name[len(prefix):])
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        return None
    return base / rel


async def restore_full_zip(zip_path: str) -> dict[str, int]:
    """Restore a full ZIP: the database file as a whole (every table, exactly as it was), then the attachments
    and the settings files. A copy of the current database is kept in data/snapshots first."""
    import asyncio
    from app.database import AsyncSessionLocal, Base as _Base, engine
    from app.services.db_maintenance import SNAPSHOT_DIR, cleanup_orphans, snapshot_to

    loop = asyncio.get_running_loop()
    work_dir = Path(tempfile.mkdtemp(prefix="helpdesk-restore-"))
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            if "data/tickets.db" not in zf.namelist():
                raise ValueError("O ZIP não contém data/tickets.db: não parece um backup completo")
            extracted = work_dir / "tickets.db"
            with zf.open("data/tickets.db") as src, open(extracted, "wb") as out:
                shutil.copyfileobj(src, out)
            await loop.run_in_executor(None, _check_sqlite_file, extracted)

            safety = await loop.run_in_executor(
                None, snapshot_to, SNAPSHOT_DIR / f"antes-do-restauro-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
            )
            logger.warning("Restauro de ZIP: cópia da base de dados atual em %s", safety)

            await engine.dispose()
            await loop.run_in_executor(None, _copy_database_into_live, extracted)
            await engine.dispose()

            # An older backup may predate some columns/tables
            from app.main import _add_missing_columns
            async with engine.begin() as conn:
                await conn.run_sync(_Base.metadata.create_all)
                await _add_missing_columns(conn)
                await cleanup_orphans(conn)

            uploads = 0
            for info in zf.infolist():
                target = _zip_member_target(info.filename, "data/uploads/", DATA_DIR / "uploads")
                if target is None:
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, open(target, "wb") as out:
                    shutil.copyfileobj(src, out)
                uploads += 1

            for extra in ("app_settings.json", "backup_config.json"):
                name = f"data/{extra}"
                if name in zf.namelist():
                    with zf.open(name) as src:
                        content = json.load(src)
                    write_json_atomic(DATA_DIR / extra, content)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    counts: dict[str, int] = {}
    async with AsyncSessionLocal() as db:
        for name in ("schools", "categories", "users", "tickets", "comments", "attachments"):
            counts[name] = (await db.execute(text(f"SELECT COUNT(*) FROM {name}"))).scalar_one()
        await _after_restore(db)
    counts["upload_files"] = uploads
    return counts
