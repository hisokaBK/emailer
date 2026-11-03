from __future__ import annotations

import json
from email.message import EmailMessage
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

import pytest
from pypdf import PdfWriter

import services.gmail_service as gmail_module
from services.gmail_service import GMAIL_SEND_SCOPE, GmailError, GmailService


def make_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def write_fake_oauth_client(path: Path) -> None:
    path.write_text(
        json.dumps({
            "installed": {
                "client_id": "test-client.apps.googleusercontent.com",
                "project_id": "test-project",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": "not-a-real-secret",
                "redirect_uris": ["http://localhost"],
            }
        }),
        encoding="utf-8",
    )


class FakeCredentials:
    def __init__(
        self,
        valid: bool = True,
        expired: bool = False,
        refresh_token: str | None = "test-refresh-token",
    ) -> None:
        self.valid = valid
        self.expired = expired
        self.refresh_token = refresh_token
        self.scopes = [GMAIL_SEND_SCOPE]
        self.refresh_calls = 0

    @classmethod
    def from_authorized_user_file(cls, _filename: str, _scopes: list[str]):
        return cls()

    def refresh(self, _request: object) -> None:
        self.refresh_calls += 1
        self.valid = True
        self.expired = False

    def to_json(self) -> str:
        return json.dumps({"token": "test-token", "scopes": self.scopes})


@pytest.fixture
def oauth_files(tmp_path: Path) -> tuple[Path, Path]:
    credentials_path = tmp_path / "google_credentials.json"
    token_path = tmp_path / "gmail_token.json"
    write_fake_oauth_client(credentials_path)
    return credentials_path, token_path


def test_oauth_credentials_detected_without_exposing_file_contents(oauth_files):
    credentials_path, token_path = oauth_files
    service = GmailService(token_path=token_path, credentials_path=credentials_path)

    assert service.is_configured()
    service._validate_oauth_file()


def test_missing_oauth_credentials_produce_safe_error(tmp_path: Path):
    service = GmailService(
        token_path=tmp_path / "gmail_token.json",
        credentials_path=tmp_path / "missing.json",
    )
    with pytest.raises(GmailError, match="credentials/google_credentials.json"):
        service.authorize()


def test_valid_token_is_reused(oauth_files, monkeypatch):
    credentials_path, token_path = oauth_files
    token_path.write_text("test-token", encoding="utf-8")
    credentials = FakeCredentials()
    monkeypatch.setattr(
        gmail_module,
        "Credentials",
        type("FakeCredentialsLoader", (), {
            "from_authorized_user_file": staticmethod(lambda _path: credentials)
        }),
    )
    service = GmailService(token_path=token_path, credentials_path=credentials_path)

    assert service.authorize()
    assert service.is_authenticated()
    assert credentials.refresh_calls == 0


def test_expired_token_refreshes_and_is_saved(oauth_files, monkeypatch):
    credentials_path, token_path = oauth_files
    token_path.write_text("test-token", encoding="utf-8")
    credentials = FakeCredentials(valid=False, expired=True)
    monkeypatch.setattr(
        gmail_module,
        "Credentials",
        type("FakeCredentialsLoader", (), {
            "from_authorized_user_file": staticmethod(lambda _path: credentials)
        }),
    )
    monkeypatch.setattr(gmail_module, "Request", lambda: object())
    service = GmailService(token_path=token_path, credentials_path=credentials_path)

    assert service.is_authenticated()
    assert credentials.refresh_calls == 1
    assert json.loads(token_path.read_text(encoding="utf-8"))["token"] == "test-token"


def test_oauth_flow_saves_local_token(oauth_files, monkeypatch):
    credentials_path, token_path = oauth_files
    expected_credentials = FakeCredentials()
    captured: dict = {}

    class FakeFlow:
        client_config = {"client_id": "test-client"}
        client_type = "installed"

        def run_local_server(self, **kwargs):
            captured.update(kwargs)
            return expected_credentials

    class FakeInstalledAppFlow:
        @staticmethod
        def from_client_secrets_file(_path: str, scopes: list[str]):
            assert scopes == [GMAIL_SEND_SCOPE]
            return FakeFlow()

    monkeypatch.setattr(gmail_module, "InstalledAppFlow", FakeInstalledAppFlow)
    monkeypatch.setattr(gmail_module, "Credentials", FakeCredentials)
    service = GmailService(token_path=token_path, credentials_path=credentials_path)

    assert service.authorize()
    assert token_path.is_file()
    assert captured["open_browser"] is True
    assert captured["host"] == "localhost"
    assert captured["port"] == 0
    assert captured["access_type"] == "offline"
    assert captured["prompt"] == "consent select_account"
    assert captured["authorization_prompt_message"] == ""


