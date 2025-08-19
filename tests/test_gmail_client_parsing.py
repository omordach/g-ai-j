import base64
from types import SimpleNamespace

from googleapiclient.errors import HttpError


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


def test_extract_headers_message_id(app_setup):
    gmail_client = app_setup["gmail_client"]
    headers = [
        {"name": "From", "value": "foo@example.com"},
        {"name": "Message-ID", "value": "<id1@example.com>"},
    ]
    result = gmail_client.extract_headers(headers)
    assert result.get("Message-ID") == "<id1@example.com>"


def test_list_new_message_ids_since_api_error(app_setup, monkeypatch):
    gmail_client = app_setup["gmail_client"]

    class Users:
        def history(self):
            return self

        def list(self, **kwargs):
            return self

        def execute(self):  # pragma: no cover - behavior under test
            resp = SimpleNamespace(status=500, reason="boom")
            raise HttpError(resp, b"error")

    class Service:
        def users(self):
            return Users()

    monkeypatch.setattr(gmail_client, "get_gmail_service", lambda: Service())

    assert list(gmail_client.list_new_message_ids_since(1, 2)) == []


def test_get_message_api_error(app_setup, monkeypatch):
    gmail_client = app_setup["gmail_client"]

    class Users:
        def messages(self):
            return self

        def get(self, **kwargs):
            return self

        def execute(self):  # pragma: no cover - behavior under test
            resp = SimpleNamespace(status=500, reason="boom")
            raise HttpError(resp, b"error")

    class Service:
        def users(self):
            return Users()

    monkeypatch.setattr(gmail_client, "get_gmail_service", lambda: Service())

    assert gmail_client.get_message("1") == {}
