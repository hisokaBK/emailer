from __future__ import annotations

import sqlite3
from pathlib import Path

from config.settings import DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                source_job_id TEXT,
                url TEXT,
                title TEXT,
                company TEXT,
                location TEXT,
                contract_type TEXT,
                experience_level TEXT,
                work_mode TEXT,
                description TEXT,
                requirements TEXT,
                skills TEXT,
                published_at TEXT,
                first_seen_at TEXT,
                last_seen_at TEXT,
                source_updated_at TEXT,
                status TEXT DEFAULT 'new',
                is_active INTEGER DEFAULT 1,
                content_hash TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(source, source_job_id)
            );

            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                website TEXT,
                activity TEXT,
                city TEXT,
                contact_person TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(name)
            );

            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                job_id INTEGER,
                recipient_email TEXT,
                subject TEXT,
                body TEXT,
                generation_status TEXT DEFAULT 'pending',
                sending_status TEXT DEFAULT 'not_sent',
                application_status TEXT DEFAULT 'new',
                gmail_message_id TEXT,
                application_type TEXT,
                opportunity_type TEXT,
                target_position TEXT,
                additional_instructions TEXT,
                created_at TEXT NOT NULL,
                sent_at TEXT,
                last_error TEXT,
                notes TEXT,
                FOREIGN KEY(company_id) REFERENCES companies(id),
                FOREIGN KEY(job_id) REFERENCES jobs(id)
            );

            CREATE TABLE IF NOT EXISTS generated_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id INTEGER,
                company_name TEXT,
                recipient_email TEXT,
                subject TEXT,
                body TEXT,
                application_type TEXT,
                status TEXT DEFAULT 'generated',
                created_at TEXT NOT NULL,
                FOREIGN KEY(application_id) REFERENCES applications(id)
            );

            CREATE TABLE IF NOT EXISTS sending_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id INTEGER,
                gmail_message_id TEXT,
                recipient_email TEXT,
                status TEXT,
                sent_at TEXT NOT NULL,
                details TEXT,
                FOREIGN KEY(application_id) REFERENCES applications(id)
            );

            CREATE TABLE IF NOT EXISTS source_refresh_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                refreshed_at TEXT NOT NULL,
                job_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'ok'
            );

            CREATE TABLE IF NOT EXISTS uploaded_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_type TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                status TEXT DEFAULT 'uploaded',
                metadata TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS app_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value TEXT,
                updated_at TEXT NOT NULL
            );
            """
        )
        application_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(applications)").fetchall()
        }
        for column in ("application_type", "opportunity_type", "target_position", "additional_instructions"):
            if column not in application_columns:
                conn.execute(f"ALTER TABLE applications ADD COLUMN {column} TEXT")
        generated_email_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(generated_emails)").fetchall()
        }
        if "application_type" not in generated_email_columns:
            conn.execute("ALTER TABLE generated_emails ADD COLUMN application_type TEXT")
        conn.commit()
    finally:
        conn.close()


initialize_database()
