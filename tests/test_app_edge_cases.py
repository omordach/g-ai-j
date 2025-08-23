def test_parse_envelope_edge_cases(app_setup):
    app = app_setup["app"]
    # None or missing message
    assert app.parse_envelope(None) is None
    assert app.parse_envelope({}) is None
    # Bad base64 data
    bad_env = {"message": {"data": "%%%"}}
    assert app.parse_envelope(bad_env) is None


def test_extract_history_id_edge_cases(app_setup):
    app = app_setup["app"]
    assert app.extract_history_id({}) is None
    assert app.extract_history_id({"historyId": "abc"}) is None


def test_handle_new_messages_failure(app_setup, monkeypatch):
    app = app_setup["app"]
    # Simulate one message that raises during processing
    monkeypatch.setattr(app.gmail_client, "list_new_message_ids_since", lambda a, b: ["1"])

    def boom(mid: str) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(app, "process_message", boom)
    called = {"set": False}

    def fake_set(hist: int) -> None:
        called["set"] = True

    monkeypatch.setattr(app.firestore_state, "set_last_history_id", fake_set)
    app.handle_new_messages(1, 2)
    assert called["set"] is False
