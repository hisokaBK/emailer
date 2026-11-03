from __future__ import annotations

from io import BytesIO
from email.message import EmailMessage
from pathlib import Path

import pandas as pd
import pytest

import database.db as db
from database import repositories
from services.ai_generator import AIGenerator
from services.email_composer import compose_email
from services.gmail_service import GmailService
from services.pdf_service import save_uploaded_pdf
from services.job_fetcher import resolve_job_url
from services.excel_service import detect_upload_sheets, read_excel_upload
from services.validation_service import is_valid_email


@pytest.fixture
def isolated_database(monkeypatch):
    database_path = Path(__file__).with_name("_mvp_test.db")
    if database_path.exists():
        database_path.unlink()
    monkeypatch.setattr(db, "DB_PATH", database_path)
    db.initialize_database()
    try:
        yield
    finally:
        if database_path.exists():
            database_path.unlink()


def test_job_application_and_settings_persist(isolated_database):
    job = {"source": "test", "source_job_id": "job-1", "title": "D\u00e9veloppeur", "company": "Exemple"}
    job_id = repositories.upsert_job(job)
    assert repositories.upsert_job({**job, "title": "D\u00e9veloppeur Python"}) == job_id
    assert len(repositories.list_jobs()) == 1
    assert repositories.list_jobs()[0]["title"] == "D\u00e9veloppeur Python"

    company_id = repositories.save_company("Exemple")
    application_id = repositories.add_application({
        "company_id": company_id, "job_id": job_id, "subject": "Candidature",
        "body": "Bonjour", "generation_status": "prepared",
        "application_type": "Candidature spontanée – Stage",
        "opportunity_type": "Stage",
        "target_position": "Développeur Web",
    })
    repositories.update_application(application_id, sending_status="sent", gmail_message_id="message-1")
    application = repositories.list_applications()[0]
    assert application["company_name"] == "Exemple"
    assert application["job_title"] == "D\u00e9veloppeur Python"
    assert application["sending_status"] == "sent"
    assert application["gmail_message_id"] == "message-1"
    assert application["application_type"] == "Candidature spontanée – Stage"
    assert application["target_position"] == "Développeur Web"
    connection = db.get_connection()
    try:
        generated_email = connection.execute(
            "SELECT application_type FROM generated_emails WHERE application_id = ?",
            (application_id,),
        ).fetchone()
    finally:
        connection.close()
    assert generated_email["application_type"] == "Candidature spontanée – Stage"

    repositories.save_setting("email_signature", "Cordialement")
    assert repositories.get_setting("email_signature") == "Cordialement"


def test_email_composition_and_gmail_attachments():
    assert is_valid_email("recrutement@example.ma")
    assert not is_valid_email("not-an-email")
    final = compose_email("Candidature", "Bonjour, je joins mon CV.", "Cordialement", "recrutement@example.ma")
    assert "Subject: Candidature" in final
    assert "Cordialement" in final

    message = GmailService().build_message(
        "recrutement@example.ma", "Candidature", "Bonjour", [("cv.pdf", b"%PDF-test")]
    )
    assert isinstance(message, EmailMessage)
    assert message["To"] == "recrutement@example.ma"
    assert len(list(message.iter_attachments())) == 1
    assert list(message.iter_attachments())[0].get_filename() == "cv.pdf"
    with pytest.raises(ValueError):
        GmailService().build_message("invalid", "Candidature", "Bonjour", [])


def test_pdf_upload_rejects_bad_files():
    with pytest.raises(ValueError, match="format PDF"):
        save_uploaded_pdf(b"not a pdf", "cv.txt", "cv")
    with pytest.raises(ValueError, match="invalide"):
        save_uploaded_pdf(b"not a pdf", "cv.pdf", "cv")


def test_job_links_resolve_relative_urls():
    assert resolve_job_url("/emploi/123", "rekrute") == "https://www.rekrute.com/emploi/123"
    assert resolve_job_url("https://jobs.example.org/1", "rekrute") == "https://jobs.example.org/1"
    assert resolve_job_url("javascript:alert(1)", "rekrute") is None


def test_email_prompt_changes_with_application_purpose():
    generator = AIGenerator()
    internship_prompt = generator._build_prompt(
        "Entreprise Exemple",
        {"technical_skills": {"frontend": ["React"]}},
        application_type="Candidature spontanée – Stage",
    )
    offer_prompt = generator._build_prompt(
        "Entreprise Exemple",
        {"technical_skills": {"backend": ["Python"]}},
        offer_context={
            "is_published_offer": True,
            "title": "Stage Développeur Python",
            "description": "Participer au développement d'outils internes.",
            "requirements": "Python",
        },
        application_type="Réponse à une offre de stage",
        target_position="Stage Développeur Python",
    )
    assert "candidature spontanée pour un stage" in internship_prompt
    assert "Ne mentionne aucune offre publiée" in internship_prompt
    assert "Stage Développeur Python" in offer_prompt
    assert "Participer au développement d'outils internes." in offer_prompt
    assert "Réponds à l'offre de stage publiée" in offer_prompt


def test_fallback_body_respects_selected_purpose():
    generator = AIGenerator()
    body = generator._fallback_body(
        "Entreprise Exemple",
        {"technical_skills": {"backend": ["Python"]}},
        application_type="Candidature spontanée – Stage",
    )
    assert "candidature spontanée" in body
    assert "stage" in body
    assert "offre" not in body.lower()


def test_excel_upload_can_be_read_for_batch_generation():
    buffer = BytesIO()
    pd.DataFrame([
        {"Entreprise": "Exemple", "E-mail": "contact@example.ma"},
    ]).to_excel(buffer, index=False, sheet_name="Candidatures")
    content = buffer.getvalue()
    assert detect_upload_sheets(content) == ["Candidatures"]
    dataframe = read_excel_upload(content, "Candidatures")
    assert dataframe.iloc[0]["Entreprise"] == "Exemple"
    assert dataframe.iloc[0]["E-mail"] == "contact@example.ma"
