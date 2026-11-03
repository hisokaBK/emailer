from __future__ import annotations

from datetime import datetime

from config.constants import DEFAULT_BATCH_PAUSE_SECONDS
from services.gmail_service import GmailService


class EmailSender:
    def __init__(self, gmail_service: GmailService | None = None, pause_seconds: int = DEFAULT_BATCH_PAUSE_SECONDS) -> None:
        self.gmail_service = gmail_service or GmailService()
        self.pause_seconds = pause_seconds

    def send_batch(self, drafts: list[dict]) -> list[dict]:
        sent_results = []
        for item in drafts:
            try:
                message_id = self.gmail_service.send_message(
                    to_email=item["recipient_email"],
                    subject=item["subject"],
                    body=item["body"],
                    attachments=[
                        (item.get("cv_filename", "cv.pdf"), item.get("cv_content", b"")),
                        (item.get("cover_letter_filename", "cover_letter.pdf"), item.get("cover_letter_content", b"")),
                    ],
                )
                sent_results.append({
                    "recipient_email": item["recipient_email"],
                    "status": "sent",
                    "gmail_message_id": message_id,
                    "sent_at": datetime.utcnow().isoformat(),
                })
            except Exception as exc:  # pragma: no cover - network layer can fail in local environment
                sent_results.append({
                    "recipient_email": item["recipient_email"],
                    "status": "error",
                    "error": str(exc),
                    "sent_at": datetime.utcnow().isoformat(),
                })
        return sent_results
