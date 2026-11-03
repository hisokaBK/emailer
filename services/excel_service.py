from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd

from config.constants import ALLOWED_EXCEL_EXTENSIONS
from services.validation_service import is_valid_email


def validate_excel_file(file_path: str | Path) -> dict:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError("Le fichier Excel est introuvable.")
    if path.suffix.lower().lstrip(".") not in {ext.lstrip(".") for ext in ALLOWED_EXCEL_EXTENSIONS}:
        raise ValueError("Le fichier doit être un fichier Excel (.xlsx ou .xls).")
    return {"path": str(path), "name": path.name, "size_bytes": path.stat().st_size}


def read_excel_sheet(file_path: str | Path, sheet_name: str | None = None) -> pd.DataFrame:
    dataframe = pd.read_excel(file_path, sheet_name=sheet_name)
    return dataframe.fillna("")


def read_excel_upload(content: bytes, sheet_name: str | None = None) -> pd.DataFrame:
    if not content:
        raise ValueError("Le fichier Excel est vide.")
    return pd.read_excel(BytesIO(content), sheet_name=sheet_name).fillna("")


def detect_upload_sheets(content: bytes) -> list[str]:
    if not content:
        raise ValueError("Le fichier Excel est vide.")
    return pd.ExcelFile(BytesIO(content)).sheet_names


def detect_sheets(file_path: str | Path) -> list[str]:
    workbook = pd.ExcelFile(file_path)
    return workbook.sheet_names


def map_columns(df: pd.DataFrame, mapping: dict[str, str] | None = None) -> list[dict]:
    mapping = mapping or {
        "company_name": "Company name",
        "email": "Email",
        "website": "Website",
        "activity": "Business activity",
        "city": "City",
        "contact_person": "Contact person",
        "notes": "Notes",
    }
    rows = []
    allowed_headers = {key: value for key, value in mapping.items() if value in df.columns}
    for _, row in df.iterrows():
        record = {}
        for field_name, column_label in allowed_headers.items():
            value = row.get(column_label, "")
            record[field_name] = str(value).strip() if not pd.isna(value) else ""
        rows.append(record)
    return rows


def clean_company_rows(rows: list[dict]) -> list[dict]:
    cleaned = []
    for row in rows:
        company = (row.get("company_name") or row.get("Company name") or "").strip()
        email = (row.get("email") or row.get("Email") or "").strip()
        if not company:
            continue
        cleaned.append({
            "company_name": company,
            "email": email,
            "website": (row.get("website") or row.get("Website") or "").strip(),
            "activity": (row.get("activity") or row.get("Business activity") or "").strip(),
            "city": (row.get("city") or row.get("City") or "").strip(),
            "contact_person": (row.get("contact_person") or row.get("Contact person") or "").strip(),
            "notes": (row.get("notes") or row.get("Notes") or "").strip(),
        })
    return cleaned


def validate_company_records(records: list[dict]) -> tuple[list[dict], list[str]]:
    valid = []
    errors = []
    for record in records:
        company = record.get("company_name", "").strip()
        email = record.get("email", "").strip()
        if not company:
            errors.append("Nom d'entreprise manquant dans une ligne du fichier Excel.")
            continue
        if not email or not is_valid_email(email):
            errors.append(f"Adresse e-mail invalide pour {company or 'une entreprise'}.")
            continue
        valid.append(record)
    return valid, errors
