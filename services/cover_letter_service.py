from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config.settings import COVER_LETTER_CONTEXT_PATH


def load_cover_letter_context(path: str | Path = COVER_LETTER_CONTEXT_PATH) -> dict[str, Any]:
    context_path = Path(path)
    if not context_path.exists():
        return {}
    data = json.loads(context_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Le contexte de lettre de motivation doit être un objet JSON.")
    return data


def save_cover_letter_context(context: dict[str, Any], path: str | Path = COVER_LETTER_CONTEXT_PATH) -> Path:
    allowed_fields = {
        "professional_objective",
        "preferred_opportunity",
        "professional_positioning",
        "main_arguments",
        "writing_style",
        "professional_strengths",
    }
    normalized = {
        field: str(context.get(field, ""))
        for field in allowed_fields
    }
    context_path = Path(path)
    context_path.parent.mkdir(parents=True, exist_ok=True)
    context_path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return context_path
