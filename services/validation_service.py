from __future__ import annotations

import re
from email.utils import parseaddr


def is_valid_email(email: str | None) -> bool:
    if not email:
        return False
    sanitized = email.strip()
    if len(sanitized) > 254:
        return False
    pattern = r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$"
    return bool(re.fullmatch(pattern, sanitized))


def normalize_email(email: str | None) -> str | None:
    if not email:
        return None
    value = email.strip().lower()
    return value if is_valid_email(value) else None


def ensure_valid_subject(subject: str | None) -> str:
    cleaned = (subject or "").strip()
    return cleaned or "Candidature professionnelle"


def sanitize_text(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.replace("\r", "\n").split())
