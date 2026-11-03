from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class JobRecord:
    source: str
    source_job_id: str | None = None
    url: str | None = None
    title: str | None = None
    company: str | None = None
    location: str | None = None
    contract_type: str | None = None
    experience_level: str | None = None
    work_mode: str | None = None
    description: str | None = None
    requirements: str | None = None
    skills: str | None = None
    published_at: str | None = None
    first_seen_at: str | None = None
    last_seen_at: str | None = None
    source_updated_at: str | None = None
    status: str = "new"
    is_active: int = 1
    content_hash: str | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ApplicationRecord:
    company_name: str
    job_title: str | None = None
    recipient_email: str | None = None
    source: str | None = None
    original_offer_url: str | None = None
    subject: str | None = None
    body: str | None = None
    generation_status: str = "pending"
    sending_status: str = "not_sent"
    application_status: str = "new"
    gmail_message_id: str | None = None
    application_type: str | None = None
    opportunity_type: str | None = None
    target_position: str | None = None
    additional_instructions: str | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    sent_at: str | None = None
    last_error: str | None = None
    notes: str | None = None


@dataclass
class DocumentRecord:
    document_type: str
    file_name: str
    file_path: str
    status: str = "uploaded"
    metadata: dict[str, Any] | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
