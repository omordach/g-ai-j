import base64
import json
import os
from collections.abc import Iterable
from typing import Any

from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .logger_setup import logger
from .settings import settings

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_PATH = settings.gmail_token_file_path

_service: Any | None = None


def get_gmail_service() -> Any:
    global _service
    if _service is not None:
        return _service

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)  # type: ignore[no-untyped-call]
    else:
        token_json = os.environ.get("GMAIL_TOKEN_FILE", "").strip()
        if token_json.startswith("{"):
            creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)  # type: ignore[no-untyped-call]
        else:
            logger.error(
                "Gmail token not found. Checked path %s and GMAIL_TOKEN_FILE env.",
                TOKEN_PATH,
            )
            raise FileNotFoundError(TOKEN_PATH)
    _service = build("gmail", "v1", credentials=creds)
    return _service


def extract_body(payload: dict[str, Any]) -> str:
    """Recursively extracts email body text from payload."""
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")

    if mime_type.startswith("multipart"):
        for part in payload.get("parts", []):
            text = extract_body(part)
            if text:
                return text
    elif body_data:
        decoded = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
        if mime_type == "text/plain":
            return decoded.strip()
        if mime_type == "text/html":
            return BeautifulSoup(decoded, "html.parser").get_text().strip()
    return ""


def extract_headers(headers: list[dict[str, str]]) -> dict[str, str]:
    """Return a subset of headers with case-insensitive matching."""
    desired = {"from": "", "subject": "", "date": "", "message-id": ""}
    for header in headers:
        name = header.get("name", "").lower()
        if name in desired:
            desired[name] = header.get("value", "")
    return {
        "From": desired["from"],
        "Subject": desired["subject"],
        "Date": desired["date"],
        "Message-ID": desired["message-id"],
    }


def list_new_message_ids_since(
    start_history_id: int, end_history_id: int
) -> Iterable[str]:
    """Yield message IDs added between history IDs without storing them all."""
    service = get_gmail_service()
    user_id = settings.gmail_user_id
    page_token = None
    while True:
        req = {
            "userId": user_id,
            "startHistoryId": start_history_id,
            "historyTypes": ["messageAdded"],
        }
        if page_token:
            req["pageToken"] = page_token
        try:
            resp = service.users().history().list(**req).execute()
        except HttpError as err:
            logger.error(
                "Gmail API error listing history %s-%s: %s",
                start_history_id,
                end_history_id,
                err,
            )
            return
        except Exception as err:  # pragma: no cover - generic safeguard
            logger.error(
                "Unexpected error listing history %s-%s: %s",
                start_history_id,
                end_history_id,
                err,
            )
            return
        for history in resp.get("history", []):
            for added in history.get("messagesAdded", []):
                mid = added.get("message", {}).get("id")
                if mid:
                    yield mid
        page_token = resp.get("nextPageToken")
        if not page_token:
            break


def get_message(message_id: str, format: str = "full") -> dict[str, str]:
    """Return parsed details for a Gmail message."""
    service = get_gmail_service()
    user_id = settings.gmail_user_id
    try:
        msg = (
            service.users()
            .messages()
            .get(userId=user_id, id=message_id, format=format)
            .execute()
        )
    except HttpError as err:
        logger.error("Gmail API error fetching message %s: %s", message_id, err)
        return {}
    except Exception as err:  # pragma: no cover - generic safeguard
        logger.error("Unexpected error fetching message %s: %s", message_id, err)
        return {}

    payload = msg.get("payload", {})
    headers = extract_headers(payload.get("headers", []))
    body_text = extract_body(payload)

    return {
        "from": headers.get("From", ""),
        "subject": headers.get("Subject", ""),
        "date": headers.get("Date", ""),
        "message_id": headers.get("Message-ID", ""),
        "body_text": body_text,
    }


def get_latest_email_from(sender: str) -> dict[str, Any] | None:
    service = get_gmail_service()
    query = f"from:{sender}"
    results = service.users().messages().list(userId="me", q=query, maxResults=1).execute()
    messages = results.get("messages", [])
    if not messages:
        return None

    msg = service.users().messages().get(userId="me", id=messages[0]['id'], format="full").execute()
    payload = msg['payload']
    headers = payload.get('headers', [])
    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "(No Subject)")
    body = extract_body(payload)

    if not body:
        logger.warning("Email body was empty or could not be extracted.")

    return {
        "subject": subject,
        "body": body,
        "attachments": [],  # Attachments can be implemented later if needed
    }
