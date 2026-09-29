"""Resumo dos pedidos desde uma data (para relatórios à Direção).

No servidor:  docker compose -f docker-compose.unraid.yml exec -T backend python scripts/estatisticas.py 2026-09-01
"""
import sqlite3, datetime as dt, sys
since = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else dt.date.today().replace(day=1)
db = sys.argv[2] if len(sys.argv) > 2 else '/app/data/tickets.db'
c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
today = dt.date.today()
days = (today - since).days + 1
workdays = sum(1 for i in range(days) if (since + dt.timedelta(i)).weekday() < 5)
nd = "t.creator_id NOT IN (SELECT id FROM users WHERE auth_provider='demo')"
q = lambda s: c.execute(s).fetchall()
one = lambda s: c.execute(s).fetchone()[0]
S = f"'{since.isoformat()}'"
created = one(f"SELECT COUNT(*) FROM tickets t WHERE {nd} AND t.created_at >= {S}")
done_of_created = one(f"SELECT COUNT(*) FROM tickets t WHERE {nd} AND t.created_at >= {S} AND t.status IN ('RESOLVED','CLOSED')")
cols = [r[1] for r in q("PRAGMA table_info(tickets)")]
resolved_in = one(f"SELECT COUNT(*) FROM tickets t WHERE {nd} AND t.status IN ('RESOLVED','CLOSED') AND t.resolved_at >= {S}") if 'resolved_at' in cols else None
avg_h = one(f"SELECT AVG((julianday(t.resolved_at)-julianday(t.created_at))*24) FROM tickets t WHERE {nd} AND t.created_at >= {S} AND t.status IN ('RESOLVED','CLOSED') AND t.resolved_at IS NOT NULL") if 'resolved_at' in cols else None
hours = sorted(r[0] for r in q(f"SELECT (julianday(t.resolved_at)-julianday(t.created_at))*24 FROM tickets t WHERE {nd} AND t.created_at >= {S} AND t.status IN ('RESOLVED','CLOSED') AND t.resolved_at IS NOT NULL")) if 'resolved_at' in cols else []
med_h = hours[len(hours)//2] if hours else None
open_now = one(f"SELECT COUNT(*) FROM tickets t WHERE {nd} AND t.status NOT IN ('RESOLVED','CLOSED') AND t.archived_at IS NULL")
print(f"Período: {since:%d/%m/%Y} a {today:%d/%m/%Y} — {days} dias, {workdays} dias úteis")
print(f"Pedidos recebidos: {created}")
print(f"Média por dia: {created/days:.1f}   |   Média por dia útil: {created/max(workdays,1):.1f}")
print(f"Desses, já resolvidos ou fechados: {done_of_created} ({(done_of_created/created*100 if created else 0):.0f}%)")
if resolved_in is not None: print(f"Resolvidos/fechados no período (incluindo pedidos mais antigos): {resolved_in}")
if avg_h is not None: print(f"Tempo até resolver — média: {avg_h:.1f} h ({avg_h/24:.1f} dias) | mediana: {med_h:.1f} h" if med_h is not None else "Tempo até resolver: sem dados")
print(f"Em aberto agora: {open_now}")
print("Por escola:"); [print(f"  {n or 'Sem escola'}: {k}") for n, k in q(f"SELECT s.name, COUNT(*) FROM tickets t LEFT JOIN schools s ON s.id=t.school_id WHERE {nd} AND t.created_at >= {S} GROUP BY s.name ORDER BY 2 DESC")]
print("Categorias mais pedidas:"); [print(f"  {n}: {k}") for n, k in q(f"SELECT cat.name, COUNT(*) FROM tickets t JOIN categories cat ON cat.id=t.category_id WHERE {nd} AND t.created_at >= {S} GROUP BY cat.name ORDER BY 2 DESC LIMIT 6")]
top = q(f"SELECT date(t.created_at), COUNT(*) FROM tickets t WHERE {nd} AND t.created_at >= {S} GROUP BY 1 ORDER BY 2 DESC LIMIT 1")
if top: print(f"Dia com mais pedidos: {top[0][0]} ({top[0][1]})")
if 'ticket_ratings' in [r[0] for r in q("SELECT name FROM sqlite_master WHERE type='table'")]:
    r = q("SELECT AVG(stars), COUNT(*) FROM ticket_ratings")[0]
    print(f"Avaliações: {r[1]} (média {r[0]:.1f} estrelas)" if r[1] else "Avaliações: ainda nenhuma")
