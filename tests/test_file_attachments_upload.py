
def test_file_attachments_upload(app_setup, monkeypatch):
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
        "attachments": [
            {
                "filename": "file1.pdf",
                "mime_type": "application/pdf",
                "data_bytes": b"1",
                "is_inline": False,
                "content_id": None,
            },
            {
                "filename": "doc.docx",
                "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
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
    assert set(uploaded) == {"file1.pdf", "doc.docx", "email-render.pdf"}
    content = [p["content"][0]["text"] for p in desc["adf"]["content"] if p.get("content")]
    assert "file1.pdf" in "".join(content)
    assert "doc.docx" in "".join(content)
