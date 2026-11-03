from __future__ import annotations

from io import BytesIO
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader

from config.constants import MAX_UPLOAD_SIZE_BYTES
from config.settings import CV_DIR, COVER_LETTER_DIR
from services.validation_service import sanitize_text


def validate_pdf_file(file_path: str | Path, max_size_bytes: int = MAX_UPLOAD_SIZE_BYTES) -> dict:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError("Le fichier PDF est introuvable.")
    if path.suffix.lower() != ".pdf":
        raise ValueError("Le fichier doit être au format PDF.")
    size = path.stat().st_size
    if size <= 0:
        raise ValueError("Le fichier PDF est vide.")
    if size > max_size_bytes:
        raise ValueError(f"Le fichier PDF dépasse la taille maximale autorisée ({max_size_bytes} octets).")
    return {"path": str(path), "size_bytes": size, "size_mb": round(size / (1024 * 1024), 2)}


def save_pdf_document(file_path: str | Path, document_type: str, target_dir: str | Path | None = None) -> Path:
    source_path = Path(file_path)
    target = Path(target_dir or (CV_DIR if document_type == "cv" else COVER_LETTER_DIR))
    target.mkdir(parents=True, exist_ok=True)
    destination = target / source_path.name
    if destination.exists():
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        destination = target / f"{source_path.stem}_{timestamp}{source_path.suffix}"
    destination.write_bytes(source_path.read_bytes())
    return destination


def save_uploaded_pdf(content: bytes, file_name: str, document_type: str) -> Path:
    """Validate and persist an uploaded PDF without using a temporary file."""
    if document_type not in {"cv", "cover_letter"}:
        raise ValueError("Type de document non pris en charge.")
    safe_name = Path(file_name).name
    if Path(safe_name).suffix.lower() != ".pdf":
        raise ValueError("Le fichier doit \u00eatre au format PDF.")
    if not content:
        raise ValueError("Le fichier PDF est vide.")
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise ValueError(f"Le fichier PDF d\u00e9passe la taille maximale autoris\u00e9e ({MAX_UPLOAD_SIZE_BYTES} octets).")
    try:
        reader = PdfReader(BytesIO(content))
        if not reader.pages:
            raise ValueError("Le document PDF ne contient aucune page.")
    except Exception as exc:
        if isinstance(exc, ValueError):
            raise
        raise ValueError("Le document PDF est invalide ou illisible.") from exc

    target_dir = CV_DIR if document_type == "cv" else COVER_LETTER_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / safe_name
    if destination.exists():
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        destination = target_dir / f"{Path(safe_name).stem}_{timestamp}.pdf"
    destination.write_bytes(content)
    return destination


def extract_text_from_pdf(file_path: str | Path) -> str:
    reader = PdfReader(str(file_path))
    return sanitize_text("\n".join(page.extract_text() or "" for page in reader.pages))


def extract_text_from_pdf_bytes(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    return sanitize_text("\n".join(page.extract_text() or "" for page in reader.pages))


def has_useful_text(text: str) -> bool:
    cleaned = " ".join(text.split())
    return len(cleaned) >= 80


def extract_profile_metadata(file_name: str) -> dict:
    return {
        "source_filename": file_name,
        "processed_at": datetime.utcnow().isoformat(),
        "profile_version": "v1",
    }
