from typing import Any, Optional

import requests  # type: ignore[import-untyped]
from requests.auth import HTTPBasicAuth  # type: ignore[import-untyped]

from .logger_setup import logger
from .settings import settings

CLIENT_FIELD_ID = settings.jira_client_field_id


def build_adf(text: str) -> dict[str, Any]:
    lines = text.splitlines() if text else []
    content = []
    for line in lines:
        content.append({"type": "paragraph", "content": [{"type": "text", "text": line}]})
    if not content:
        content.append({"type": "paragraph"})
    return {"type": "doc", "version": 1, "content": content}


def create_ticket(summary: str, adf_description: dict[str, Any], client: str, issue_type: str = "Task", labels: list[str] | None = None, assignee: str | None = None) -> str | None:
    if labels is None:
        labels = ["Billable"]
    url = f"{settings.jira_url}/rest/api/3/issue"
    auth = HTTPBasicAuth(settings.jira_user, settings.jira_api_token)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    fields = {
        "project": {"key": settings.jira_project_key},
        "summary": summary,
        "description": adf_description,
        "issuetype": {"name": issue_type},
        settings.jira_client_field_id: [{"value": client}],
        "labels": labels,
        "priority": {"name": "Medium"},
    }
    assignee = assignee or settings.jira_assignee
    if assignee:
        fields["assignee"] = {"emailAddress": assignee}

    payload = {"fields": fields}

    try:
        response = requests.post(url, auth=auth, headers=headers, json=payload, timeout=10)
        if response.status_code == 201:
            key = response.json().get("key")
            logger.info("Jira ticket created: %s", key)
            return str(key) if key else None
        logger.error("Failed to create Jira ticket: %s %s", response.status_code, response.text)
    except requests.RequestException as exc:
        logger.error("Request to Jira failed: %s", exc)
    return None


def create_jira_ticket(*args: Any, **kwargs: Any) -> str | None:
    """Backward-compatible wrapper for :func:`create_ticket`."""
    return create_ticket(*args, **kwargs)
