import base64

from gaij.html_renderer import render_html


def test_render_full_fidelity_pdf_unit():
    # Include a character outside Latin-1 to ensure PDF generation doesn't crash.
    html = "<p style='color:red'>Hi\u202fthere</p><img src='cid:abc'>"
    inline_parts = [
        {
            "filename": "img.png",
            "mime_type": "image/png",
            "data_bytes": b"img",
            "is_inline": True,
            "content_id": "abc",
        }
    ]
    pdf_bytes, name = render_html(html, inline_parts, "pdf")
    assert name.endswith(".pdf")
    # Real PDFs must start with the "%PDF-" header and terminate with "%%EOF".
    assert pdf_bytes.startswith(b"%PDF-")
    assert pdf_bytes.strip().endswith(b"%%EOF")


def test_render_full_fidelity_pdf_integration(app_setup, monkeypatch):
    app = app_setup["app"]
    gmail_client = app_setup["gmail_client"]
    gpt_agent = app_setup["gpt_agent"]
    jira_client = app_setup["jira_client"]

    message = {
        "from": "Marisa@oetraining.com",
        "subject": "Sub",
        "message_id": "<id1>",
        "body_text": "Body",
        "body_html": "<p>Body<img src='cid:abc'></p>",
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
                "filename": "img.png",
                "mime_type": "image/png",
                "data_bytes": b"img",
                "is_inline": True,
                "content_id": "abc",
            }
        ],
    }

    monkeypatch.setattr(gmail_client, "get_message", lambda mid: message)
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

    assert "email-render.pdf" in uploaded
    first_para = desc["adf"]["content"][0]["content"][0]["text"]
    assert "email-render.pdf" in first_para
