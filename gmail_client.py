import base64
import os
from typing import Dict, List

from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from logger_setup import logger

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Cached Gmail API service instance
_service = None


def get_gmail_service():
    global _service
    if _service is not None:
        return _service

    token_path = "token.json"
    if not os.path.exists(token_path):
        logger.error("Gmail token file not found at %s", token_path)
        raise FileNotFoundError(token_path)

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    _service = build("gmail", "v1", credentials=creds)
    return _service


def extract_body(payload: Dict) -> str:
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


def extract_headers(headers: List[Dict]) -> Dict[str, str]:
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


def list_new_message_ids_since(start_history_id: int, end_history_id: int) -> List[str]:
    """Return unique message IDs added between history IDs."""
    service = get_gmail_service()
    user_id = os.getenv("GMAIL_USER_ID", "me")
    msg_ids = set()
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
            return []
        except Exception as err:  # pragma: no cover - generic safeguard
            logger.error(
                "Unexpected error listing history %s-%s: %s",
                start_history_id,
                end_history_id,
                err,
            )
            return []
        for history in resp.get("history", []):
            for added in history.get("messagesAdded", []):
                msg_ids.add(added.get("message", {}).get("id"))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return list(msg_ids)


def get_message(message_id: str, format: str = "full") -> Dict[str, str]:
    """Return parsed details for a Gmail message."""
    service = get_gmail_service()
    user_id = os.getenv("GMAIL_USER_ID", "me")
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
        "from": headers.get("From"),
        "subject": headers.get("Subject"),
        "date": headers.get("Date"),
        "message_id": headers.get("Message-ID"),
        "body_text": body_text,
    }


def get_latest_email_from(sender):
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
        "attachments": []  # Attachments can be implemented later if needed
    }
