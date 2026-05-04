#!/usr/bin/env python3
"""
Torna um utilizador administrador pela linha de comandos.

Uso:
    docker compose -f docker-compose.unraid.yml exec backend python scripts/make_admin.py pedropereira@queiroz.pt
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.user import User, UserRole


async def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/make_admin.py <email>")
        sys.exit(1)

    email = sys.argv[1].strip().lower()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.email.ilike(email))
        )
        user = result.scalar_one_or_none()

        if not user:
            print(f"Utilizador '{email}' nao encontrado.")
            print("\nUtilizadores existentes:")
            all_users = (await db.execute(select(User))).scalars().all()
            for u in all_users:
                print(f"  {u.email}  (role: {u.role})")
            sys.exit(1)

        old_role = user.role
        user.role = UserRole.ADMIN
        await db.commit()

        print(f"OK: {user.email}")
        print(f"   Role: {old_role} -> admin")
        print(f"\nFaz logout e login novamente para o efeito ter efecto.")


asyncio.run(main())
