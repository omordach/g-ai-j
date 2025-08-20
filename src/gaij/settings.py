from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Settings:
    jira_url: str = os.environ["JIRA_URL"]
    jira_project_key: str = os.environ["JIRA_PROJECT_KEY"]
    jira_user: str = os.environ["JIRA_USER"]
    jira_api_token: str = os.environ["JIRA_API_TOKEN"]
    jira_client_field_id: str = os.environ["JIRA_CLIENT_FIELD_ID"]
    jira_assignee: str | None = os.getenv("JIRA_ASSIGNEE")

    gmail_token_file_path: str = os.getenv("GMAIL_TOKEN_FILE_PATH", "/workspace/token.json")
    gmail_token_file: str | None = os.getenv("GMAIL_TOKEN_FILE")
    gmail_user_id: str = os.getenv("GMAIL_USER_ID", "me")

    domain_to_client_json: dict[str, str] = field(
        default_factory=lambda: json.loads(os.getenv("DOMAIN_TO_CLIENT_JSON", "{}"))
    )
    allowed_senders_json: list[str] = field(
        default_factory=lambda: json.loads(os.getenv("ALLOWED_SENDERS_JSON", "[]"))
    )

    gcp_project_id: str | None = os.getenv("GCP_PROJECT_ID")
    gcp_firestore_collection: str = os.getenv("GCP_FIRESTORE_COLLECTION", "gaij_state")
    pubsub_topic: str | None = os.getenv("PUBSUB_TOPIC")

    openai_api_key: str = os.environ["OPENAI_API_KEY"]
    email_sender: str | None = os.getenv("EMAIL_SENDER")


settings = Settings()
