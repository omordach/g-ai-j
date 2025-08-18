import base64


def test_extract_body_html(app_setup):
    gmail_client = app_setup["gmail_client"]
    payload = {
        "mimeType": "text/html",
        "body": {"data": base64.urlsafe_b64encode(b"<p>Hello <b>World</b></p>").decode()},
    }
    assert gmail_client.extract_body(payload) == "Hello World"


def test_extract_body_nested_multipart(app_setup):
    gmail_client = app_setup["gmail_client"]
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {
                "mimeType": "multipart/mixed",
                "parts": [
                    {
                        "mimeType": "text/html",
                        "body": {
                            "data": base64.urlsafe_b64encode(b"<p>Inner HTML</p>").decode()
                        },
                    }
                ],
            }
        ],
    }
    assert gmail_client.extract_body(payload) == "Inner HTML"
