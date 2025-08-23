import importlib
import time


def test_register_watch(monkeypatch, firestore_state_module):
    monkeypatch.setenv("GCP_PROJECT_ID", "proj")
    monkeypatch.setenv("PUBSUB_TOPIC", "gmail-notifications")
    import gaij.gmail_watch as gmail_watch
    import gaij.settings as settings
    importlib.reload(settings)
    importlib.reload(gmail_watch)

    class FakeService:
        def users(self):
            return self

        def watch(self, userId, body):  # noqa: N803
            self.body = body
            return self

        def execute(self):
            return {"historyId": "99", "expiration": 2000}

    monkeypatch.setattr(gmail_watch.gmail_client, "get_gmail_service", lambda: FakeService())

    gmail_watch.register_watch()
    watch = firestore_state_module.get_watch()
    assert watch["historyId"] == 99
    assert firestore_state_module.get_last_history_id() == 99


def test_renew_watch_if_expiring(monkeypatch, firestore_state_module):
    import gaij.gmail_watch as gmail_watch
    import gaij.settings as settings
    importlib.reload(settings)
    importlib.reload(gmail_watch)

    called = {"registered": False}

    def fake_register():
        called["registered"] = True

    monkeypatch.setattr(gmail_watch, "register_watch", fake_register)
    monkeypatch.setattr(
        firestore_state_module,
        "get_watch",
        lambda: {"expiration": int((time.time() + 3600) * 1000)},
    )

    gmail_watch.renew_watch_if_needed()
    assert called["registered"] is True
