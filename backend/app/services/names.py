"""How people are named in emails and notifications — the same rules as the frontend (src/utils/names.ts):
first and last name, without the directory's suffixes ("Docente-520 - Biologia e Geologia", "-520"…), and for names
starting with Maria the second name instead: "Maria do Carmo de J.Valente Fortunato" → "M. Carmo Fortunato"."""
from __future__ import annotations

import re

_ROLE_SPLIT = re.compile(r"\s+(?:Docente|Não Docente|Nao Docente|Funcionári[oa])[-\s]", re.IGNORECASE)
_SMALL = {"e", "de", "da", "do", "das", "dos", "a", "o"}


def short_name(name: str | None) -> str:
    if not name:
        return ""
    base = _ROLE_SPLIT.split(name)[0].split(" - ")[0].strip()
    # Directory codes are dropped: group numbers ("Silva-520" → "Silva", "910"), codes with numbers ("GR910") and
    # short all-capital codes ("GR", "EE") — unless the whole name is written in capitals
    all_caps = base == base.upper()
    words = [
        w for w in (re.sub(r"[-–]\d.*$", "", w) for w in base.split())
        if w and not re.search(r"\d", w) and not (not all_caps and 2 <= len(w) <= 4 and w.isalpha() and w.isupper())
    ]
    if not words:
        return base
    last = next((w for w in reversed(words) if w.lower() not in _SMALL), words[-1])
    if words[0].lower() == "maria" and len(words) > 2:
        second = next((w for w in words[1:-1] if w.lower() not in _SMALL and "." not in w), None)
        if second:
            return f"M. {second} {last}"
    return f"{words[0]} {last}" if len(words) > 1 else words[0]


def short_names(names: str | None) -> str:
    """"Ana Admin, Maria Leonor … Serra Docente-510 - FQ" → "Ana Admin, M. Leonor Serra"."""
    return ", ".join(short_name(n) for n in (names or "").split(", ") if n.strip())
