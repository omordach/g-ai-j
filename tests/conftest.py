import base64
import importlib
import json
import os
import sys
from types import SimpleNamespace

import pytest
from google.cloud import firestore as firestore_mod
from google.api_core import exceptions as gcloud_exceptions

# Ensure the repository root is on the import path so application modules can
# be imported when tests run from the `tests/` directory.
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))


class FakeDocument:
    def __init__(self, store, path):
        self.store = store
        self.path = path

    def get(self):
        data = self.store.get(self.path)
        return SimpleNamespace(
            exists=data is not None,
            to_dict=lambda: data or {},
        )

    def set(self, data):
        self.store[self.path] = data

    def create(self, data):
        if self.path in self.store:
            raise gcloud_exceptions.AlreadyExists("Document already exists")
        self.store[self.path] = data

    def delete(self):
        self.store.pop(self.path, None)

    def collection(self, name):
        return FakeCollection(self.store, f"{self.path}/{name}")


class FakeCollection:
    def __init__(self, store, path):
        self.store = store
        self.path = path

    def document(self, name):
        return FakeDocument(self.store, f"{self.path}/{name}")


class FakeFirestoreClient:
    def __init__(self, project=None):
        self.store = {}

    def collection(self, name):
        return FakeCollection(self.store, name)


@pytest.fixture
def firestore_state_module(monkeypatch):
    """Provide the firestore_state module backed by an in-memory store."""
    monkeypatch.setattr(firestore_mod, "Client", FakeFirestoreClient)
    monkeypatch.setenv("JIRA_URL", "https://example.atlassian.net")
    monkeypatch.setenv("JIRA_USER", "user@example.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "token")
    monkeypatch.setenv("JIRA_PROJECT_KEY", "UIV4")
    monkeypatch.setenv("JIRA_CLIENT_FIELD_ID", "customfield_10000")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("JIRA_MAX_ATTACHMENT_BYTES", "10485760")
    monkeypatch.setenv(
        "ATTACHMENT_ALLOWED_MIME_JSON",
        json.dumps(
            [
                "application/pdf",
                "image/png",
                "image/jpeg",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/msword",
            ]
        ),
    )
    monkeypatch.setenv("ATTACHMENT_UPLOAD_ENABLED", "true")
    monkeypatch.setenv("ATTACH_INLINE_IMAGES", "true")
    monkeypatch.setenv("PRESERVE_HTML_RENDER", "true")
    monkeypatch.setenv("HTML_RENDER_FORMAT", "pdf")
    import gaij.firestore_state as firestore_state
    import gaij.settings as settings
    importlib.reload(settings)
    importlib.reload(firestore_state)
    return firestore_state


@pytest.fixture
def app_setup(monkeypatch, firestore_state_module):
    """Set up application modules with fakes and return references."""
    monkeypatch.setenv("JIRA_URL", "https://example.atlassian.net")
    monkeypatch.setenv("JIRA_USER", "user@example.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "token")
    monkeypatch.setenv("JIRA_PROJECT_KEY", "UIV4")
    monkeypatch.setenv("JIRA_ASSIGNEE", "assignee@example.com")
    monkeypatch.setenv("JIRA_CLIENT_FIELD_ID", "customfield_10000")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("JIRA_MAX_ATTACHMENT_BYTES", "10485760")
    monkeypatch.setenv(
        "ATTACHMENT_ALLOWED_MIME_JSON",
        json.dumps(
            [
                "application/pdf",
                "image/png",
                "image/jpeg",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/msword",
            ]
        ),
    )
    monkeypatch.setenv("ATTACHMENT_UPLOAD_ENABLED", "true")
    monkeypatch.setenv("ATTACH_INLINE_IMAGES", "true")
    monkeypatch.setenv("PRESERVE_HTML_RENDER", "true")
    monkeypatch.setenv("HTML_RENDER_FORMAT", "pdf")
    domain_map = {"oetraining.com": "OETraining"}
    monkeypatch.setenv("DOMAIN_TO_CLIENT_JSON", json.dumps(domain_map))

    token_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "token.json"
    )
    with open(token_path, "w") as f:
        json.dump({}, f)
    monkeypatch.setenv("GMAIL_TOKEN_FILE_PATH", token_path)

    import gaij.settings as settings
    importlib.reload(settings)
    import gaij.app as app
    import gaij.gmail_client as gmail_client
    import gaij.gpt_agent as gpt_agent
    import gaij.jira_client as jira_client
    importlib.reload(gmail_client)
    importlib.reload(jira_client)
    importlib.reload(gpt_agent)
    importlib.reload(app)
    gmail_client._service = None

    client = app.app.test_client()
    return {
        "client": client,
        "firestore_state": firestore_state_module,
        "gmail_client": gmail_client,
        "jira_client": jira_client,
        "gpt_agent": gpt_agent,
        "app": app,
    }


@pytest.fixture
def pubsub_envelope():
    payload = base64.b64encode(
        json.dumps({"emailAddress": "me", "historyId": "12345"}).encode()
    ).decode()
    return {"message": {"data": payload}}
