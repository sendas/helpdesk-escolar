"""Real-time channel (WebSocket, with HTTP polling as a fallback when a proxy blocks WebSockets).

Everything lives in memory: the backend runs as a single process. Events are delivered per user, and every event
is also kept in a short per-user buffer so polling clients (and WebSockets that reconnect) catch up.

Ticket events never carry content: they only tell the browser to reload the ticket through the normal API, which
already applies every permission rule (private messages, internal notes, roles). Chat events carry the message,
but only ever go to members of that conversation.
"""
import asyncio
import itertools
import time
from collections import defaultdict, deque

BUFFER_SIZE = 200
BUFFER_TTL = 600          # seconds an event stays available for polling clients
POLL_ONLINE_TTL = 25      # a polling client counts as online for this long after its last poll
VIEW_TTL = 40             # a "viewing this ticket" mark expires unless refreshed

_seq = itertools.count(1)
_buffers: dict[int, deque] = defaultdict(lambda: deque(maxlen=BUFFER_SIZE))
_sockets: dict[int, set] = defaultdict(set)          # user_id -> set[asyncio.Queue]
_poll_seen: dict[int, float] = {}                    # user_id -> last poll time
_viewers: dict[int, dict[int, float]] = defaultdict(dict)   # ticket_id -> {user_id: last_seen}
_names: dict[int, str] = {}


def remember_name(user_id: int, name: str) -> None:
    _names[user_id] = name


def is_online(user_id: int) -> bool:
    return bool(_sockets.get(user_id)) or time.time() - _poll_seen.get(user_id, 0) < POLL_ONLINE_TTL


def online_users() -> set[int]:
    now = time.time()
    return {u for u, qs in _sockets.items() if qs} | {u for u, t in _poll_seen.items() if now - t < POLL_ONLINE_TTL}


def current_seq() -> int:
    """Sequence number a new client starts from (it only wants events from now on)."""
    return next(_seq)


def publish(user_ids, event: dict) -> None:
    now = time.time()
    for uid in {u for u in user_ids if u}:
        item = {**event, "seq": next(_seq)}
        buf = _buffers[uid]
        buf.append((now, item))
        while buf and now - buf[0][0] > BUFFER_TTL:
            buf.popleft()
        for q in list(_sockets.get(uid, ())):
            try:
                q.put_nowait(item)
            except asyncio.QueueFull:
                pass


def events_after(user_id: int, after: int) -> list[dict]:
    return [item for _, item in _buffers.get(user_id, ()) if item["seq"] > after]


def mark_polled(user_id: int) -> None:
    _poll_seen[user_id] = time.time()


def register(user_id: int) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=500)
    _sockets[user_id].add(q)
    return q


def unregister(user_id: int, q: asyncio.Queue) -> None:
    _sockets[user_id].discard(q)
    if not _sockets[user_id]:
        _sockets.pop(user_id, None)
        # Drop the user from every ticket they were viewing
        for ticket_id in [t for t, v in _viewers.items() if user_id in v]:
            leave_ticket(user_id, ticket_id)


# ── Who is looking at a ticket ──────────────────────────────────────────

def ticket_viewers(ticket_id: int) -> set[int]:
    now = time.time()
    viewers = _viewers.get(ticket_id, {})
    for uid in [u for u, t in viewers.items() if now - t > VIEW_TTL]:
        viewers.pop(uid, None)
    return set(viewers)


def _broadcast_viewers(ticket_id: int) -> None:
    viewers = ticket_viewers(ticket_id)
    payload = [{"id": uid, "name": _names.get(uid, "")} for uid in sorted(viewers)]
    publish(viewers, {"type": "ticket.viewers", "ticket_id": ticket_id, "viewers": payload})


def view_ticket(user_id: int, ticket_id: int) -> None:
    is_new = user_id not in ticket_viewers(ticket_id)
    _viewers[ticket_id][user_id] = time.time()
    if is_new:
        _broadcast_viewers(ticket_id)


def leave_ticket(user_id: int, ticket_id: int) -> None:
    if _viewers.get(ticket_id, {}).pop(user_id, None) is not None:
        _broadcast_viewers(ticket_id)


def ticket_changed(ticket_id: int, related_ids=()) -> None:
    """Ask everyone looking at the ticket to reload it, and the people linked to it to refresh lists/counters."""
    viewers = ticket_viewers(ticket_id)
    publish(viewers, {"type": "ticket.changed", "ticket_id": ticket_id})
    publish(set(related_ids) - viewers, {"type": "tickets.changed", "ticket_id": ticket_id})
