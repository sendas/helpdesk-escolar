"""What each person wants to be told about, by email and by phone/browser notification (push).

Only the choices that differ from the defaults are stored (User.notification_prefs, JSON), so new kinds of
notification get sensible defaults for everyone."""
from __future__ import annotations

import json

from app.models.user import User, UserRole

# key -> (label, description, channels)
KINDS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "assigned": ("Tickets atribuídos a mim", "Quando um ticket lhe é atribuído, a si ou a um grupo seu.", ("email", "push")),
    "replies": ("Respostas", "Novas respostas nos tickets que fez, que tem atribuídos ou que segue.", ("email", "push")),
    "private": ("Mensagens privadas", "Mensagens privadas que lhe enviam dentro de um ticket.", ("email", "push")),
    "status": ("Mudanças de estado", "Quando um ticket fica a aguardar a sua resposta, é resolvido ou fechado.", ("email", "push")),
    "mentions": ("Menções", "Quando alguém o menciona com @ numa resposta ou nota.", ("email", "push")),
    "reminders": ("Lembretes", "Os lembretes que marcou nos tickets.", ("email", "push")),
    "chat": ("Chat", "Mensagens no chat da equipa e do apoio ao vivo quando não está na aplicação.", ("push",)),
}


def _is_staff(user: User) -> bool:
    return user.role in {UserRole.ADMIN, UserRole.TECHNICIAN} or bool(user.is_technician)


def defaults(user: User) -> dict[str, dict[str, bool]]:
    staff = _is_staff(user)
    out = {kind: {ch: True for ch in channels} for kind, (_, _, channels) in KINDS.items()}
    # The support team follows state changes in the app itself; requesters want to know
    out["status"] = {"email": not staff, "push": False}
    return out


def _saved(user: User) -> dict:
    try:
        data = json.loads(user.notification_prefs or "{}")
        return data if isinstance(data, dict) else {}
    except (TypeError, ValueError):
        return {}


def get_prefs(user: User) -> dict[str, dict[str, bool]]:
    prefs = defaults(user)
    for kind, channels in _saved(user).items():
        if kind in prefs and isinstance(channels, dict):
            for ch, on in channels.items():
                if ch in prefs[kind]:
                    prefs[kind][ch] = bool(on)
    return prefs


def set_prefs(user: User, wanted: dict) -> dict[str, dict[str, bool]]:
    base = defaults(user)
    diff: dict[str, dict[str, bool]] = {}
    for kind, channels in (wanted or {}).items():
        if kind not in base or not isinstance(channels, dict):
            continue
        for ch, on in channels.items():
            if ch in base[kind] and bool(on) != base[kind][ch]:
                diff.setdefault(kind, {})[ch] = bool(on)
    user.notification_prefs = json.dumps(diff) if diff else None
    return get_prefs(user)


def wants(user: User | None, kind: str, channel: str) -> bool:
    if user is None:
        return True
    return get_prefs(user).get(kind, {}).get(channel, False)


def catalog() -> list[dict]:
    return [{"key": k, "label": label, "description": desc, "channels": list(ch)} for k, (label, desc, ch) in KINDS.items()]
