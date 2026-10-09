"""Pedidos reportados à empresa de apoio: quais já foram resolvidos pela escola e podem ser encerrados do lado deles.

No servidor:
  docker compose -f docker-compose.unraid.yml exec -T backend python scripts/empresa_apoio.py
      → lista e prepara o texto de UM email para a empresa (não envia nada)
  docker compose -f docker-compose.unraid.yml exec -T backend python scripts/empresa_apoio.py --marcar
      → além disso, deixa de considerar reportados os que a escola já resolveu (sem enviar emails)
"""
import datetime as dt
import sqlite3
import sys

DB = next((a for a in sys.argv[1:] if a.endswith(".db")), "/app/data/tickets.db")
mark = "--marcar" in sys.argv
c = sqlite3.connect(DB, timeout=30)
has_ref = "provider_ref" in {r[1] for r in c.execute("PRAGMA table_info(tickets)")}
ref_col = "t.provider_ref" if has_ref else "NULL"
rows = c.execute(f"""
    SELECT t.id, t.title, t.status, t.updated_at,
           (SELECT MAX(e.created_at) FROM ticket_events e WHERE e.ticket_id = t.id AND e.event_type = 'escalated'),
           {ref_col}
    FROM tickets t WHERE t.is_escalated = 1 ORDER BY t.id
""").fetchall()
done = [r for r in rows if r[2] in ("RESOLVED", "CLOSED")]
still = [r for r in rows if r[2] not in ("RESOLVED", "CLOSED")]
label = {"OPEN": "Aberto", "ASSIGNED": "Atribuído", "IN_PROGRESS": "Em curso", "WAITING_USER": "A aguardar utilizador",
         "RESOLVED": "Resolvido", "CLOSED": "Fechado"}
ref = lambda r: f" (vosso #{r[5]})" if r[5] else ""
day = lambda s: dt.datetime.fromisoformat(s).strftime("%d/%m/%Y") if s else "?"

print(f"Pedidos marcados como reportados à empresa de apoio: {len(rows)}\n")
print(f"Ainda por resolver ({len(still)}):")
for r in still:
    print(f"  #{r[0]}  {r[1]}{ref(r)}  — {label.get(r[2], r[2])}, reportado a {day(r[4])}")
print(f"\nJá resolvidos pela escola — podem ser encerrados pela empresa ({len(done)}):")
for r in done:
    print(f"  #{r[0]}  {r[1]}{ref(r)}  — {label.get(r[2], r[2])} a {day(r[3])}")

if done:
    print("\n----- Texto para enviar num único email à empresa de apoio -----\n")
    print("Boa tarde,\n\nOs seguintes pedidos que vos foram reportados já foram resolvidos pela equipa da escola e podem ser")
    print("encerrados no vosso sistema (incluindo eventuais duplicados com o mesmo assunto):\n")
    for r in done:
        print(f"  - [Ticket #{r[0]}] {r[1]}{ref(r)}")
    if still:
        print("\nContinuam por resolver, e precisamos do vosso apoio, apenas:\n")
        for r in still:
            print(f"  - [Ticket #{r[0]}] {r[1]}{ref(r)}")
    print("\nA partir de agora, cada situação é reportada uma única vez; as mensagens seguintes seguem como resposta")
    print("ao mesmo email, e quando resolvermos internamente enviamos um único aviso para encerrarem.\n\nObrigado.")
    print("\n-----------------------------------------------------------------")

if mark and done:
    now = dt.datetime.utcnow().isoformat(" ")
    for tid, *_ in done:
        c.execute("UPDATE tickets SET is_escalated = 0 WHERE id = ?", (tid,))
        c.execute("INSERT INTO ticket_events (ticket_id, actor_id, event_type, message, created_at) VALUES (?, NULL, 'deescalated', ?, ?)",
                  (tid, "Resolvido pela escola: deixou de estar reportado à empresa de apoio (atualização manual)", now))
    c.commit()
    print(f"\n{len(done)} pedido(s) deixaram de estar marcados como reportados.")
elif done:
    print("\n(Para deixar de os considerar reportados, corra outra vez com --marcar.)")
