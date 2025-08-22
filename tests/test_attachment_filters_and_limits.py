
def test_attachment_filters_and_limits(app_setup, monkeypatch):
    app = app_setup["app"]
    jira_client = app_setup["jira_client"]
    gpt_agent = app_setup["gpt_agent"]
    gmail_client_module = app_setup["gmail_client"]
    settings = app_setup["app"].settings

    oversize = settings.jira_max_attachment_bytes + 1
    message = {
        "from": "Marisa@oetraining.com",
        "subject": "Sub",
        "message_id": "<id1>",
        "body_text": "Body",
        "body_html": "<p>Body</p>",
        "inline_map": {},
        "inline_parts": [],
        "attachments": [
            {
                "filename": "big.pdf",
                "mime_type": "application/pdf",
                "data_bytes": b"0" * oversize,
                "is_inline": False,
                "content_id": None,
            },
            {
                "filename": "bad.exe",
                "mime_type": "application/x-msdownload",
                "data_bytes": b"1",
                "is_inline": False,
                "content_id": None,
            },
            {
                "filename": "ok.pdf",
                "mime_type": "application/pdf",
                "data_bytes": b"2",
                "is_inline": False,
                "content_id": None,
            },
        ],
    }

    monkeypatch.setattr(gmail_client_module, "get_message", lambda mid: message)
    monkeypatch.setattr(gpt_agent, "gpt_classify_issue", lambda s, b: {"issueType": "Task"})
    monkeypatch.setattr(jira_client, "create_ticket", lambda *a, **k: "JIRA-1")

    uploaded = []

    def fake_post(url, auth=None, headers=None, files=None, timeout=None):
        uploaded.append(files["file"][0])
        class R:
            status_code = 200
            text = ""
        return R()

    monkeypatch.setattr(jira_client.requests, "post", fake_post)
    desc = {}
    monkeypatch.setattr(jira_client, "update_issue_description", lambda k, a: desc.setdefault("adf", a))

    app.process_message("A1")
    assert set(uploaded) == {"ok.pdf", "email-render.pdf"}
