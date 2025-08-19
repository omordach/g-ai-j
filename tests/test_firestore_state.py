
def test_history_id_roundtrip(firestore_state_module):
    fs = firestore_state_module
    assert fs.get_last_history_id() is None
    fs.set_last_history_id(100)
    assert fs.get_last_history_id() == 100


def test_mark_processed_prunes(firestore_state_module, monkeypatch):
    fs = firestore_state_module
    monkeypatch.setattr(fs, "_MAX_STORED_IDS", 3)
    for i in range(5):
        fs.mark_processed(f"M{i}")
    assert fs.is_processed("M4")
    assert not fs.is_processed("M0")


def test_get_last_history_id_invalid_value_warns(firestore_state_module, caplog):
    fs = firestore_state_module
    fs._runtime_doc().set({"last_history_id": "bad"})
    with caplog.at_level("WARNING"):
        assert fs.get_last_history_id() is None
        assert "Invalid last_history_id value" in caplog.text


def test_get_last_history_id_none_value_warns(firestore_state_module, caplog):
    fs = firestore_state_module
    fs._runtime_doc().set({"last_history_id": None})
    with caplog.at_level("WARNING"):
        assert fs.get_last_history_id() is None
        assert "Invalid last_history_id value" in caplog.text
