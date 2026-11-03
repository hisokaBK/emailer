from __future__ import annotations

from services.validation_service import ensure_valid_subject, is_valid_email


def compose_email(subject: str, body: str, signature: str, recipient_email: str) -> str:
    if not is_valid_email(recipient_email):
        raise ValueError("Adresse e-mail du destinataire invalide.")
    cleaned_subject = ensure_valid_subject(subject)
    cleaned_body = (body or "").strip()
    if not cleaned_body:
        raise ValueError("Le corps du message est vide.")
    cleaned_signature = (signature or "").strip()
    if not cleaned_signature:
        raise ValueError("La signature n'est pas définie.")
    if "pièces jointes" not in cleaned_body.lower():
        cleaned_body += "\n\nVous trouverez en pièces jointes mon CV ainsi que ma lettre de motivation."
    final = (
        f"Subject: {cleaned_subject}\n\n"
        f"{cleaned_body}\n\n"
        f"{cleaned_signature}\n"
    )
    return final


def validate_final_email(final_email: str, recipient_email: str, subject: str) -> dict:
    if not final_email or "Subject:" not in final_email:
        raise ValueError("Le message final est vide ou incomplet.")
    if not is_valid_email(recipient_email):
        raise ValueError("Le destinataire n'est pas valide.")
    subject_line = ensure_valid_subject(subject)
    if subject_line not in final_email:
        raise ValueError("Le sujet final n'est pas présent.")
    if "Cordialement" not in final_email and "Cordialement," not in final_email:
        raise ValueError("La signature n'est pas présente.")
    return {"valid": True, "subject": subject_line, "recipient": recipient_email}
