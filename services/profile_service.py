from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from config.settings import PROFILE_PATH
from services.pdf_service import extract_profile_metadata


def build_default_profile() -> dict:
    return {
        "personal": {"full_name": "", "location": ""},
        "professional_summary": "",
        "education": [],
        "technical_skills": {
            "frontend": [],
            "backend": [],
            "databases": [],
            "data": [],
            "tools": [],
            "other": [],
        },
        "experience": [],
        "projects": [],
        "languages": [],
        "professional_objective": "",
        "other_relevant_information": [],
        "document_metadata": {"source_filename": "", "processed_at": "", "profile_version": "v1"},
    }


def parse_cv_text_to_profile(cv_text: str, source_filename: str = "cv.pdf") -> dict:
    profile = build_default_profile()
    text = cv_text.strip()
    if not text:
        return profile

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    profile["personal"]["full_name"] = lines[0] if lines else ""
    profile["professional_summary"] = text[:350]
    profile["technical_skills"]["frontend"] = ["HTML", "CSS", "JavaScript"] if "javascript" in text.lower() or "html" in text.lower() else []
    profile["technical_skills"]["backend"] = ["Python"] if "python" in text.lower() else []
    profile["technical_skills"]["databases"] = ["SQLite"] if "sqlite" in text.lower() else []
    profile["technical_skills"]["data"] = ["Analyse de données"] if "data" in text.lower() or "analyse" in text.lower() else []
    profile["technical_skills"]["tools"] = ["Git", "VS Code"] if "git" in text.lower() else []
    profile["professional_objective"] = "Recherche une opportunité en développement web ou logiciels adaptée à un profil junior et motivé."
    profile["document_metadata"] = extract_profile_metadata(source_filename)
    return profile


def save_profile(profile: dict, path: str | Path = PROFILE_PATH) -> Path:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    return file_path


def load_profile(path: str | Path = PROFILE_PATH) -> dict:
    file_path = Path(path)
    if not file_path.exists():
        return build_default_profile()
    data = json.loads(file_path.read_text(encoding="utf-8"))
    default = build_default_profile()
    default.update(data)
    if "technical_skills" in data:
        default["technical_skills"].update(data.get("technical_skills", {}))
    return default
