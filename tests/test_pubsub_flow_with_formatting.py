import base64


def test_pubsub_flow_with_formatting(app_setup, monkeypatch, pubsub_envelope):
    client = app_setup["client"]
    gmail_client = app_setup["gmail_client"]
    gpt_agent = app_setup["gpt_agent"]
    jira_client = app_setup["jira_client"]
    fs = app_setup["firestore_state"]

    message = {
        "from": "Marisa@oetraining.com",
        "subject": "Sub",
        "message_id": "<id1>",
        "body_text": "Body",
        "body_html": "<h1>Hi</h1><p>Body<img src='cid:abc'></p>",
        "inline_map": {"abc": "img.png"},
        "inline_parts": [
            {
                "filename": "img.png",
                "mime_type": "image/png",
                "data_bytes": b"img",
                "is_inline": True,
                "content_id": "abc",
            }
        ],
        "attachments": [
            {
                "filename": "doc.pdf",
                "mime_type": "application/pdf",
                "data_bytes": b"1",
                "is_inline": False,
                "content_id": None,
            },
            {
                "filename": "img.png",
                "mime_type": "image/png",
                "data_bytes": b"img",
                "is_inline": True,
                "content_id": "abc",
            },
        ],
    }

    monkeypatch.setattr(
        gmail_client, "list_new_message_ids_since", lambda a, b: iter(["1"])
    )
    monkeypatch.setattr(gmail_client, "get_message", lambda mid: message)
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

    resp = client.post("/pubsub", json=pubsub_envelope)
    assert resp.status_code == 204

    assert set(uploaded) == {"doc.pdf", "img.png", "email-render.pdf"}
    first_para = desc["adf"]["content"][0]["content"][0]["text"]
    assert "email-render.pdf" in first_para
    assert fs.is_processed("1")
