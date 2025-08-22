import base64

def test_attachments_file_basic(app_setup, monkeypatch):
    app = app_setup["app"]
    gmail_client = app_setup["gmail_client"]
    jira_client = app_setup["jira_client"]
    gpt_agent = app_setup["gpt_agent"]
    fs = app_setup["firestore_state"]

    attachments = [
        {
            "filename": "file1.pdf",
            "mime_type": "application/pdf",
            "data_bytes": b"1",
            "is_inline": False,
            "content_id": None,
        },
        {
            "filename": "image.png",
            "mime_type": "image/png",
            "data_bytes": b"2",
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
            "message_id": "<id1>",
            "body_text": "Body",
            "attachments": attachments,
        },
    )
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

    assert fs.is_processed("A1")
    assert set(uploaded) == {"file1.pdf", "image.png"}
    content = desc["adf"]["content"]
    assert any(p["content"][0]["text"] == "Attachments" for p in content)
    assert any(p["content"][0]["text"] == "file1.pdf" for p in content)
    assert any(p["content"][0]["text"] == "image.png" for p in content)
