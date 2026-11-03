from __future__ import annotations

import base64
from email.message import EmailMessage
from pathlib import Path

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except Exception:  # pragma: no cover - optional dependency for real env
    Request = None
    Credentials = None
    InstalledAppFlow = None
    build = None

from config.settings import CREDENTIALS_DIR, get_env
from services.validation_service import ensure_valid_subject, is_valid_email


class GmailService:
    def __init__(self, token_path: str | Path | None = None, credentials_path: str | Path | None = None) -> None:
        self.token_path = Path(token_path or get_env("GMAIL_TOKEN_PATH", str(CREDENTIALS_DIR / "gmail_token.json")))
        self.credentials_path = Path(credentials_path or get_env("GMAIL_CREDENTIALS_PATH", str(CREDENTIALS_DIR / "google_credentials.json")))
        self.scopes = ["https://www.googleapis.com/auth/gmail.send"]
        self.user_email = None
        self.connected = False

    def is_configured(self) -> bool:
        return self.credentials_path.exists() and self.token_path.exists()

    def get_authorization_url(self) -> str:
        if InstalledAppFlow is None or Request is None:
            raise RuntimeError("Les biblioth\u00e8ques Google OAuth ne sont pas install\u00e9es.")
        flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_path), self.scopes)
        return flow.authorization_url(prompt="consent")[0]

    def authorize(self) -> bool:
        if InstalledAppFlow is None or build is None:
            raise RuntimeError("Les biblioth\u00e8ques Gmail ne sont pas install\u00e9es.")
        if not self.credentials_path.exists():
            raise FileNotFoundError("Le fichier des identifiants OAuth n'est pas pr\u00e9sent.")
        flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_path), self.scopes)
        creds = flow.run_local_server(port=0)
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_path.write_text(creds.to_json(), encoding="utf-8")
        self.connected = True
        return True

    def build_message(self, to_email: str, subject: str, body: str, attachments: list[tuple[str, bytes]]) -> EmailMessage:
        if not is_valid_email(to_email):
            raise ValueError("Adresse e-mail du destinataire invalide.")
        if not (body or "").strip():
            raise ValueError("Le corps du message est vide.")
        message = EmailMessage()
        message["To"] = to_email.strip()
        message["Subject"] = ensure_valid_subject(subject)
        message.set_content(body)
        for filename, content in attachments:
            if not isinstance(content, bytes):
                raise ValueError("Le contenu de chaque pi\u00e8ce jointe doit \u00eatre en octets.")
            message.add_attachment(content, maintype="application", subtype="pdf", filename=Path(filename).name)
        return message

    def send_message(self, to_email: str, subject: str, body: str, attachments: list[tuple[str, bytes]]) -> str:
        if build is None or Credentials is None:
            raise RuntimeError("L'API Gmail n'est pas disponible dans cet environnement.")
        if not self.is_configured():
            raise RuntimeError("L'authentification Gmail n'est pas pr\u00eate. Configurez les credentials puis autorisez le compte.")
        message = self.build_message(to_email, subject, body, attachments)
        encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        credentials = Credentials.from_authorized_user_file(str(self.token_path), self.scopes)
        if credentials.expired and credentials.refresh_token:
            if Request is None:
                raise RuntimeError("Le renouvellement du jeton Gmail n'est pas disponible.")
            credentials.refresh(Request())
            self.token_path.write_text(credentials.to_json(), encoding="utf-8")
        service = build("gmail", "v1", credentials=credentials)
        response = service.users().messages().send(userId="me", body={"raw": encoded}).execute()
        return response.get("id", "unknown")
