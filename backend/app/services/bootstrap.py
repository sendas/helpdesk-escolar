from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.group import HelpdeskGroup
from app.models.knowledge import KnowledgeArticle
from app.models.school import School


DEFAULT_SCHOOLS = [
    {"name": "Escola Eça de Queirós", "short_name": "Eça", "address": ""},
    {"name": "Escola Vasco da Gama", "short_name": "Vasco da Gama", "address": ""},
    {"name": "Escola Parque das Nações", "short_name": "Parque das Nações", "address": ""},
]

DEFAULT_CATEGORIES = [
    {
        "name": "Inovar",
        "description": "Pedidos relacionados com a plataforma Inovar",
        "email_to": "",
        "color": "#3D52D5",
        "icon": "school",
        "sla_hours": 24,
    },
    {
        "name": "Apoio Técnico",
        "description": "Equipamentos, rede, contas e suporte informático",
        "email_to": "",
        "color": "#0D9488",
        "icon": "build",
        "sla_hours": 24,
    },
]

DEFAULT_GROUPS = [
    {"name": "Equipa TIC VG", "description": "Equipa TIC da Escola Vasco da Gama"},
    {"name": "Equipa TIC PN", "description": "Equipa TIC da Escola Parque das Nações"},
    {"name": "Equipa TIC EQ", "description": "Equipa TIC da Escola Eça de Queirós"},
]

DEFAULT_KNOWLEDGE = [
    {
        "title": "Antes de abrir um pedido de Apoio Técnico",
        "body": "Indique sempre escola, sala, equipamento afetado, hora em que o problema ocorreu e, se possível, anexe uma captura de ecrã ou fotografia.",
    },
    {
        "title": "Antes de abrir um pedido sobre Inovar",
        "body": "Inclua o módulo do Inovar, a turma ou aluno afetado quando aplicável, a mensagem de erro e os passos que fez até ao problema aparecer.",
    },
]


async def ensure_defaults(db: AsyncSession) -> None:
    await ensure_schema(db)

    for data in DEFAULT_SCHOOLS:
        exists = await db.execute(select(School).where(School.name == data["name"]))
        if not exists.scalar_one_or_none():
            db.add(School(**data))

    for data in DEFAULT_CATEGORIES:
        exists = await db.execute(select(Category).where(Category.name == data["name"]))
        if not exists.scalar_one_or_none():
            db.add(Category(**data))

    for data in DEFAULT_GROUPS:
        exists = await db.execute(select(HelpdeskGroup).where(HelpdeskGroup.name == data["name"]))
        if not exists.scalar_one_or_none():
            db.add(HelpdeskGroup(**data))

    for data in DEFAULT_KNOWLEDGE:
        exists = await db.execute(select(KnowledgeArticle).where(KnowledgeArticle.title == data["title"]))
        if not exists.scalar_one_or_none():
            db.add(KnowledgeArticle(**data))

    await db.commit()


async def ensure_schema(db: AsyncSession) -> None:
    result = await db.execute(text("PRAGMA table_info(categories)"))
    category_columns = {row[1] for row in result.fetchall()}
    if "email_to" not in category_columns:
        await db.execute(text("ALTER TABLE categories ADD COLUMN email_to VARCHAR(200)"))
        await db.commit()

    result = await db.execute(text("PRAGMA table_info(users)"))
    user_columns = {row[1] for row in result.fetchall()}
    user_migrations = [
        ("role_source", "ALTER TABLE users ADD COLUMN role_source VARCHAR(20) DEFAULT 'entra'"),
        ("role_locked", "ALTER TABLE users ADD COLUMN role_locked BOOLEAN DEFAULT 0"),
        ("onprem_dn", "ALTER TABLE users ADD COLUMN onprem_dn VARCHAR(500)"),
        ("onprem_path", "ALTER TABLE users ADD COLUMN onprem_path VARCHAR(500)"),
    ]
    changed = False
    for column, statement in user_migrations:
        if column not in user_columns:
            await db.execute(text(statement))
            changed = True
    if changed:
        await db.execute(text("UPDATE users SET role_source = 'manual', role_locked = 1 WHERE role = 'ADMIN'"))
        await db.commit()

    result = await db.execute(text("PRAGMA table_info(tickets)"))
    ticket_columns = {row[1] for row in result.fetchall()}
    ticket_changed = False
    if "group_id" not in ticket_columns:
        await db.execute(text("ALTER TABLE tickets ADD COLUMN group_id INTEGER"))
        ticket_changed = True
    if "archived_at" not in ticket_columns:
        await db.execute(text("ALTER TABLE tickets ADD COLUMN archived_at DATETIME"))
        ticket_changed = True
    if ticket_changed:
        await db.commit()

    await db.execute(text("""
        CREATE TABLE IF NOT EXISTS ticket_watchers (
            ticket_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            PRIMARY KEY (ticket_id, user_id),
            FOREIGN KEY(ticket_id) REFERENCES tickets(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """))
    await db.commit()

    result = await db.execute(text("PRAGMA table_info(comments)"))
    comment_columns = {row[1] for row in result.fetchall()}
    comment_changed = False
    if "updated_at" not in comment_columns:
        await db.execute(text("ALTER TABLE comments ADD COLUMN updated_at DATETIME"))
        comment_changed = True
    if "deleted_at" not in comment_columns:
        await db.execute(text("ALTER TABLE comments ADD COLUMN deleted_at DATETIME"))
        comment_changed = True
    if comment_changed:
        await db.commit()
