from __future__ import annotations

import base64
import logging
import os
import tempfile
from email.message import EmailMessage
from io import BytesIO
from pathlib import Path
from typing import TypeAlias

try:
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:  # pragma: no cover - dependencies are declared in requirements.txt
    RefreshError = Exception
    Request = None
    Credentials = None
    InstalledAppFlow = None
    build = None
    HttpError = Exception

from pypdf import PdfReader

from config.settings import BASE_DIR, CREDENTIALS_DIR, get_env
from services.validation_service import ensure_valid_subject, is_valid_email

logger = logging.getLogger(__name__)
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
Attachment: TypeAlias = Path | str | tuple[str, bytes] | tuple[str, Path]


class GmailError(RuntimeError):
    """Safe, user-facing Gmail integration error."""


class GmailReauthorizationRequired(GmailError):
    """The stored token cannot be repaired without user consent."""


class GmailService:
    def __init__(
        self,
        token_path: str | Path | None = None,
        credentials_path: str | Path | None = None,
    ) -> None:
        self.token_path = self._resolve_path(
            token_path or get_env("GMAIL_TOKEN_PATH", str(CREDENTIALS_DIR / "gmail_token.json"))
        )
        self.credentials_path = self._resolve_path(
            credentials_path
            or get_env("GMAIL_CREDENTIALS_PATH", str(CREDENTIALS_DIR / "google_credentials.json"))
        )
        self.scopes = [GMAIL_SEND_SCOPE]

    @staticmethod
    def _resolve_path(path: str | Path | None) -> Path:
        resolved = Path(path or "")
        if not resolved.is_absolute():
            resolved = BASE_DIR / resolved
        return resolved.resolve()

    def is_configured(self) -> bool:
        return self.credentials_path.is_file()

    def is_authenticated(self) -> bool:
        try:
            self._get_credentials()
            return True
        except GmailError:
            return False

    def authentication_status(self) -> tuple[bool, str | None]:
        try:
            self._get_credentials()
            return True, None
        except GmailError as exc:
            return False, str(exc)

    def authorize(self) -> bool:
        """Reuse a valid token or start the local desktop OAuth flow."""
        self._require_oauth_libraries()
        self._validate_oauth_file()

        if self.token_path.is_file():
            try:
                self._get_credentials()
                return True
            except GmailReauthorizationRequired:
                try:
                    self.token_path.unlink()
                except OSError:
                    raise GmailError(
                        "Le jeton Gmail doit être renouvelé, mais il est impossible de le remplacer. "
                        "Supprimez-le depuis Paramètres puis réessayez."
                    ) from None

        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_path),
                self.scopes,
            )
            credentials = flow.run_local_server(
                host="localhost",
                port=0,
                open_browser=True,
                authorization_prompt_message="",
                success_message="Autorisation Gmail terminée. Vous pouvez revenir à Auto Candidature.",
                access_type="offline",
                prompt="consent select_account",
            )
        except Exception as exc:
            logger.warning("Gmail OAuth desktop flow failed (%s).", type(exc).__name__)
            raise GmailError(
                "La connexion Google n'a pas abouti. Vérifiez le réseau, le navigateur, "
                "le statut OAuth du projet et la liste des utilisateurs de test."
            ) from None

        if not self._has_required_scope(credentials):
            raise GmailError("L'autorisation obtenue ne comprend pas le droit d'envoi Gmail requis.")
        self._save_credentials(credentials)
        return True

    def disconnect(self) -> bool:
        """Remove only this app's local token; Google-side access can be revoked separately."""
        if not self.token_path.exists():
            return False
        try:
            self.token_path.unlink()
        except OSError:
            logger.warning("Could not remove local Gmail token (%s).", type(OSError).__name__)
            raise GmailError("Impossible de supprimer le jeton Gmail local.") from None
        return True

    def get_service(self):
        if build is None:
            raise GmailError("Les bibliothèques Google nécessaires ne sont pas installées.")
        credentials = self._get_credentials()
        try:
            return build("gmail", "v1", credentials=credentials, cache_discovery=False)
        except Exception as exc:
            logger.warning("Gmail API client initialization failed (%s).", type(exc).__name__)
            raise GmailError(
                "Impossible d'initialiser Gmail. Vérifiez que l'API Gmail est activée dans Google Cloud."
            ) from None

    def get_authorization_url(self) -> str:
        """Retained for callers needing a URL; the normal Streamlit flow uses authorize()."""
        self._require_oauth_libraries()
        self._validate_oauth_file()
        try:
            flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_path), self.scopes)
            authorization_url, _ = flow.authorization_url(
                access_type="offline",
                include_granted_scopes="false",
                prompt="consent select_account",
            )
            return authorization_url
        except Exception as exc:
            logger.warning("Gmail authorization URL creation failed (%s).", type(exc).__name__)
            raise GmailError("Impossible de préparer l'autorisation Google.") from None

    def _get_credentials(self):
        self._require_oauth_libraries()
        self._validate_oauth_file()
        if not self.token_path.is_file():
            raise GmailError("Gmail n'est pas encore connecté. Utilisez « Connecter Gmail ».")

        try:
            credentials = Credentials.from_authorized_user_file(
                str(self.token_path),
            )
        except Exception as exc:
            logger.warning("Gmail token could not be loaded (%s).", type(exc).__name__)
            raise GmailReauthorizationRequired(
                "Le jeton Gmail local est illisible ou invalide. Déconnectez puis reconnectez Gmail."
            ) from None

        if not self._has_required_scope(credentials):
            raise GmailReauthorizationRequired(
                "Le jeton actuel n'a pas le droit d'envoi Gmail requis. Déconnectez puis reconnectez Gmail."
            )
        if credentials.valid:
            return credentials
        if not credentials.expired:
            raise GmailError("Le jeton Gmail n'est pas valide. Reconnectez Gmail depuis Paramètres.")
        if not credentials.refresh_token:
            raise GmailReauthorizationRequired(
                "L'autorisation Gmail a expiré sans jeton de renouvellement. "
                "Déconnectez puis reconnectez Gmail."
            )
        if Request is None:
            raise GmailError("Le renouvellement Gmail est indisponible : bibliothèques Google manquantes.")

        try:
            credentials.refresh(Request())
        except RefreshError as exc:
            logger.warning("Gmail token refresh failed (%s).", type(exc).__name__)
            raise GmailReauthorizationRequired(
                "Le jeton Gmail a expiré ou a été révoqué. Déconnectez puis reconnectez le compte."
            ) from None
        except Exception as exc:
            logger.warning("Gmail token refresh failed (%s).", type(exc).__name__)
            raise GmailError(
                "Impossible de renouveler le jeton Gmail pour le moment. Vérifiez le réseau puis réessayez."
            ) from None
        self._save_credentials(credentials)
        return credentials

    def _validate_oauth_file(self) -> None:
        if not self.credentials_path.is_file():
            raise GmailError(
                "Le fichier credentials/google_credentials.json est introuvable. "
                "Placez-y le fichier OAuth Desktop téléchargé depuis Google Cloud."
            )
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_path),
                self.scopes,
            )
            if getattr(flow, "client_type", None) != "installed":
                raise ValueError("OAuth client is not a desktop application")
            if not getattr(flow, "client_config", {}).get("client_id"):
                raise ValueError("Missing OAuth client ID")
        except Exception as exc:
            logger.warning("Gmail OAuth credentials validation failed (%s).", type(exc).__name__)
            raise GmailError(
                "Le fichier de credentials OAuth est invalide. Vérifiez qu'il s'agit bien "
                "d'identifiants de type application de bureau."
            ) from None

    @staticmethod
    def _has_required_scope(credentials) -> bool:
        if not credentials:
            return False
        scopes = getattr(credentials, "scopes", None)
        if scopes is None:
            return False
        return set(scopes) == {GMAIL_SEND_SCOPE}

    def _require_oauth_libraries(self) -> None:
        if Credentials is None or InstalledAppFlow is None or Request is None:
            raise GmailError("Les bibliothèques Google OAuth ne sont pas installées.")

    def _save_credentials(self, credentials) -> None:
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        token_json = credentials.to_json()
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.token_path.parent,
                prefix=f".{self.token_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as token_file:
                temporary_path = Path(token_file.name)
                token_file.write(token_json)
                token_file.flush()
                os.fsync(token_file.fileno())
            try:
                temporary_path.chmod(0o600)
            except OSError:
                pass
            temporary_path.replace(self.token_path)
            try:
                self.token_path.chmod(0o600)
            except OSError:
                pass
        except OSError as exc:
            logger.warning("Gmail token could not be saved (%s).", type(exc).__name__)
            raise GmailError("Impossible d'enregistrer le jeton Gmail sur cet ordinateur.") from None
        finally:
            if temporary_path and temporary_path.exists():
                temporary_path.unlink(missing_ok=True)

    def build_message(
        self,
        to_email: str,
        subject: str,
        body: str,
        attachments: list[Attachment] | None = None,
    ) -> EmailMessage:
        if not is_valid_email(to_email):
            raise ValueError("Adresse e-mail du destinataire invalide.")
        if not (body or "").strip():
            raise ValueError("Le corps du message est vide.")

        message = EmailMessage()
        message["To"] = to_email.strip()
        message["Subject"] = ensure_valid_subject(subject)
        message.set_content(body, charset="utf-8")
        for attachment in attachments or []:
            filename, content = self._read_pdf_attachment(attachment)
            message.add_attachment(
                content,
                maintype="application",
                subtype="pdf",
                filename=filename,
            )
        return message

    @staticmethod
    def _read_pdf_attachment(attachment: Attachment) -> tuple[str, bytes]:
        if isinstance(attachment, tuple):
            filename, source = attachment
            filename = Path(filename).name
            if isinstance(source, Path):
                path = source
                if not path.is_file():
                    raise ValueError(f"La pièce jointe {filename} est introuvable.")
                content = path.read_bytes()
            elif isinstance(source, bytes):
                content = source
            else:
                raise ValueError("Format de pièce jointe non pris en charge.")
        else:
            path = Path(attachment)
            if not path.is_file():
                raise ValueError(f"La pièce jointe {path.name} est introuvable.")
            filename = path.name
            content = path.read_bytes()

        if Path(filename).suffix.lower() != ".pdf":
            raise ValueError(f"La pièce jointe {filename} doit être un fichier PDF.")
        if not content.startswith(b"%PDF-"):
            raise ValueError(f"La pièce jointe {filename} n'est pas un PDF valide.")
        try:
            reader = PdfReader(BytesIO(content), strict=True)
            if not reader.pages:
                raise ValueError("Le PDF ne contient aucune page.")
        except Exception as exc:
            raise ValueError(f"La pièce jointe {filename} est illisible ou corrompue.") from None
        return filename, content

    def send_message(
        self,
        to_email: str,
        subject: str,
        body: str,
        attachments: list[Attachment] | None = None,
    ) -> str:
        message = self.build_message(to_email, subject, body, attachments)
        service = self.get_service()
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        try:
            response = service.users().messages().send(
                userId="me",
                body={"raw": encoded_message},
            ).execute()
        except HttpError as exc:
            status = getattr(getattr(exc, "resp", None), "status", None)
            logger.warning("Gmail messages.send failed with HTTP status %s.", status)
            if status == 403:
                raise GmailError(
                    "Google a refusé l'envoi. Vérifiez l'autorisation Gmail, "
                    "l'activation de l'API et le statut du compte OAuth."
                ) from None
            if status == 429:
                raise GmailError("La limite d'envoi Gmail est atteinte. Réessayez plus tard.") from None
            raise GmailError("Gmail n'a pas pu envoyer cet email. Vérifiez votre connexion et réessayez.") from None
        except Exception as exc:
            logger.warning("Gmail messages.send failed (%s).", type(exc).__name__)
            raise GmailError("Erreur réseau lors de l'envoi Gmail. Vérifiez votre connexion et réessayez.") from None
        message_id = response.get("id")
        if not message_id:
            logger.warning("Gmail API send response did not contain a message ID.")
            raise GmailError("Gmail n'a pas confirmé l'envoi du message.")
        return message_id


def authenticate_gmail() -> bool:
    return GmailService().authorize()


def get_gmail_service():
    return GmailService().get_service()


def is_gmail_authenticated() -> bool:
    return GmailService().is_authenticated()


def disconnect_gmail() -> bool:
    return GmailService().disconnect()
