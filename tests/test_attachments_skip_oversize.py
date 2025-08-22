
def test_attachments_skip_oversize(app_setup, monkeypatch, caplog):
    app = app_setup["app"]
    gmail_client = app_setup["gmail_client"]
    jira_client = app_setup["jira_client"]
    gpt_agent = app_setup["gpt_agent"]

    attachments = [
        {
            "filename": "big.pdf",
            "mime_type": "application/pdf",
            "data_bytes": b"1234567",
            "is_inline": False,
            "content_id": None,
        },
        {
            "filename": "small.pdf",
            "mime_type": "application/pdf",
            "data_bytes": b"1",
            "is_inline": False,
            "content_id": None,
        },
    ]

    monkeypatch.setattr(
        gmail_client,
        "get_message",
        lambda mid: {
            "from": "Marisa@oetraining.com",
            "subject": "Sub",
            "message_id": "<id>",
            "body_text": "Body",
            "attachments": attachments,
        },
    )
    monkeypatch.setattr(gpt_agent, "gpt_classify_issue", lambda s, b: {"issueType": "Task"})
    monkeypatch.setattr(jira_client, "create_ticket", lambda *a, **k: "JIRA-3")
    monkeypatch.setattr(jira_client.settings, "jira_max_attachment_bytes", 5)

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

    with caplog.at_level("WARNING"):
        app.process_message("A1")

    assert uploaded == ["small.pdf"]
    assert "oversize attachment" in caplog.text
    content = desc["adf"]["content"]
    assert any(p["content"][0]["text"] == "small.pdf" for p in content)
    assert all("big.pdf" not in p["content"][0]["text"] for p in content if p.get("content"))
