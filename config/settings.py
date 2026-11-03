from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env", override=False)

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
CV_DIR = UPLOADS_DIR / "cv"
COVER_LETTER_DIR = UPLOADS_DIR / "cover_letters"
EXCEL_DIR = UPLOADS_DIR / "excel"
CREDENTIALS_DIR = BASE_DIR / "credentials"
EXPORTS_DIR = BASE_DIR / "exports"
LOGS_DIR = BASE_DIR / "logs"
DB_PATH = BASE_DIR / "auto_candidature.db"
PROFILE_PATH = DATA_DIR / "profile.json"
COVER_LETTER_CONTEXT_PATH = DATA_DIR / "cover_letter_context.json"
APP_SETTINGS_PATH = DATA_DIR / "app_settings.json"


def get_env(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


def get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default
