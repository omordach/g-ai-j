import requests


def test_create_ticket_failure(monkeypatch, app_setup):
    jira_client = app_setup["jira_client"]

    def fake_post(url, auth=None, headers=None, json=None, timeout=None):
        class Resp:
            status_code = 400
            text = "bad"
        return Resp()

    monkeypatch.setattr(jira_client.requests, "post", fake_post)
    key = jira_client.create_ticket("Summary", {"type": "doc", "content": []}, "Client")
    assert key is None


def test_upload_attachments_inline_and_error(monkeypatch, app_setup):
    jira_client = app_setup["jira_client"]
    monkeypatch.setattr(jira_client.settings, "attach_inline_images", False)

    def fake_post(url, auth=None, headers=None, files=None, timeout=None):
        name = files["file"][0]
        if name == "error.png":
            raise requests.RequestException("boom")
        class R:
            status_code = 200
            text = ""
        return R()

    monkeypatch.setattr(jira_client.requests, "post", fake_post)
    attachments = [
        {
            "filename": "inline.png",
            "mime_type": "image/png",
            "data_bytes": b"1",
            "is_inline": True,
            "content_id": "cid1",
        },
        {
            "filename": "error.png",
            "mime_type": "image/png",
            "data_bytes": b"2",
            "is_inline": False,
            "content_id": None,
        },
    ]
    results = jira_client.upload_attachments("JIRA-1", attachments)
    assert results["inline.png"] == "skipped inline"
    assert results["error.png"] == "error"


def test_update_issue_description_error(monkeypatch, app_setup):
    jira_client = app_setup["jira_client"]

    def fake_put(url, auth=None, headers=None, json=None, timeout=None):
        class Resp:
            status_code = 500
            text = "fail"
        return Resp()

    monkeypatch.setattr(jira_client.requests, "put", fake_put)
    jira_client.update_issue_description("KEY", {"type": "doc", "version": 1, "content": []})
