from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from .logger_setup import logger


def require_env(var_name: str) -> str:
    value = os.getenv(var_name)
    if value is None:
        raise ValueError(f"Required environment variable '{var_name}' is missing")
    return value


def _load_domain_to_client_json() -> dict[str, str]:
    try:
        raw = json.loads(os.getenv("DOMAIN_TO_CLIENT_JSON", "{}"))
    except json.JSONDecodeError:
        logger.error(
            "Failed to decode DOMAIN_TO_CLIENT_JSON; defaulting to empty dict"
        )
        return {}

    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}

    logger.error(
        "DOMAIN_TO_CLIENT_JSON is not a JSON object; defaulting to empty dict"
    )
    return {}


def _load_allowed_senders_json() -> list[str]:
    try:
        raw = json.loads(os.getenv("ALLOWED_SENDERS_JSON", "[]"))
    except json.JSONDecodeError:
        logger.error(
            "Failed to decode ALLOWED_SENDERS_JSON; defaulting to empty list"
        )
        return []

    if isinstance(raw, list):
        return [str(item) for item in raw]

    logger.error(
        "ALLOWED_SENDERS_JSON is not a JSON array; defaulting to empty list"
    )
    return []


@dataclass
class Settings:
    jira_url: str = require_env("JIRA_URL")
    jira_project_key: str = require_env("JIRA_PROJECT_KEY")
    jira_user: str = require_env("JIRA_USER")
    jira_api_token: str = require_env("JIRA_API_TOKEN")
    jira_client_field_id: str = require_env("JIRA_CLIENT_FIELD_ID")
    jira_assignee: str | None = os.getenv("JIRA_ASSIGNEE")

    gmail_token_file_path: str = os.getenv("GMAIL_TOKEN_FILE_PATH", "/workspace/token.json")
    gmail_token_file: str | None = os.getenv("GMAIL_TOKEN_FILE")
    gmail_user_id: str = os.getenv("GMAIL_USER_ID", "me")

    domain_to_client_json: dict[str, str] = field(
        default_factory=_load_domain_to_client_json
    )
    allowed_senders_json: list[str] = field(
        default_factory=_load_allowed_senders_json
    )

    app_host: str = os.getenv("APP_HOST", "127.0.0.1")
    app_port: int = int(os.getenv("APP_PORT", "8080"))

    gcp_project_id: str | None = os.getenv("GCP_PROJECT_ID")
    gcp_firestore_collection: str = os.getenv("GCP_FIRESTORE_COLLECTION", "gaij_state")
    pubsub_topic: str | None = os.getenv("PUBSUB_TOPIC")

    jira_max_attachment_bytes: int = int(
        os.getenv("JIRA_MAX_ATTACHMENT_BYTES", str(10 * 1024 * 1024))
    )
    attachment_allowed_mime_json: list[str] = field(
        default_factory=lambda: json.loads(
            os.getenv(
                "ATTACHMENT_ALLOWED_MIME_JSON",
                '["application/pdf","image/png","image/jpeg","application/vnd.openxmlformats-officedocument.wordprocessingml.document","application/msword"]',
            )
        )
    )
    attachment_upload_enabled: bool = (
        os.getenv("ATTACHMENT_UPLOAD_ENABLED", "true").lower() == "true"
    )
    attach_inline_images: bool = (
        os.getenv("ATTACH_INLINE_IMAGES", "true").lower() == "true"
    )

    preserve_html_render: bool = (
        os.getenv("PRESERVE_HTML_RENDER", "true").lower() == "true"
    )
    html_render_format: str = os.getenv("HTML_RENDER_FORMAT", "pdf")

    openai_api_key: str = require_env("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4")
    email_sender: str | None = os.getenv("EMAIL_SENDER")


settings = Settings()
