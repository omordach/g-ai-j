import base64
import json


def test_pubsub_happy_path(app_setup, pubsub_envelope, monkeypatch):
    client = app_setup["client"]
    fs = app_setup["firestore_state"]
    gmail_client = app_setup["gmail_client"]
    jira_client = app_setup["jira_client"]
    gpt_agent = app_setup["gpt_agent"]

    monkeypatch.setattr(gmail_client, "list_new_message_ids_since", lambda s, e: ["A1"])
    monkeypatch.setattr(
        gmail_client,
        "get_message",
        lambda mid: {
            "from": "Marisa@oetraining.com",
            "subject": "Add County",
            "message_id": "<abc@googlemail.com>",
            "body_text": "Line1\nLine2",
        },
    )
    monkeypatch.setattr(gpt_agent, "gpt_classify_issue", lambda s, b: {"issueType": "Task"})

    called = {}

    def fake_create(summary, adf, client_name, issue_type="Task", labels=None):
        called["summary"] = summary
        called["client"] = client_name
        called["labels"] = labels
        return "JIRA-1"

    monkeypatch.setattr(jira_client, "create_ticket", fake_create)

    res = client.post("/pubsub", json=pubsub_envelope)
    assert res.status_code == 204
    assert fs.get_last_history_id() == 12345
    assert fs.is_processed("A1")
    assert called["client"] == "OETraining"
    assert "email_msgid_abc-googlemail-com" in called["labels"]


def test_pubsub_duplicate_history(app_setup, pubsub_envelope, monkeypatch):
    client = app_setup["client"]
    fs = app_setup["firestore_state"]
    fs.set_last_history_id(12345)

    listed = {"called": False}

    def fake_list(start, end):
        listed["called"] = True
        return []

    monkeypatch.setattr(app_setup["gmail_client"], "list_new_message_ids_since", fake_list)
    res = client.post("/pubsub", json=pubsub_envelope)
    assert res.status_code == 204
    assert listed["called"] is False


def test_pubsub_duplicate_message(app_setup, pubsub_envelope, monkeypatch):
    client = app_setup["client"]
    fs = app_setup["firestore_state"]
    gmail_client = app_setup["gmail_client"]
    jira_client = app_setup["jira_client"]

    fs.mark_processed("A1")
    monkeypatch.setattr(gmail_client, "list_new_message_ids_since", lambda s, e: ["A1"])

    called = {"get": False, "ticket": False}

    def fake_get(mid):
        called["get"] = True
        return {}

    def fake_ticket(*args, **kwargs):
        called["ticket"] = True
        return "JIRA-1"

    monkeypatch.setattr(gmail_client, "get_message", fake_get)
    monkeypatch.setattr(jira_client, "create_ticket", fake_ticket)

    res = client.post("/pubsub", json=pubsub_envelope)
    assert res.status_code == 204
    assert not called["get"]
    assert not called["ticket"]
    assert fs.get_last_history_id() == 12345


def test_pubsub_process_message_failure(app_setup, pubsub_envelope, monkeypatch, caplog):
    client = app_setup["client"]
    fs = app_setup["firestore_state"]
    gmail_client = app_setup["gmail_client"]
    app_module = app_setup["app"]

    monkeypatch.setattr(gmail_client, "list_new_message_ids_since", lambda s, e: ["A1", "A2"])

    def fake_process(mid):
        if mid == "A2":
            raise RuntimeError("boom")

    monkeypatch.setattr(app_module, "process_message", fake_process)

    with caplog.at_level("ERROR"):
        res = client.post("/pubsub", json=pubsub_envelope)

    assert res.status_code == 204
    assert fs.get_last_history_id() is None
    assert "not updating history ID" in caplog.text


def test_pubsub_missing_history_id(app_setup, monkeypatch):
    client = app_setup["client"]
    gmail_client = app_setup["gmail_client"]
    fs = app_setup["firestore_state"]

    listed = {"called": False}

    def fake_list(start, end):
        listed["called"] = True
        return []

    monkeypatch.setattr(gmail_client, "list_new_message_ids_since", fake_list)

    payload = base64.b64encode(json.dumps({"emailAddress": "me"}).encode()).decode()
    envelope = {"message": {"data": payload}}

    res = client.post("/pubsub", json=envelope)
    assert res.status_code == 204
    assert listed["called"] is False
    assert fs.get_last_history_id() is None


def test_pubsub_non_numeric_history_id(app_setup, monkeypatch):
    client = app_setup["client"]
    gmail_client = app_setup["gmail_client"]
    fs = app_setup["firestore_state"]

    listed = {"called": False}

    def fake_list(start, end):
        listed["called"] = True
        return []

    monkeypatch.setattr(gmail_client, "list_new_message_ids_since", fake_list)

    payload = base64.b64encode(
        json.dumps({"emailAddress": "me", "historyId": "abc"}).encode()
    ).decode()
    envelope = {"message": {"data": payload}}

    res = client.post("/pubsub", json=envelope)
    assert res.status_code == 204
    assert listed["called"] is False
    assert fs.get_last_history_id() is None


def test_pubsub_gmail_api_failure(app_setup, pubsub_envelope, monkeypatch):
    client = app_setup["client"]
    fs = app_setup["firestore_state"]
    gmail_client = app_setup["gmail_client"]

    class Users:
        def history(self):
            return self

        def list(self, **kwargs):
            return self

        def execute(self):
            from types import SimpleNamespace
            from googleapiclient.errors import HttpError

            resp = SimpleNamespace(status=500, reason="boom")
            raise HttpError(resp, b"error")

    class Service:
        def users(self):
            return Users()

    monkeypatch.setattr(gmail_client, "get_gmail_service", lambda: Service())

    res = client.post("/pubsub", json=pubsub_envelope)
    assert res.status_code == 204
    assert fs.get_last_history_id() == 12345
