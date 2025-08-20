import base64
import importlib
import json
from types import SimpleNamespace

import pytest

REQUIRED_ENV = {
    "JIRA_URL": "https://example.atlassian.net",
    "JIRA_PROJECT_KEY": "UIV4",
    "JIRA_USER": "user@example.com",
    "JIRA_API_TOKEN": "token",
    "JIRA_CLIENT_FIELD_ID": "customfield_10000",
    "OPENAI_API_KEY": "sk-test",
}


def setup_env(monkeypatch):
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)


def test_get_gmail_service_from_env(monkeypatch, tmp_path):
    setup_env(monkeypatch)
    monkeypatch.setenv("GMAIL_TOKEN_FILE_PATH", str(tmp_path / "token.json"))
    token_json = json.dumps({"client_id": "id", "client_secret": "secret"})
    monkeypatch.setenv("GMAIL_TOKEN_FILE", token_json)
    import gaij.settings as settings
    importlib.reload(settings)
    import gaij.gmail_client as gmail_client
    importlib.reload(gmail_client)
    dummy_creds = object()
    monkeypatch.setattr(
        gmail_client,
        "Credentials",
        SimpleNamespace(
            from_authorized_user_info=lambda info, scopes: dummy_creds,
            from_authorized_user_file=lambda path, scopes: dummy_creds,
        ),
    )
    dummy_service = object()
    monkeypatch.setattr(gmail_client, "build", lambda *args, **kwargs: dummy_service)
    gmail_client._service = None
    service = gmail_client.get_gmail_service()
    assert service is dummy_service
    assert gmail_client.get_gmail_service() is dummy_service  # cached


def test_get_gmail_service_missing_token(monkeypatch, tmp_path):
    setup_env(monkeypatch)
    missing = tmp_path / "missing.json"
    monkeypatch.setenv("GMAIL_TOKEN_FILE_PATH", str(missing))
    monkeypatch.delenv("GMAIL_TOKEN_FILE", raising=False)
    import gaij.settings as settings
    importlib.reload(settings)
    import gaij.gmail_client as gmail_client
    importlib.reload(gmail_client)
    gmail_client._service = None
    with pytest.raises(FileNotFoundError):
        gmail_client.get_gmail_service()


def test_list_new_message_ids_since_success(monkeypatch, app_setup):
    gmail_client = app_setup["gmail_client"]

    class Users:
        def __init__(self):
            self.calls = 0

        def history(self):
            return self

        def list(self, **kwargs):
            return self

        def execute(self):
            self.calls += 1
            if self.calls == 1:
                return {
                    "history": [{"messagesAdded": [{"message": {"id": "1"}}]}],
                    "nextPageToken": "tok",
                }
            return {"history": [{"messagesAdded": [{"message": {"id": "2"}}]}]}

    users = Users()

    class Service:
        def users(self):
            return users

    monkeypatch.setattr(gmail_client, "get_gmail_service", lambda: Service())
    ids = list(gmail_client.list_new_message_ids_since(1, 2))
    assert ids == ["1", "2"]


def test_get_message_success(monkeypatch, app_setup):
    gmail_client = app_setup["gmail_client"]

    class Users:
        def messages(self):
            return self

        def get(self, **kwargs):
            return self

        def execute(self):
            body = base64.urlsafe_b64encode(b"Body").decode()
            return {
                "payload": {
                    "mimeType": "text/plain",
                    "body": {"data": body},
                    "headers": [
                        {"name": "From", "value": "foo@example.com"},
                        {"name": "Subject", "value": "sub"},
                        {"name": "Date", "value": "today"},
                        {"name": "Message-ID", "value": "<id>"},
                    ],
                }
            }

    class Service:
        def users(self):
            return Users()

    monkeypatch.setattr(gmail_client, "get_gmail_service", lambda: Service())
    msg = gmail_client.get_message("1")
    assert msg["subject"] == "sub"
    assert msg["body_text"] == "Body"


def test_get_latest_email_from(monkeypatch, app_setup):
    gmail_client = app_setup["gmail_client"]

    class Messages:
        def __init__(self):
            self.stage = 0

        def list(self, userId, q, maxResults):  # noqa: N803
            assert q == "from:foo@example.com"
            return self

        def get(self, userId, id, format):  # noqa: N803
            self.stage = 1
            return self

        def execute(self):
            if self.stage == 0:
                return {"messages": [{"id": "1"}]}
            body = base64.urlsafe_b64encode(b"body").decode()
            return {
                "payload": {
                    "mimeType": "text/plain",
                    "body": {"data": body},
                    "headers": [{"name": "Subject", "value": "sub"}],
                }
            }

    class Users:
        def messages(self):
            return Messages()

    class Service:
        def users(self):
            return Users()

    monkeypatch.setattr(gmail_client, "get_gmail_service", lambda: Service())
    email = gmail_client.get_latest_email_from("foo@example.com")
    assert email == {"subject": "sub", "body": "body", "attachments": []}
