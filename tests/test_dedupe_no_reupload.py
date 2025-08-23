
def test_dedupe_no_reupload(app_setup, monkeypatch):
    app = app_setup["app"]
    jira_client = app_setup["jira_client"]
    gpt_agent = app_setup["gpt_agent"]
    gmail_client_module = app_setup["gmail_client"]

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

    monkeypatch.setattr(gmail_client_module, "get_message", lambda mid: message)
    monkeypatch.setattr(gpt_agent, "gpt_classify_issue", lambda s, b: {"issueType": "Task"})

    created = []
    monkeypatch.setattr(jira_client, "create_ticket", lambda *a, **k: created.append("JIRA-1") or "JIRA-1")

    uploaded = []

    def fake_post(url, auth=None, headers=None, files=None, timeout=None):
        name = files["file"][0]
        uploaded.append(name)
        idx = len(uploaded)
        class R:
            status_code = 200
            text = ""
            def json(self):
                return [{"id": str(idx)}]
        return R()

    monkeypatch.setattr(jira_client.requests, "post", fake_post)
    desc = {}
    monkeypatch.setattr(jira_client, "update_issue_description", lambda k, a: desc.setdefault("adf", a))

    app.process_message("A1")
    app.process_message("A1")  # second time should be skipped

    assert created == ["JIRA-1"]
    assert uploaded == ["email-render.pdf"]
