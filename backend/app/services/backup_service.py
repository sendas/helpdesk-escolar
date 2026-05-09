import json
import os
import shutil
import tempfile
import zipfile
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


DATA_DIR = Path("/app/data")
CONFIG_PATH = DATA_DIR / "backup_config.json"
HISTORY_PATH = DATA_DIR / "backup_history.json"
MAX_HISTORY = 100

_RESTORE_INSTRUCTIONS = """\
RESTAURO DO HELPDESK ESCOLAR
==============================

Este arquivo ZIP contém tudo o que é necessário para repor o helpdesk
numa instalação limpa. Inclui:

  .env                  — variáveis de ambiente (chaves, palavras-passe, SMTP, AD)
  data/                 — volume completo do servidor
    tickets.db          — base de dados SQLite (tickets, utilizadores, etc.)
    uploads/            — ficheiros anexados aos tickets e logótipos
    app_settings.json   — configurações da aplicação (nome, fornecedor, etc.)
    backup_config.json  — configurações de backup automático

ATENÇÃO — SEGURANÇA
-------------------
Este ZIP contém o ficheiro .env com credenciais sensíveis (chave JWT,
palavras-passe SMTP, segredos AD/Azure). Guarda-o num local seguro e
não o partilhes por canais não cifrados.

PASSOS PARA RESTAURO
--------------------

1. Instala o Docker e o Docker Compose no novo servidor.

2. Cria uma pasta de trabalho e copia o docker-compose.yml para lá.

3. Extrai este ZIP para essa pasta:
     unzip helpdesk-full-*.zip -d /opt/helpdesk
   Isso vai repor o .env e a pasta data/ nos locais corretos.

4. Inicia o serviço:
     docker compose up -d

5. Abre o browser e verifica que os tickets, utilizadores e ficheiros estão presentes.
"""


def default_config() -> dict[str, Any]:
    return {
        "enabled": settings.backup_auto_enabled,
        "interval_hours": settings.backup_interval_hours,
        "directory": settings.backup_directory,
        "retention": settings.backup_retention,
        "secondary_directory": "",
        "full_zip_enabled": False,
        "full_zip_retention": 7,
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
    return config


def save_config(data: dict[str, Any]) -> dict[str, Any]:
    config = load_config()
    for key in ("enabled", "interval_hours", "directory", "retention", "secondary_directory",
                "full_zip_enabled", "full_zip_retention"):
        if key in data:
            config[key] = data[key]
    config["enabled"] = bool(config["enabled"])
    config["interval_hours"] = max(1, int(config["interval_hours"]))
    config["directory"] = str(config["directory"]).strip() or settings.backup_directory
    config["retention"] = max(1, int(config["retention"]))
    config["secondary_directory"] = str(config.get("secondary_directory") or "").strip()
    config["full_zip_enabled"] = bool(config.get("full_zip_enabled", False))
    config["full_zip_retention"] = max(1, int(config.get("full_zip_retention") or 7))
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

    entry: dict[str, Any] = {
        "id": int(datetime.utcnow().timestamp() * 1000),
        "filename": filename,
        "path": str(path),
        "locations": locations,
        "date": datetime.utcnow().isoformat(),
        "ok": secondary_error is None,
        "source": source,
    }
    if secondary_error:
        entry["secondary_error"] = secondary_error
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

    entry: dict[str, Any] = {
        "id": int(datetime.utcnow().timestamp() * 1000) + 1,
        "filename": filename,
        "path": str(dest),
        "locations": locations,
        "date": datetime.utcnow().isoformat(),
        "ok": secondary_error is None,
        "source": "auto",
        "backup_type": "zip",
    }
    if secondary_error:
        entry["secondary_error"] = secondary_error
    _append_history(entry)


_ENV_CANDIDATES = [Path("/app/.env"), Path(".env")]


def build_full_zip() -> tuple[str, str]:
    """Write a full ZIP to a temp file and return (tmp_path, filename).

    Uses a temp file instead of BytesIO so large attachment collections
    don't exhaust container memory.
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    filename = f"helpdesk-full-{timestamp}.zip"
    skip_dirs = {"backups", "full_zips"}

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp.close()

    with zipfile.ZipFile(tmp.name, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
        zf.writestr("RESTAURO.txt", _RESTORE_INSTRUCTIONS)

        for env_path in _ENV_CANDIDATES:
            if env_path.exists():
                try:
                    zf.write(env_path, ".env")
                except Exception:
                    pass
                break

        if DATA_DIR.exists():
            for path in sorted(DATA_DIR.rglob("*")):
                if not path.is_file():
                    continue
                try:
                    rel = path.relative_to(DATA_DIR)
                except ValueError:
                    continue
                if rel.parts and rel.parts[0] in skip_dirs:
                    continue
                arcname = str(Path("data") / rel)
                try:
                    zf.write(path, arcname)
                except Exception:
                    pass

    return tmp.name, filename


def write_full_zip_to_disk(target_dir: str | None = None) -> dict[str, str]:
    config = load_config()
    directory = Path(target_dir or config.get("secondary_directory") or config["directory"])
    directory.mkdir(parents=True, exist_ok=True)
    tmp_path, filename = build_full_zip()
    dest = directory / filename
    shutil.move(tmp_path, dest)
    return {"filename": filename, "path": str(dest)}


async def restore_backup(db: AsyncSession, data: dict[str, Any]) -> dict[str, int]:
    """Restore from a JSON backup. Clears existing data and reimports."""
    from app.models.group import HelpdeskGroup

    # Clear existing data (order matters for FK constraints)
    for model in (Attachment, Comment, Ticket, User, Category, School):
        rows = (await db.execute(select(model))).scalars().all()
        for row in rows:
            await db.delete(row)
    await db.flush()

    counts: dict[str, int] = {}

    def _parse_dt(v: Any) -> datetime | None:
        if not v:
            return None
        try:
            return datetime.fromisoformat(str(v))
        except Exception:
            return None

    for school_d in data.get("schools", []):
        s = School(**{k: v for k, v in school_d.items() if hasattr(School, k)})
        db.add(s)
    counts["schools"] = len(data.get("schools", []))

    for cat_d in data.get("categories", []):
        c = Category(**{k: v for k, v in cat_d.items() if hasattr(Category, k)})
        db.add(c)
    counts["categories"] = len(data.get("categories", []))

    for user_d in data.get("users", []):
        u = User(**{k: v for k, v in user_d.items() if hasattr(User, k)})
        db.add(u)
    counts["users"] = len(data.get("users", []))

    await db.flush()

    for ticket_d in data.get("tickets", []):
        t = Ticket(**{k: v for k, v in ticket_d.items() if hasattr(Ticket, k)})
        db.add(t)
    counts["tickets"] = len(data.get("tickets", []))

    for comment_d in data.get("comments", []):
        c = Comment(**{k: v for k, v in comment_d.items() if hasattr(Comment, k)})
        db.add(c)
    counts["comments"] = len(data.get("comments", []))

    for att_d in data.get("attachments", []):
        a = Attachment(**{k: v for k, v in att_d.items() if hasattr(Attachment, k)})
        db.add(a)
    counts["attachments"] = len(data.get("attachments", []))

    await db.commit()
    return counts
