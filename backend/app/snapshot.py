"""Consistent copy of the database, for use before a deploy:

    docker compose -f docker-compose.unraid.yml exec -T backend python -m app.snapshot

Writes /app/data/tickets.db.bak-AAAAMMDD-HHMM (data/tickets.db.bak-... on the server)."""
from datetime import datetime

from app.services.db_maintenance import snapshot_to

if __name__ == "__main__":
    path = snapshot_to(f"/app/data/tickets.db.bak-{datetime.now().strftime('%Y%m%d-%H%M')}")
    print(f"Cópia criada: {path}" if path else "Base de dados não encontrada")
