from __future__ import annotations

import hashlib
import re
from typing import Iterable

from services.validation_service import normalize_email


def normalize_company_name(value: str | None) -> str:
    if not value:
        return ""
    normalized = re.sub(r"\s+", " ", value.strip().lower())
    return normalized.replace("&", "et")


def make_job_fingerprint(title: str | None, company: str | None, location: str | None) -> str:
    source = "|".join([normalize_company_name(company), normalize_company_name(title), normalize_company_name(location)])
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def normalize_url(url: str | None) -> str | None:
    if not url:
        return None
    return url.strip().lower().rstrip("/")


def is_duplicate_company_email(candidate: str | None, seen: Iterable[str]) -> bool:
    normalized = normalize_email(candidate)
    if not normalized:
        return True
    return normalized in {normalize_email(item) for item in seen if item}
