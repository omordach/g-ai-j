import time
from typing import Any, cast

from . import firestore_state, gmail_client
from .logger_setup import logger
from .settings import settings


def register_watch() -> dict[str, Any]:
    service = gmail_client.get_gmail_service()
    user = settings.gmail_user_id
    project = settings.gcp_project_id
    topic = settings.pubsub_topic
    body = {
        "topicName": f"projects/{project}/topics/{topic}",
        "labelIds": ["INBOX"],
        "labelFilterAction": "include",
    }
    response = service.users().watch(userId=user, body=body).execute()
    firestore_state.set_watch(response.get("historyId"), response.get("expiration"))
    firestore_state.set_last_history_id(int(response.get("historyId")))
    logger.info("Registered Gmail watch: %s", response)
    return cast(dict[str, Any], response)


def renew_watch_if_needed() -> None:
    watch = firestore_state.get_watch()
    if not watch:
        logger.info("No existing watch; registering new one")
        register_watch()
        return
    expiration = int(watch.get("expiration", 0))
    seconds_left = expiration / 1000 - time.time()
    if seconds_left < 24 * 3600:
        logger.info("Watch expiring in %.0f seconds; renewing", seconds_left)
        register_watch()
    else:
        logger.info("Watch still valid for %.0f seconds", seconds_left)


if __name__ == "__main__":
    renew_watch_if_needed()
