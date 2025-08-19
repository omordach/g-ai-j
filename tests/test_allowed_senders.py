import importlib
import json


def test_sender_normalization(monkeypatch, app_setup):
    monkeypatch.setenv("ALLOWED_SENDERS_JSON", json.dumps(["Oleh@Get-Code.net"]))
    import app
    app = importlib.reload(app)

    assert "oleh@get-code.net" in app.ALLOWED_SENDERS

    called = {"ticket": False}

    monkeypatch.setattr(app, "gpt_classify_issue", lambda s, b: {})
    monkeypatch.setattr(
        app.gmail_client,
        "get_message",
        lambda mid: {
            "from": "Oleh Mordach <oleh@get-code.net>",
            "subject": "hi",
            "body_text": "",
        },
    )

    def fake_create(summary, adf, client, issue_type="Task", labels=None):
        called["ticket"] = True
        return "JIRA-1"

    monkeypatch.setattr(app.jira_client, "create_ticket", fake_create)

    app.process_message("A1")
    assert called["ticket"]

