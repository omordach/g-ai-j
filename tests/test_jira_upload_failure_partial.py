
def test_jira_upload_failure_partial(app_setup, monkeypatch):
    import gaij.settings as settings_mod

    settings_mod.settings.preserve_html_render = False

    app = app_setup["app"]
    gmail_client = app_setup["gmail_client"]
    jira_client = app_setup["jira_client"]
    gpt_agent = app_setup["gpt_agent"]
    fs = app_setup["firestore_state"]

    attachments = [
        {
            "filename": "good.pdf",
            "mime_type": "application/pdf",
            "data_bytes": b"1",
            "is_inline": False,
            "content_id": None,
        },
        {
            "filename": "bad.pdf",
            "mime_type": "application/pdf",
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
            "message_id": "<id>",
            "body_text": "Body",
            "attachments": attachments,
        },
    )
    monkeypatch.setattr(gpt_agent, "gpt_classify_issue", lambda s, b: {"issueType": "Task"})
    monkeypatch.setattr(jira_client, "create_ticket", lambda *a, **k: "JIRA-6")

    uploaded: list[str] = []

    def fake_post(url, auth=None, headers=None, files=None, timeout=None):
        name = files["file"][0]
        uploaded.append(name)
        class R:
            text = ""
            status_code = 200 if name == "good.pdf" else 400
            def json(self):
                return [{"id": "1"}]
        return R()

    monkeypatch.setattr(jira_client.requests, "post", fake_post)
    desc: dict[str, object] = {}
    monkeypatch.setattr(jira_client, "update_issue_description", lambda k, a: desc.setdefault("adf", a))

    app.process_message("A1")

    assert fs.is_processed("A1")
    assert uploaded == ["good.pdf", "bad.pdf"]
    content = desc["adf"]["content"]  # type: ignore[index]
    assert any(p["content"][0]["text"] == "good.pdf" for p in content)
    assert all("bad.pdf" not in p["content"][0]["text"] for p in content if p.get("content"))
