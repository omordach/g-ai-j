import os
from typing import Optional
from google.cloud import firestore
from google.api_core import exceptions
from logger_setup import logger

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
COLLECTION = os.getenv("GCP_FIRESTORE_COLLECTION", "gaij_state")

# Lazily initialize the Firestore client so tests can provide fakes without
# needing real GCP credentials at import time.
_client = None
_collection = None


def _get_collection():
    """Return the Firestore collection, creating the client on first use."""
    global _client, _collection
    if _collection is None:
        _client = firestore.Client(project=PROJECT_ID)
        _collection = _client.collection(COLLECTION)
    return _collection

_MAX_STORED_IDS = 5000


def _processed_doc():
    return _get_collection().document("processed")


def _runtime_doc():
    return _get_collection().document("runtime")


def _config_doc():
    return _get_collection().document("config").collection("watch").document("current")


def get_last_history_id() -> Optional[int]:
    try:
        doc = _runtime_doc().get()
        if doc.exists:
            value = doc.to_dict().get("last_history_id")
            try:
                return int(value)
            except (TypeError, ValueError):
                logger.warning("Invalid last_history_id value: %r", value)
                return None
    except exceptions.GoogleAPICallError as exc:
        logger.error("Failed to fetch last_history_id: %s", exc)
    return None


def set_last_history_id(value: int) -> None:
    try:
        _runtime_doc().set({"last_history_id": int(value)})
    except exceptions.GoogleAPICallError as exc:
        logger.error("Failed to set last_history_id: %s", exc)


def is_processed(message_id: str) -> bool:
    try:
        doc = _processed_doc().get()
        ids = doc.to_dict().get("message_ids", []) if doc.exists else []
        return message_id in ids
    except exceptions.GoogleAPICallError as exc:
        logger.error("Failed to check processed message: %s", exc)
        return False


def mark_processed(message_id: str) -> None:
    try:
        doc_ref = _processed_doc()
        doc = doc_ref.get()
        ids = doc.to_dict().get("message_ids", []) if doc.exists else []
        ids.append(message_id)
        if len(ids) > _MAX_STORED_IDS:
            ids = ids[-_MAX_STORED_IDS:]
        doc_ref.set({"message_ids": ids})
    except exceptions.GoogleAPICallError as exc:
        logger.error("Failed to mark processed message: %s", exc)


def get_watch() -> Optional[dict]:
    try:
        doc = _config_doc().get()
        return doc.to_dict() if doc.exists else None
    except exceptions.GoogleAPICallError as exc:
        logger.error("Failed to get watch config: %s", exc)
        return None


def set_watch(history_id: int, expiration: int) -> None:
    try:
        _config_doc().set({"historyId": int(history_id), "expiration": int(expiration)})
    except exceptions.GoogleAPICallError as exc:
        logger.error("Failed to set watch config: %s", exc)
