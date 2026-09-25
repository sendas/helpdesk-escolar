"""Roles (papéis) and permissions.

Every user has a base ``role`` (teacher, technician, admin, …, kept in sync with Entra ID) and can optionally be
given an editable papel (``role_key``). The permissions of the effective papel decide what the user can do.
Administrators always have every permission, so nobody can lock themselves out.

"Staff" behaviour (managing tickets) keeps being derived from ``role``/``is_technician`` in the existing queries;
``sync_user_flags`` keeps those columns consistent with the ``tickets.manage`` permission.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.role import Role
from app.models.user import User, UserRole

PERMISSIONS: list[dict] = [
    {"key": "tickets.view_all", "label": "Ver todos os tickets", "hint": "Acesso à Gestão de tickets e a qualquer ticket, só de leitura."},
    {"key": "tickets.manage", "label": "Gerir tickets", "hint": "Atribuir, alterar estados, notas internas e mensagens privadas."},
    {"key": "stats.view", "label": "Ver estatísticas", "hint": "Página de estatísticas."},
    {"key": "knowledge.edit", "label": "Editar a base de conhecimento", "hint": "Criar, editar e apagar artigos."},
    {"key": "users.manage", "label": "Gerir utilizadores e papéis", "hint": "Alterar papéis, grupos e contas."},
    {"key": "settings.manage", "label": "Configurações do sistema", "hint": "Configurações, categorias, escolas, emails e cópias de segurança."},
]
ALL_PERMISSIONS = {p["key"] for p in PERMISSIONS}
STAFF_PERMISSIONS = {"tickets.view_all", "tickets.manage"}

DEFAULT_ROLES: list[dict] = [
    {"key": "teacher", "label": "Docente", "icon": "school", "color": "#3D52D5", "permissions": [], "sort": 10},
    {"key": "non_teaching", "label": "Não docente", "icon": "badge", "color": "#64748B", "permissions": [], "sort": 20},
    {"key": "secretary", "label": "Secretaria", "icon": "business_center", "color": "#0D9488", "permissions": [], "sort": 30},
    {"key": "direcao", "label": "Direção", "icon": "account_balance", "color": "#7C3AED",
     "permissions": ["tickets.view_all", "stats.view"], "sort": 40},
    {"key": "technician", "label": "Técnico", "icon": "build", "color": "#F59E0B",
     "permissions": ["tickets.view_all", "tickets.manage", "stats.view"], "sort": 50},
    {"key": "tic", "label": "Equipa TIC", "icon": "computer", "color": "#0891B2",
     "permissions": ["tickets.view_all", "tickets.manage", "stats.view", "knowledge.edit"], "sort": 60},
    {"key": "admin", "label": "Administrador", "icon": "admin_panel_settings", "color": "#EF4444",
     "permissions": sorted(ALL_PERMISSIONS), "sort": 90},
]
# Papéis that cannot be deleted; the admin papel cannot be edited at all.
BUILTIN_KEYS = {r["key"] for r in DEFAULT_ROLES}
LOCKED_KEYS = {"admin"}

# key -> {"label", "permissions": set, ...}; loaded at startup and refreshed after every change
_roles: dict[str, dict] = {}


def _row_to_dict(role: Role) -> dict:
    perms = {p for p in (role.permissions or "").split(",") if p in ALL_PERMISSIONS}
    return {"key": role.key, "label": role.label, "icon": role.icon, "color": role.color,
            "permissions": perms, "builtin": role.builtin, "sort": role.sort}


async def load_roles(db: AsyncSession) -> None:
    rows = (await db.execute(select(Role))).scalars().all()
    _roles.clear()
    _roles.update({r.key: _row_to_dict(r) for r in rows})


async def ensure_default_roles(db: AsyncSession) -> None:
    existing = {r.key for r in (await db.execute(select(Role))).scalars().all()}
    for r in DEFAULT_ROLES:
        if r["key"] not in existing:
            db.add(Role(key=r["key"], label=r["label"], icon=r["icon"], color=r["color"],
                        permissions=",".join(r["permissions"]), builtin=True, sort=r["sort"]))
    await db.commit()
    await load_roles(db)


def effective_role_key(user: User) -> str:
    if user.role == UserRole.ADMIN:
        return "admin"
    if user.role_key and user.role_key in _roles:
        return user.role_key
    if user.role == UserRole.TECHNICIAN or user.is_technician:
        return "technician"
    return user.role.value if user.role else "teacher"


def role_label(user: User) -> str:
    role = _roles.get(effective_role_key(user))
    return role["label"] if role else ""


def permissions_for(user: User) -> set[str]:
    if user.role == UserRole.ADMIN:
        return set(ALL_PERMISSIONS)
    perms = set(_roles.get(effective_role_key(user), {}).get("permissions", set()))
    # Existing technicians keep managing tickets whatever their papel says
    if user.role == UserRole.TECHNICIAN or user.is_technician:
        perms |= STAFF_PERMISSIONS
    return perms


def has_perm(user: User, perm: str) -> bool:
    return perm in permissions_for(user)


def role_permissions(key: str) -> set[str]:
    return set(_roles.get(key, {}).get("permissions", set()))


def sync_user_flags(user: User) -> None:
    """Keep role/is_technician consistent with the papel, as the rest of the app reads those columns."""
    if user.role == UserRole.ADMIN or not user.role_key:
        return
    manages = "tickets.manage" in role_permissions(user.role_key)
    user.is_technician = manages
    if manages:
        user.role = UserRole.TECHNICIAN
    elif user.role == UserRole.TECHNICIAN:
        user.role = UserRole(user.role_key) if user.role_key in UserRole._value2member_map_ else UserRole.TEACHER
