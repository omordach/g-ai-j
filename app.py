import base64
import json
import os
from flask import Flask, request

import firestore_state
import gmail_client
import jira_client
from gpt_agent import gpt_classify_issue
from logger_setup import logger

app = Flask(__name__)

DOMAIN_MAP = json.loads(os.getenv("DOMAIN_TO_CLIENT_JSON", "{}"))
ALLOWED_SENDERS = set(json.loads(os.getenv("ALLOWED_SENDERS_JSON", "[]")))


@app.get("/healthz")
def healthz():
    return "ok", 200


def process_message(message_id: str) -> None:
    if firestore_state.is_processed(message_id):
        logger.info("Message %s already processed", message_id)
        return

    msg = gmail_client.get_message(message_id)
    sender = msg.get("from", "")
    if ALLOWED_SENDERS and sender not in ALLOWED_SENDERS:
        logger.info("Sender %s not allowed", sender)
        return

    classification = gpt_classify_issue(msg.get("subject", ""), msg.get("body_text", ""))
    issue_type = classification.get("issueType", "Task") if classification else "Task"
    client = classification.get("client", "N/A") if classification else "N/A"

    domain = sender.split("@")[-1].lower() if "@" in sender else ""
    if domain in DOMAIN_MAP:
        client = DOMAIN_MAP[domain]

    adf = jira_client.build_adf(msg.get("body_text", ""))
    labels = ["Billable", f"email_msgid_{msg.get('message_id')}"]
    key = jira_client.create_ticket(
        msg.get("subject", "(No Subject)"),
        adf,
        client,
        issue_type=issue_type,
        labels=labels,
    )
    if key:
        firestore_state.mark_processed(message_id)


@app.post("/pubsub")
def pubsub_handler():
    envelope = request.get_json(silent=True)
    if not envelope or "message" not in envelope:
        logger.error("Invalid Pub/Sub envelope")
        return "Bad Request", 400

    msg = envelope["message"]
    data = msg.get("data")
    try:
        payload = json.loads(base64.b64decode(data).decode("utf-8")) if data else {}
        history_id = int(payload.get("historyId"))
    except Exception as exc:
        logger.error("Failed to parse Pub/Sub message: %s", exc)
        return "Bad Request", 400

    last_history_id = firestore_state.get_last_history_id() or 0
    if history_id <= last_history_id:
        logger.info("Received stale historyId %s", history_id)
        return "", 204

    message_ids = gmail_client.list_new_message_ids_since(last_history_id, history_id)
    for mid in message_ids:
        try:
            process_message(mid)
        except Exception as exc:
            logger.error("Error processing message %s: %s", mid, exc)

    firestore_state.set_last_history_id(history_id)
    return "", 204


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
