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


def _upload_one_attachment(
    att: dict[str, Any],
    url: str,
    auth: HTTPBasicAuth,
    headers: dict[str, str],
    allowed: set[str],
    max_bytes: int,
    issue_key: str,
) -> tuple[str, str]:
    """Return (filename, status) after attempting a single upload."""
    name = att.get("filename", "attachment")
    data = att.get("data_bytes", b"")
    mime = att.get("mime_type", "application/octet-stream")

    if att.get("is_inline") and not settings.attach_inline_images:
        logger.info("Skipping inline attachment %s", name)
        return name, "skipped inline"
    if len(data) > max_bytes:
        logger.warning("Skipping oversize attachment %s", name)
        return name, "oversize"
    if allowed and mime not in allowed:
        logger.warning("Skipping disallowed attachment %s", name)
        return name, "disallowed"

    files = {"file": (name, data, mime)}
    try:
        resp = requests.post(url, auth=auth, headers=headers, files=files, timeout=10)
    except requests.RequestException as exc:
        logger.error("Error uploading attachment %s: %s", name, exc)
        return name, "error"

    if resp.status_code in (200, 201):
        logger.info("Uploaded attachment %s to %s", name, issue_key)
        return name, "uploaded"
    logger.error(
        "Failed to upload attachment %s: %s %s", name, resp.status_code, resp.text
    )
    return name, f"failed {resp.status_code}"


def upload_attachments(issue_key: str, attachments: list[dict[str, Any]]) -> dict[str, str]:
    """Upload attachments to a Jira issue and return per-file results."""
    results: dict[str, str] = {}
    if not settings.attachment_upload_enabled or not attachments:
        return results

    url = f"{settings.jira_url}/rest/api/3/issue/{issue_key}/attachments"
    auth = HTTPBasicAuth(settings.jira_user, settings.jira_api_token)
    headers = {"X-Atlassian-Token": "no-check"}
    allowed = set(settings.attachment_allowed_mime_json)
    max_bytes = settings.jira_max_attachment_bytes

    for att in attachments:
        name, status = _upload_one_attachment(
            att, url, auth, headers, allowed, max_bytes, issue_key
        )
        results[name] = status
    return results


def build_adf_with_attachment_list(
    base_adf: dict[str, Any], uploaded_results: dict[str, str]
) -> dict[str, Any]:
    """Append an attachment list to an existing ADF document."""
    names = [n for n, status in uploaded_results.items() if status == "uploaded"]
    if not names:
        return base_adf
    content = list(base_adf.get("content", []))
    content.append({"type": "paragraph", "content": [{"type": "text", "text": "Attachments"}]})
    for name in names:
        content.append({"type": "paragraph", "content": [{"type": "text", "text": name}]})
    return {"type": "doc", "version": 1, "content": content}


def update_issue_description(issue_key: str, adf_description: dict[str, Any]) -> None:
    """Update the Jira issue description with the provided ADF."""
    url = f"{settings.jira_url}/rest/api/3/issue/{issue_key}"
    auth = HTTPBasicAuth(settings.jira_user, settings.jira_api_token)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    payload = {"fields": {"description": adf_description}}
    try:
        resp = requests.put(url, auth=auth, headers=headers, json=payload, timeout=10)
        if resp.status_code not in (200, 204):
            logger.error(
                "Failed to update Jira issue %s description: %s %s",
                issue_key,
                resp.status_code,
                resp.text,
            )
    except requests.RequestException as exc:  # pragma: no cover - network safety
        logger.error("Error updating Jira issue %s description: %s", issue_key, exc)