def test_invalid_scope_restarts_oauth_after_explicit_connect(oauth_files, monkeypatch):
    credentials_path, token_path = oauth_files
    token_path.write_text("test-token", encoding="utf-8")
    invalid_credentials = FakeCredentials()
    invalid_credentials.scopes = ["https://www.googleapis.com/auth/gmail.readonly"]

    class FakeFlow:
        client_config = {"client_id": "test-client"}
        client_type = "installed"

        def run_local_server(self, **_kwargs):
            return FakeCredentials()

    class FakeInstalledAppFlow:
        @staticmethod
        def from_client_secrets_file(_path: str, _scopes: list[str]):
            return FakeFlow()

    monkeypatch.setattr(
        gmail_module,
        "Credentials",
        type("FakeCredentialsLoader", (), {
            "from_authorized_user_file": staticmethod(lambda _path: invalid_credentials)
        }),
    )
    monkeypatch.setattr(gmail_module, "InstalledAppFlow", FakeInstalledAppFlow)
    service = GmailService(token_path=token_path, credentials_path=credentials_path)

    assert service.authorize()
    assert json.loads(token_path.read_text(encoding="utf-8"))["scopes"] == [GMAIL_SEND_SCOPE]


def test_disconnect_removes_only_local_token(oauth_files):
    credentials_path, token_path = oauth_files
    token_path.write_text("test-token", encoding="utf-8")
    service = GmailService(token_path=token_path, credentials_path=credentials_path)

    assert service.disconnect()
    assert not token_path.exists()
    assert credentials_path.exists()


def test_gmail_service_build_and_email_send_are_mockable_without_real_send(
    oauth_files, monkeypatch
):
    credentials_path, token_path = oauth_files
    service = GmailService(token_path=token_path, credentials_path=credentials_path)
    api = Mock()
    api.users.return_value.messages.return_value.send.return_value.execute.return_value = {
        "id": "test-message-id"
    }
    monkeypatch.setattr(service, "get_service", lambda: api)

    message = service.build_message(
        "contact@example.ma",
        "Candidature",
        "Bonjour, je joins mon CV à ma candidature.",
        [("cv.pdf", make_pdf())],
    )
    assert isinstance(message, EmailMessage)
    assert message["To"] == "contact@example.ma"
    assert message.get_body().get_content_charset() == "utf-8"
    assert len(list(message.iter_attachments())) == 1
    assert service.send_message(
        "contact@example.ma",
        "Candidature",
        "Bonjour, je joins mon CV à ma candidature.",
    ) == "test-message-id"
    api.users.return_value.messages.return_value.send.assert_called_once()


def test_gmail_api_client_initialization_uses_scoped_credentials(oauth_files, monkeypatch):
    credentials_path, token_path = oauth_files
    service = GmailService(token_path=token_path, credentials_path=credentials_path)
    credentials = FakeCredentials()
    monkeypatch.setattr(service, "_get_credentials", lambda: credentials)
    mocked_build = Mock(return_value=object())
    monkeypatch.setattr(gmail_module, "build", mocked_build)

    api_client = service.get_service()

    assert api_client is not None
    assert mocked_build.call_args.args[:2] == ("gmail", "v1")
    assert mocked_build.call_args.kwargs["credentials"] is credentials
    assert mocked_build.call_args.kwargs["cache_discovery"] is False


def test_pdf_attachments_are_validated(tmp_path: Path):
    service = GmailService()
    with pytest.raises(ValueError, match="introuvable"):
        service.build_message(
            "contact@example.ma",
            "Candidature",
            "Bonjour",
            [tmp_path / "missing.pdf"],
        )
    with pytest.raises(ValueError, match="PDF valide"):
        service.build_message(
            "contact@example.ma",
            "Candidature",
            "Bonjour",
            [("fake.pdf", b"not a pdf")],
        )
    with pytest.raises(ValueError, match="doit être un fichier PDF"):
        service.build_message(
            "contact@example.ma",
            "Candidature",
            "Bonjour",
            [("document.txt", b"not a pdf")],
        )


def test_oauth_paths_resolve_from_project_directory(tmp_path: Path):
    service = GmailService(
        token_path="credentials/gmail_token.json",
        credentials_path="credentials/google_credentials.json",
    )

    assert service.token_path.is_absolute()
    assert service.credentials_path.is_absolute()
    assert service.token_path.name == "gmail_token.json"
    assert service.credentials_path.name == "google_credentials.json"
