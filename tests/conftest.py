import base64
import json
import importlib
import os
import sys
from types import SimpleNamespace

import pytest
from google.cloud import firestore as firestore_mod

# Ensure the repository root is on the import path so application modules can
# be imported when tests run from the `tests/` directory.
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


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
    import firestore_state
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
    domain_map = {"oetraining.com": "OETraining"}
    monkeypatch.setenv("DOMAIN_TO_CLIENT_JSON", json.dumps(domain_map))

    import gmail_client, jira_client, gpt_agent, app
    importlib.reload(gmail_client)
    importlib.reload(jira_client)
    importlib.reload(gpt_agent)
    importlib.reload(app)

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
