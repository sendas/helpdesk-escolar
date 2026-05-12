from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.group import HelpdeskGroup
from app.models.knowledge import KnowledgeArticle
from app.models.school import School
from app.models.ticket import Ticket


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
        "color": "#4F46E5",
        "icon": "school",
        "sla_hours": 48,
    },
    {
        "name": "Mail e Teams",
        "description": "Correio institucional, Teams, calendário e colaboração Microsoft",
        "email_to": "",
        "color": "#2563EB",
        "icon": "mail",
        "sla_hours": 48,
    },
    {
        "name": "Internet e Wi-Fi",
        "description": "Rede, acesso à Internet, Wi-Fi e conectividade",
        "email_to": "",
        "color": "#0891B2",
        "icon": "wifi",
        "sla_hours": 48,
    },
    {
        "name": "Computadores",
        "description": "Computadores, portáteis, periféricos e postos de trabalho",
        "email_to": "",
        "color": "#0F766E",
        "icon": "computer",
        "sla_hours": 48,
    },
    {
        "name": "Impressoras",
        "description": "Impressoras, digitalização, toner e filas de impressão",
        "email_to": "",
        "color": "#16A34A",
        "icon": "print",
        "sla_hours": 48,
    },
    {
        "name": "Projetores",
        "description": "Projetores, quadros interativos, imagem e som em sala",
        "email_to": "",
        "color": "#D97706",
        "icon": "videocam",
        "sla_hours": 48,
    },
    {
        "name": "Passwords",
        "description": "Reposição de palavra-passe e problemas de acesso",
        "email_to": "",
        "color": "#DC2626",
        "icon": "key",
        "sla_hours": 48,
    },
    {
        "name": "Outros",
        "description": "Pedidos que não se enquadram nas restantes categorias",
        "email_to": "",
        "color": "#64748B",
        "icon": "help_outline",
        "sla_hours": 48,
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
    await normalize_directory_roles(db)

    for data in DEFAULT_SCHOOLS:
        exists = await db.execute(select(School).where(School.name == data["name"]))
        if not exists.scalar_one_or_none():
            db.add(School(**data))

    for data in DEFAULT_CATEGORIES:
        exists = await db.execute(select(Category).where(Category.name == data["name"]))
        if not exists.scalar_one_or_none():
            db.add(Category(**data))

    old_support = (await db.execute(select(Category).where(Category.name == "Apoio Técnico"))).scalar_one_or_none()
    if old_support:
        has_tickets = (
            await db.execute(select(Ticket.id).where(Ticket.category_id == old_support.id).limit(1))
        ).scalar_one_or_none()
        if has_tickets is None:
            await db.delete(old_support)

    for data in DEFAULT_GROUPS:
        exists = await db.execute(select(HelpdeskGroup).where(HelpdeskGroup.name == data["name"]))
        if not exists.scalar_one_or_none():
            db.add(HelpdeskGroup(**data))

    for data in DEFAULT_KNOWLEDGE:
        exists = await db.execute(select(KnowledgeArticle).where(KnowledgeArticle.title == data["title"]))
        if not exists.scalar_one_or_none():
            db.add(KnowledgeArticle(**data))

    await db.commit()


async def normalize_directory_roles(db: AsyncSession) -> None:
    await db.execute(text("""
        UPDATE users
        SET role = 'NON_TEACHING', role_source = 'entra'
        WHERE COALESCE(role_locked, 0) = 0
          AND role NOT IN ('ADMIN', 'TECHNICIAN', 'SECRETARY')
          AND lower(trim(COALESCE(department, ''))) IN ('assistente operacional', 'assistentes operacionais')
    """))
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
        ("is_technician", "ALTER TABLE users ADD COLUMN is_technician BOOLEAN DEFAULT 0"),
        ("role_source", "ALTER TABLE users ADD COLUMN role_source VARCHAR(20) DEFAULT 'entra'"),
        ("role_locked", "ALTER TABLE users ADD COLUMN role_locked BOOLEAN DEFAULT 0"),
        ("onprem_dn", "ALTER TABLE users ADD COLUMN onprem_dn VARCHAR(500)"),
        ("onprem_path", "ALTER TABLE users ADD COLUMN onprem_path VARCHAR(500)"),
        ("password_hash", "ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"),
    ]
    changed = False
    for column, statement in user_migrations:
        if column not in user_columns:
            await db.execute(text(statement))
            changed = True
    if changed:
        await db.execute(text("UPDATE users SET is_technician = 1 WHERE role IN ('TECHNICIAN', 'technician')"))
        await db.execute(text("UPDATE categories SET sla_hours = 48 WHERE sla_hours = 24"))
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
    if "creator_email_notifications" not in ticket_columns:
        await db.execute(text("ALTER TABLE tickets ADD COLUMN creator_email_notifications BOOLEAN DEFAULT 1"))
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

    await db.execute(text("""
        CREATE TABLE IF NOT EXISTS ticket_assignees (
            ticket_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            PRIMARY KEY (ticket_id, user_id),
            FOREIGN KEY(ticket_id) REFERENCES tickets(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """))
    await db.execute(text("""
        INSERT OR IGNORE INTO ticket_assignees (ticket_id, user_id)
        SELECT id, assignee_id FROM tickets WHERE assignee_id IS NOT NULL
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
