import threading


def test_concurrent_processing_creates_single_ticket(app_setup, monkeypatch):
    app = app_setup["app"]
    jira_client = app_setup["jira_client"]
    gmail_client = app_setup["gmail_client"]
    gpt_agent = app_setup["gpt_agent"]

    message = {
        "from": "Marisa@oetraining.com",
        "subject": "Sub",
        "message_id": "<id1>",
        "body_text": "Body",
        "body_html": "<p>Body</p>",
        "inline_map": {},
        "inline_parts": [],
        "attachments": [],
    }

    monkeypatch.setattr(gmail_client, "get_message", lambda mid: message)
    monkeypatch.setattr(gpt_agent, "gpt_classify_issue", lambda s, b: {"issueType": "Task"})

    created = []
    monkeypatch.setattr(
        jira_client,
        "create_ticket",
        lambda *a, **k: created.append("JIRA-1") or "JIRA-1",
    )

    def run():
        app.process_message("A1")

    t1 = threading.Thread(target=run)
    t2 = threading.Thread(target=run)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert created == ["JIRA-1"]
