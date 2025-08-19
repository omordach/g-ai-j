import os
from typing import List, Optional

import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

from logger_setup import logger

load_dotenv()

JIRA_URL = os.getenv("JIRA_URL")
PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")
ASSIGNEE = os.getenv("JIRA_ASSIGNEE") or os.getenv("JIRA_USER")
CLIENT_FIELD_ID = os.getenv("JIRA_CLIENT_FIELD_ID")

REQUIRED_ENV_VARS = ["JIRA_URL", "JIRA_PROJECT_KEY", "JIRA_USER", "JIRA_API_TOKEN", "JIRA_CLIENT_FIELD_ID"]
missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
if missing:
    raise EnvironmentError(f"Missing environment variables: {', '.join(missing)}")


def build_adf(text: str) -> dict:
    lines = text.splitlines() if text else []
    content = []
    for line in lines:
        content.append({"type": "paragraph", "content": [{"type": "text", "text": line}]})
    if not content:
        content.append({"type": "paragraph"})
    return {"type": "doc", "version": 1, "content": content}


def create_ticket(summary: str, adf_description: dict, client: str, issue_type: str = "Task", labels: Optional[List[str]] = None, assignee: Optional[str] = None) -> Optional[str]:
    if labels is None:
        labels = ["Billable"]
    url = f"{JIRA_URL}/rest/api/3/issue"
    auth = HTTPBasicAuth(os.getenv("JIRA_USER"), os.getenv("JIRA_API_TOKEN"))
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    fields = {
        "project": {"key": PROJECT_KEY},
        "summary": summary,
        "description": adf_description,
        "issuetype": {"name": issue_type},
        CLIENT_FIELD_ID: [{"value": client}],
        "labels": labels,
        "priority": {"name": "Medium"},
    }
    assignee = assignee or ASSIGNEE
    if assignee:
        fields["assignee"] = {"emailAddress": assignee}

    payload = {"fields": fields}

    try:
        response = requests.post(url, auth=auth, headers=headers, json=payload, timeout=10)
        if response.status_code == 201:
            key = response.json().get("key")
            logger.info("Jira ticket created: %s", key)
            return key
        logger.error("Failed to create Jira ticket: %s %s", response.status_code, response.text)
    except requests.RequestException as exc:
        logger.error("Request to Jira failed: %s", exc)
    return None


def create_jira_ticket(*args, **kwargs):
    """Backward-compatible wrapper for :func:`create_ticket`."""
    return create_ticket(*args, **kwargs)
