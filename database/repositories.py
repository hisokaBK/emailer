from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from database.db import get_connection


def save_setting(key: str, value: str | int | float | bool | None) -> None:
    conn = get_connection()
    payload = value if value is not None else ""
    try:
        conn.execute(
            "INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (key, str(payload), datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def get_setting(key: str, default: Any = None) -> Any:
    conn = get_connection()
    try:
        row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
        if row is None:
            return default
        return row["value"]
    finally:
        conn.close()


def upsert_job(job: dict[str, Any]) -> int:
    if not (job.get("source") or "").strip():
        raise ValueError("La source de l'offre est obligatoire.")
    if not (job.get("source_job_id") or "").strip():
        raise ValueError("L'identifiant de l'offre est obligatoire.")
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO jobs (
                source, source_job_id, url, title, company, location, contract_type, experience_level,
                work_mode, description, requirements, skills, published_at, first_seen_at, last_seen_at,
                source_updated_at, status, is_active, content_hash, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, source_job_id) DO UPDATE SET
                url=excluded.url,
                title=excluded.title,
                company=excluded.company,
                location=excluded.location,
                contract_type=excluded.contract_type,
                experience_level=excluded.experience_level,
                work_mode=excluded.work_mode,
                description=excluded.description,
                requirements=excluded.requirements,
                skills=excluded.skills,
                published_at=excluded.published_at,
                last_seen_at=excluded.last_seen_at,
                source_updated_at=excluded.source_updated_at,
                status=excluded.status,
                is_active=excluded.is_active,
                content_hash=excluded.content_hash,
                updated_at=excluded.updated_at
            """,
            (
                job.get("source"),
                job.get("source_job_id"),
                job.get("url"),
                job.get("title"),
                job.get("company"),
                job.get("location"),
                job.get("contract_type"),
                job.get("experience_level"),
                job.get("work_mode"),
                job.get("description"),
                job.get("requirements"),
                job.get("skills"),
                job.get("published_at"),
                job.get("first_seen_at") or datetime.now(timezone.utc).isoformat(),
                job.get("last_seen_at") or datetime.now(timezone.utc).isoformat(),
                job.get("source_updated_at"),
                job.get("status", "new"),
                job.get("is_active", 1),
                job.get("content_hash"),
                job.get("created_at") or datetime.now(timezone.utc).isoformat(),
                job.get("updated_at") or datetime.now(timezone.utc).isoformat(),
            ),
        )
        row = conn.execute(
            "SELECT id FROM jobs WHERE source = ? AND source_job_id = ?",
            (job.get("source"), job.get("source_job_id")),
        ).fetchone()
        conn.commit()
        return int(row["id"])
    finally:
        conn.close()


def list_jobs(limit: int = 50) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def add_application(payload: dict[str, Any]) -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO applications (
                company_id, job_id, recipient_email, subject, body, generation_status,
                sending_status, application_status, gmail_message_id, application_type,
                opportunity_type, target_position, additional_instructions, created_at, sent_at,
                last_error, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.get("company_id"),
                payload.get("job_id"),
                payload.get("recipient_email"),
                payload.get("subject"),
                payload.get("body"),
                payload.get("generation_status", "pending"),
                payload.get("sending_status", "not_sent"),
                payload.get("application_status", "new"),
                payload.get("gmail_message_id"),
                payload.get("application_type"),
                payload.get("opportunity_type"),
                payload.get("target_position"),
                payload.get("additional_instructions"),
                payload.get("created_at") or datetime.now(timezone.utc).isoformat(),
                payload.get("sent_at"),
                payload.get("last_error"),
                payload.get("notes"),
            ),
        )
        if payload.get("body"):
            company = conn.execute(
                "SELECT name FROM companies WHERE id = ?", (payload.get("company_id"),)
            ).fetchone()
            conn.execute(
                """
                INSERT INTO generated_emails (
                    application_id, company_name, recipient_email, subject, body,
                    application_type, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'generated', ?)
                """,
                (
                    cursor.lastrowid,
                    company["name"] if company else None,
                    payload.get("recipient_email"),
                    payload.get("subject"),
                    payload.get("body"),
                    payload.get("application_type"),
                    payload.get("created_at") or datetime.now(timezone.utc).isoformat(),
                ),
            )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def save_company(name: str) -> int:
    """Create or find a company record for an application."""
    cleaned_name = (name or "").strip()
    if not cleaned_name:
        raise ValueError("Le nom de l'entreprise est obligatoire.")
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO companies (name, created_at, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(name) DO UPDATE SET updated_at = excluded.updated_at",
            (cleaned_name, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
        )
        row = conn.execute("SELECT id FROM companies WHERE name = ?", (cleaned_name,)).fetchone()
        conn.commit()
        return int(row["id"])
    finally:
        conn.close()


def update_application(application_id: int, **fields: Any) -> None:
    allowed = {
        "recipient_email", "subject", "body", "generation_status", "sending_status",
        "application_status", "gmail_message_id", "application_type", "opportunity_type",
        "target_position", "additional_instructions", "sent_at", "last_error", "notes",
    }
    updates = {key: value for key, value in fields.items() if key in allowed}
    if not updates:
        return
    assignments = ", ".join(f"{key} = ?" for key in updates)
    conn = get_connection()
    try:
        cursor = conn.execute(
            f"UPDATE applications SET {assignments} WHERE id = ?",
            (*updates.values(), application_id),
        )
        if cursor.rowcount == 0:
            raise ValueError("La candidature n'existe pas.")
        if "body" in updates:
            application = conn.execute(
                """
                SELECT applications.*, companies.name AS company_name
                FROM applications
                LEFT JOIN companies ON companies.id = applications.company_id
                WHERE applications.id = ?
                """,
                (application_id,),
            ).fetchone()
            conn.execute(
                """
                INSERT INTO generated_emails (
                    application_id, company_name, recipient_email, subject, body,
                    application_type, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'generated', ?)
                """,
                (
                    application_id,
                    application["company_name"] if application else None,
                    application["recipient_email"] if application else None,
                    application["subject"] if application else None,
                    application["body"] if application else None,
                    application["application_type"] if application else None,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        conn.commit()
    finally:
        conn.close()


def get_application(application_id: int) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_applications() -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT applications.*, companies.name AS company_name, jobs.title AS job_title "
            "FROM applications "
            "LEFT JOIN companies ON companies.id = applications.company_id "
            "LEFT JOIN jobs ON jobs.id = applications.job_id "
            "ORDER BY applications.created_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def record_document(document_type: str, file_name: str, file_path: str, metadata: dict[str, Any] | None = None) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO uploaded_documents (document_type, file_name, file_path, status, metadata, created_at) VALUES (?, ?, ?, 'uploaded', ?, ?)",
            (document_type, file_name, file_path, json.dumps(metadata or {}), datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def get_document_status(document_type: str) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM uploaded_documents WHERE document_type = ? ORDER BY created_at DESC LIMIT 1",
            (document_type,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
