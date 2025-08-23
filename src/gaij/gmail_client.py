import base64
import json
import os
import re
from collections.abc import Iterable
from typing import Any, cast

from bs4 import BeautifulSoup
from bs4.element import Tag
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
            try:
                creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)  # type: ignore[no-untyped-call]
            except json.JSONDecodeError as err:
                logger.error("Failed to parse JSON from GMAIL_TOKEN_FILE")
                raise FileNotFoundError("Invalid GMAIL_TOKEN_FILE content") from err
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


def _extract_html(payload: dict[str, Any]) -> str:
    """Return the first HTML body found in the payload tree."""
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")
    if mime_type.startswith("multipart"):
        for part in payload.get("parts", []):
            html = _extract_html(part)
            if html:
                return html
    elif body_data and mime_type == "text/html":
        try:
            return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
        except Exception:  # pragma: no cover - defensive
            return ""
    return ""


def _normalize_filename(name: str, index: int, mime_type: str) -> str:
    """Return a safe filename, generating one if missing."""
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name or "").strip("._")
    if not name:
        ext = mime_type.split("/")[-1] if "/" in mime_type else "bin"
        name = f"attachment_{index}.{ext}"
    return name


def _collect_all_parts(message_json: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    """Return the HTML body and all attachment parts."""
    payload = message_json.get("payload", {})
    html_body = _extract_html(payload)
    cid_refs: set[str] = set()
    if html_body:
        soup = BeautifulSoup(html_body, "html.parser")
        for tag in cast("Iterable[Tag]", soup.find_all(src=True)):
            src_attr = tag.get("src")
            if isinstance(src_attr, str) and src_attr.startswith("cid:"):
                cid_refs.add(src_attr[4:])

    attachments: list[dict[str, Any]] = []

    def walk(part: dict[str, Any]) -> None:
        mime_type = part.get("mimeType", "application/octet-stream")
        filename = part.get("filename", "")
        body = part.get("body", {})
        attachment_id = body.get("attachmentId")
        headers = {h.get("name", "").lower(): h.get("value", "") for h in part.get("headers", [])}
        if attachment_id or filename:
            if attachment_id:
                data_bytes = download_attachment(message_json.get("id", ""), attachment_id)
            else:
                data = body.get("data")
                data_bytes = base64.urlsafe_b64decode(data) if data else b""

            cid = headers.get("content-id")
            if cid:
                cid = cid.strip("<>")
            content_disp = headers.get("content-disposition", "")
            is_inline = bool(
                (cid and cid in cid_refs) or ("inline" in content_disp.lower())
            )

            norm_name = _normalize_filename(filename, len(attachments), mime_type)
            attachments.append(
                {
                    "filename": norm_name,
                    "mime_type": mime_type,
                    "data_bytes": data_bytes,
                    "is_inline": is_inline,
                    "content_id": cid,
                }
            )

        for sub in part.get("parts", []):
            walk(sub)

    walk(payload)
    return html_body or "", attachments


def download_attachment(message_id: str, attachment_id: str) -> bytes:
    """Download a single attachment's bytes from Gmail."""
    service = get_gmail_service()
    try:
        resp = (
            service.users()
            .messages()
            .attachments()
            .get(
                userId=settings.gmail_user_id,
                messageId=message_id,
                id=attachment_id,
            )
            .execute()
        )
        data = resp.get("data")
        return base64.urlsafe_b64decode(data) if data else b""
    except HttpError as err:
        logger.error("Gmail API error fetching attachment %s: %s", attachment_id, err)
    except Exception as err:  # pragma: no cover - defensive
        logger.error("Unexpected error fetching attachment %s: %s", attachment_id, err)
    return b""


def extract_html_and_inline_parts(message_json: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    """Return HTML body with placeholders and inline parts."""
    html, attachments = _collect_all_parts(message_json)
    inline_parts = [a for a in attachments if a["is_inline"]]
    for part in inline_parts:
        cid = part.get("content_id")
        if cid:
            html = html.replace(f"cid:{cid}", f"__INLINE_IMAGE__[{cid}]__")
    return html, inline_parts


def extract_attachments(message_json: dict[str, Any]) -> list[dict[str, Any]]:
    """Return non-inline attachments from a Gmail message."""
    _, attachments = _collect_all_parts(message_json)
    return [a for a in attachments if not a["is_inline"]]


def list_new_message_ids_since(
    start_history_id: int,
    end_history_id: int,
    *,
    _max_pages: int = 1000,
) -> Iterable[str]:
    """Yield message IDs added between history IDs without storing them all."""
    service = get_gmail_service()
    user_id = settings.gmail_user_id
    page_token = None
    pages = 0
    while pages < _max_pages:
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
        pages += 1
    else:  # pragma: no cover - defensive safeguard
        logger.error(
            "Exceeded %d pages listing Gmail history %s-%s",
            _max_pages,
            start_history_id,
            end_history_id,
        )


def get_message(message_id: str, format: str = "full") -> dict[str, Any]:
    """Return parsed details for a Gmail message including attachments."""
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
    html_body, all_parts = _collect_all_parts(msg)
    inline_parts = [a for a in all_parts if a["is_inline"]]
    attachments = [a for a in all_parts if not a["is_inline"]]
    all_attachments = attachments + inline_parts
    inline_map = {
        part["content_id"]: part["filename"]
        for part in inline_parts
        if part.get("content_id")
    }

    return {
        "from": headers.get("From", ""),
        "subject": headers.get("Subject", ""),
        "date": headers.get("Date", ""),
        "message_id": headers.get("Message-ID", ""),
        "body_text": body_text,
        "body_html": html_body,
        "attachments": all_attachments,
        "inline_map": inline_map,
        "inline_parts": inline_parts,
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
