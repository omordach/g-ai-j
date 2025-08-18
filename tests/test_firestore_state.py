
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
