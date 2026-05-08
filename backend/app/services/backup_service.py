import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.category import Category
from app.models.school import School
from app.models.ticket import Attachment, Comment, Ticket
from app.models.user import User


CONFIG_PATH = Path("/app/data/backup_config.json")
HISTORY_PATH = Path("/app/data/backup_history.json")
MAX_HISTORY = 100


def default_config() -> dict[str, Any]:
    return {
        "enabled": settings.backup_auto_enabled,
        "interval_hours": settings.backup_interval_hours,
        "directory": settings.backup_directory,
        "retention": settings.backup_retention,
        "secondary_directory": "",
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
    return config


def save_config(data: dict[str, Any]) -> dict[str, Any]:
    config = load_config()
    for key in ("enabled", "interval_hours", "directory", "retention", "secondary_directory"):
        if key in data:
            config[key] = data[key]
    config["enabled"] = bool(config["enabled"])
    config["interval_hours"] = max(1, int(config["interval_hours"]))
    config["directory"] = str(config["directory"]).strip() or settings.backup_directory
    config["retention"] = max(1, int(config["retention"]))
    config["secondary_directory"] = str(config.get("secondary_directory") or "").strip()
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
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
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        HISTORY_PATH.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _to_dict(obj: Any) -> dict[str, Any]:
    data = {}
    for column in obj.__table__.columns:
        value = getattr(obj, column.name)
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        elif hasattr(value, "value"):
            value = value.value
        data[column.name] = value
    return data


async def build_backup(db: AsyncSession) -> dict[str, Any]:
    schools = (await db.execute(select(School))).scalars().all()
    categories = (await db.execute(select(Category))).scalars().all()
    users = (await db.execute(select(User))).scalars().all()
    tickets = (await db.execute(select(Ticket))).scalars().all()
    comments = (await db.execute(select(Comment))).scalars().all()
    attachments = (await db.execute(select(Attachment))).scalars().all()

    return {
        "exported_at": datetime.utcnow().isoformat(),
        "schools": [_to_dict(item) for item in schools],
        "categories": [_to_dict(item) for item in categories],
        "users": [_to_dict(item) for item in users],
        "tickets": [_to_dict(item) for item in tickets],
        "comments": [_to_dict(item) for item in comments],
        "attachments": [_to_dict(item) for item in attachments],
    }


async def write_backup(db: AsyncSession) -> dict[str, Any]:
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

    entry: dict[str, Any] = {
        "id": int(datetime.utcnow().timestamp() * 1000),
        "filename": filename,
        "path": str(path),
        "locations": locations,
        "date": datetime.utcnow().isoformat(),
        "ok": True,
        "source": "auto" if False else "manual",
    }
    if secondary_error:
        entry["secondary_error"] = secondary_error
    _append_history(entry)

    return {"filename": filename, "path": str(path), "locations": locations, "secondary_error": secondary_error}


async def write_backup_auto(db: AsyncSession) -> None:
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

    entry: dict[str, Any] = {
        "id": int(datetime.utcnow().timestamp() * 1000),
        "filename": filename,
        "path": str(path),
        "locations": locations,
        "date": datetime.utcnow().isoformat(),
        "ok": secondary_error is None,
        "source": "auto",
    }
    if secondary_error:
        entry["secondary_error"] = secondary_error
    _append_history(entry)


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

