
def test_attachments_no_duplicates_for_processed_message(app_setup, monkeypatch):
    app = app_setup["app"]
    gmail_client = app_setup["gmail_client"]
    jira_client = app_setup["jira_client"]
    fs = app_setup["firestore_state"]

    fs.mark_processed("A1")

    called = {"ticket": False, "upload": False, "get": False}

    def fake_get(mid):
        called["get"] = True
        return {}

    def fake_ticket(*a, **k):
        called["ticket"] = True
        return "JIRA-5"

    def fake_upload(*a, **k):
        called["upload"] = True
        return {}

    monkeypatch.setattr(gmail_client, "get_message", fake_get)
    monkeypatch.setattr(jira_client, "create_ticket", fake_ticket)
    monkeypatch.setattr(jira_client, "upload_attachments", fake_upload)

    app.process_message("A1")

    assert called["get"] is False
    assert called["ticket"] is False
    assert called["upload"] is False
