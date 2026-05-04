from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
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
        "color": "#3D52D5",
        "icon": "school",
        "sla_hours": 24,
    },
    {
        "name": "Apoio Técnico",
        "description": "Equipamentos, rede, contas e suporte informático",
        "color": "#0D9488",
        "icon": "build",
        "sla_hours": 24,
    },
]


async def ensure_defaults(db: AsyncSession) -> None:
    for data in DEFAULT_SCHOOLS:
        exists = await db.execute(select(School).where(School.name == data["name"]))
        if not exists.scalar_one_or_none():
            db.add(School(**data))

    for data in DEFAULT_CATEGORIES:
        exists = await db.execute(select(Category).where(Category.name == data["name"]))
        if not exists.scalar_one_or_none():
            db.add(Category(**data))

    await db.commit()
