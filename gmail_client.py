import base64
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from bs4 import BeautifulSoup
from logger_setup import logger

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def get_gmail_service():
    token_path = "token.json"
    if not os.path.exists(token_path):
        logger.error("Gmail token file not found at %s", token_path)
        raise FileNotFoundError(token_path)

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    return build("gmail", "v1", credentials=creds)

def extract_body(payload):
    """Recursively extracts email body text from payload"""
    if 'parts' in payload:
        for part in payload['parts']:
            text = extract_body(part)
            if text:
                return text
    else:
        mime_type = payload.get('mimeType')
        data = payload.get('body', {}).get('data')
        if data:
            decoded = base64.urlsafe_b64decode(data).decode("utf-8")
            if mime_type == 'text/plain':
                return decoded.strip()
            elif mime_type == 'text/html':
                return BeautifulSoup(decoded, "html.parser").get_text().strip()
    return ""

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
