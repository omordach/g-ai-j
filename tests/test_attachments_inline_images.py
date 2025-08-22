import base64

def test_attachments_inline_images(app_setup, monkeypatch):
    gmail_client = app_setup["gmail_client"]
    jira_client = app_setup["jira_client"]
    app = app_setup["app"]
    gpt_agent = app_setup["gpt_agent"]

    message_json = {
        "id": "1",
        "payload": {
            "mimeType": "multipart/related",
            "parts": [
                {
                    "mimeType": "text/html",
                    "body": {
                        "data": base64.urlsafe_b64encode(b'<html><body><img src="cid:abc123"></body></html>').decode()
                    },
                },
                {
                    "filename": "photo.png",
                    "mimeType": "image/png",
                    "body": {"attachmentId": "a1"},
                    "headers": [{"name": "Content-ID", "value": "<abc123>"}],
                },
            ],
        },
    }

    class Attachments:
        def get(self, userId, messageId, id):  # noqa: N803
            return self

        def execute(self):
            return {"data": base64.urlsafe_b64encode(b"img").decode()}

    class Messages:
        def attachments(self):
            return Attachments()

    class Users:
        def messages(self):
            return Messages()

    class Service:
        def users(self):
            return Users()

    monkeypatch.setattr(gmail_client, "get_gmail_service", lambda: Service())

    attachments = gmail_client.extract_attachments(message_json)
    assert attachments[0]["is_inline"]

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
    monkeypatch.setattr(jira_client, "create_ticket", lambda *a, **k: "JIRA-2")

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

    assert set(uploaded) == {"photo.png"}
    content = desc["adf"]["content"]
    assert any(p["content"][0]["text"] == "photo.png" for p in content)
