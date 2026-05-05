import json
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


def default_config() -> dict[str, Any]:
    return {
        "enabled": settings.backup_auto_enabled,
        "interval_hours": settings.backup_interval_hours,
        "directory": settings.backup_directory,
        "retention": settings.backup_retention,
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
    return config


def save_config(data: dict[str, Any]) -> dict[str, Any]:
    config = load_config()
    for key in ("enabled", "interval_hours", "directory", "retention"):
        if key in data:
            config[key] = data[key]
    config["enabled"] = bool(config["enabled"])
    config["interval_hours"] = max(1, int(config["interval_hours"]))
    config["directory"] = str(config["directory"]).strip() or settings.backup_directory
    config["retention"] = max(1, int(config["retention"]))
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return config


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


async def write_backup(db: AsyncSession) -> dict[str, str]:
    config = load_config()
    directory = Path(config["directory"])
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"helpdesk-backup-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
    path = directory / filename
    data = await build_backup(db)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    cleanup_old_backups(directory, config["retention"])
    return {"filename": filename, "path": str(path)}


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
