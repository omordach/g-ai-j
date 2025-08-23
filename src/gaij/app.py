import base64
import json
import os
import re
from collections.abc import Mapping
from email.utils import parseaddr
from typing import Any

from flask import Flask, request

from . import firestore_state, gmail_client, jira_client
from .gpt_agent import gpt_classify_issue
from .html_renderer import render_html
from .html_to_adf import build_adf_from_html, prepend_note
from .logger_setup import logger
from .settings import settings

TOKEN_PATH = settings.gmail_token_file_path


def validate_config() -> None:
    if not os.path.exists(TOKEN_PATH):
        raise FileNotFoundError(f"Gmail token not found at {TOKEN_PATH}")
    logger.info("Configuration validated")


app = Flask(__name__)
validate_config()

DOMAIN_MAP = settings.domain_to_client_json
ALLOWED_SENDERS = {s.strip().lower() for s in settings.allowed_senders_json}


def is_sender_allowed(sender_addr: str, sender_full: str) -> bool:
    if ALLOWED_SENDERS and sender_addr not in ALLOWED_SENDERS:
        logger.info("Sender %s not allowed (addr=%s)", sender_full, sender_addr)
        return False
    return True


def classify_client_and_issue(msg: Mapping[str, str], sender_addr: str) -> tuple[str, str]:
    classification = gpt_classify_issue(msg.get("subject", ""), msg.get("body_text", ""))
    issue_type = classification.get("issueType", "Task") if classification else "Task"
    client = classification.get("client", "N/A") if classification else "N/A"
    domain = sender_addr.split("@")[-1].lower() if "@" in sender_addr else ""
    if domain in DOMAIN_MAP:
        client = DOMAIN_MAP[domain]
    return issue_type, client


def sanitize_msg_id(raw_msg_id: str) -> str:
    sanitized = re.sub(r"[<>]", "", raw_msg_id)
    return re.sub(r"[^A-Za-z0-9_-]+", "-", sanitized).strip("-")


def build_labels(sanitized_msg_id: str) -> list[str]:
    labels = ["Billable"]
    if sanitized_msg_id:
        labels.append(f"email_msgid_{sanitized_msg_id}")
    return labels


def parse_envelope(envelope: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not envelope or "message" not in envelope:
        logger.error("Invalid Pub/Sub envelope")
        return None
    msg = envelope["message"]
    data = msg.get("data")
    try:
        return json.loads(base64.b64decode(data).decode("utf-8")) if data else {}
    except Exception as exc:
        logger.error("Failed to parse Pub/Sub message: %s", exc)
        return None


def extract_history_id(payload: Mapping[str, Any]) -> int | None:
    history_id_str = payload.get("historyId")
    if history_id_str is None:
        logger.warning("Missing historyId in Pub/Sub message")
        return None
    try:
        return int(history_id_str)
    except (TypeError, ValueError):
        logger.warning("Non-numeric historyId: %s", history_id_str)
        return None


def handle_new_messages(last_history_id: int, history_id: int) -> None:
    failed = False
    for mid in gmail_client.list_new_message_ids_since(last_history_id, history_id):
        try:
            process_message(mid)
        except Exception as exc:
            failed = True
            logger.error("Error processing message %s: %s", mid, exc)
    if failed:
        logger.error(
            "One or more messages failed to process; not updating history ID %s",
            history_id,
        )
    else:
        firestore_state.set_last_history_id(history_id)


@app.get("/healthz")
def healthz() -> tuple[str, int]:
    return "ok", 200


def process_message(message_id: str) -> None:
    if not firestore_state.claim_message(message_id):
        logger.info("Message %s already processed", message_id)
        return

    try:
        msg = gmail_client.get_message(message_id)
        sender_full = msg.get("from", "")
        sender_addr = parseaddr(sender_full)[1].lower()
        if not is_sender_allowed(sender_addr, sender_full):
            firestore_state.unclaim_message(message_id)
            return

        issue_type, client = classify_client_and_issue(msg, sender_addr)

        html = msg.get("body_html", msg.get("body_text", ""))
        inline_map = msg.get("inline_map", {})
        adf = build_adf_from_html(html, inline_map)

        attachments = list(msg.get("attachments", []))
        inline_parts = msg.get("inline_parts", [])

        if settings.preserve_html_render:
            render_bytes, render_name = render_html(
                html, inline_parts, settings.html_render_format
            )
            attachments.append(
                {
                    "filename": render_name,
                    "mime_type": "application/pdf"
                    if settings.html_render_format == "pdf"
                    else "image/png",
                    "data_bytes": render_bytes,
                    "is_inline": False,
                    "content_id": None,
                }
            )
            adf = prepend_note(
                adf, f"Full-fidelity email rendering attached: {render_name}"
            )

        sanitized_msg_id = sanitize_msg_id(msg.get("message_id", "") or "")
        labels = build_labels(sanitized_msg_id)

        key = jira_client.create_ticket(
            msg.get("subject", "(No Subject)"),
            adf,
            client,
            issue_type=issue_type,
            labels=labels,
        )

        if key:
            results = jira_client.upload_attachments(key, attachments)
            if results:
                new_adf = jira_client.build_adf_with_attachment_list(adf, results)
                if new_adf != adf:
                    jira_client.update_issue_description(key, new_adf)
            firestore_state.mark_processed(message_id)
        else:
            logger.error(
                "Failed to create Jira ticket for message %s; response: %s",
                message_id,
                key,
            )
            firestore_state.unclaim_message(message_id)
    except Exception:
        firestore_state.unclaim_message(message_id)
        raise


@app.post("/pubsub")
def pubsub_handler() -> tuple[str, int]:
    payload = parse_envelope(request.get_json(silent=True))
    if payload is None:
        return "Bad Request", 400

    history_id = extract_history_id(payload)
    if history_id is None:
        return "", 204

    last_history_id = firestore_state.get_last_history_id() or 0
    if history_id <= last_history_id:
        logger.info("Received stale historyId %s", history_id)
        return "", 204

    handle_new_messages(last_history_id, history_id)
    return "", 204


if __name__ == "__main__":
    app.run(host=settings.app_host, port=settings.app_port)
