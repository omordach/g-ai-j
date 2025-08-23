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


def _attachment_skip_reason(
    att: dict[str, Any],
    name: str,
    data: bytes,
    mime: str,
    allowed: set[str],
    max_bytes: int,
) -> Optional[str]:
    """Return a skip status if the attachment should not be uploaded."""
    if att.get("is_inline") and not settings.attach_inline_images:
        logger.info("Skipping inline attachment %s", name)
        return "skipped inline"
    if len(data) > max_bytes:
        logger.warning("Skipping oversize attachment %s", name)
        return "oversize"
    if allowed and mime not in allowed:
        logger.warning("Skipping disallowed attachment %s", name)
        return "disallowed"
    return None


def _extract_attachment_id(resp: requests.Response) -> Optional[str]:
    """Best-effort extraction of the attachment ID from the response."""
    try:
        data = resp.json()
        if isinstance(data, list) and data:
            return str(data[0].get("id"))
    except Exception:  # pragma: no cover - best effort
        return None
    return None


def _upload_one_attachment(
    att: dict[str, Any],
    url: str,
    auth: HTTPBasicAuth,
    headers: dict[str, str],
    allowed: set[str],
    max_bytes: int,
    issue_key: str,
) -> tuple[str, str, Optional[str]]:
    """Return ``(filename, status, attachment_id)`` after attempting upload."""
    name = att.get("filename", "attachment")
    data = att.get("data_bytes", b"")
    mime = att.get("mime_type", "application/octet-stream")

    skip_reason = _attachment_skip_reason(att, name, data, mime, allowed, max_bytes)
    if skip_reason:
        return name, skip_reason, None

    files = {"file": (name, data, mime)}
    try:
        resp = requests.post(url, auth=auth, headers=headers, files=files, timeout=10)
    except requests.RequestException as exc:
        logger.error("Error uploading attachment %s: %s", name, exc)
        return name, "error", None

    if resp.status_code in (200, 201):
        attach_id = _extract_attachment_id(resp)
        logger.info("Uploaded attachment %s to %s", name, issue_key)
        return name, "uploaded", attach_id
    logger.error(
        "Failed to upload attachment %s: %s %s", name, resp.status_code, resp.text
    )
    return name, f"failed {resp.status_code}", None


def upload_attachments(
    issue_key: str, attachments: list[dict[str, Any]]
) -> tuple[dict[str, str], dict[str, str]]:
    """Upload attachments and return status plus ``cid/filename → id`` map."""
    results: dict[str, str] = {}
    id_map: dict[str, str] = {}
    if not settings.attachment_upload_enabled or not attachments:
        return results, id_map

    url = f"{settings.jira_url}/rest/api/3/issue/{issue_key}/attachments"
    auth = HTTPBasicAuth(settings.jira_user, settings.jira_api_token)
    headers = {"X-Atlassian-Token": "no-check"}
    allowed = set(settings.attachment_allowed_mime_json)
    max_bytes = settings.jira_max_attachment_bytes

    for att in attachments:
        name, status, attach_id = _upload_one_attachment(
            att, url, auth, headers, allowed, max_bytes, issue_key
        )
        results[name] = status
        if attach_id:
            key = att.get("content_id") or name
            id_map[str(key)] = attach_id
    return results, id_map


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
