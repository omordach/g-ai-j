from types import SimpleNamespace


def test_gpt_classify_issue_success(monkeypatch, app_setup):
    gpt_agent = app_setup["gpt_agent"]

    dummy_resp = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content='{"issueType":"Bug","client":"ClientX"}'
                )
            )
        ]
    )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **kwargs: dummy_resp)
        )
    )
    monkeypatch.setattr(gpt_agent, "_client", fake_client)

    result = gpt_agent.gpt_classify_issue("subj", "body")
    assert result == {"issueType": "Bug", "client": "ClientX"}


def test_gpt_classify_issue_failure(monkeypatch, app_setup):
    gpt_agent = app_setup["gpt_agent"]

    def raise_exc(**kwargs):
        raise ValueError("boom")

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=raise_exc)
        )
    )
    monkeypatch.setattr(gpt_agent, "_client", fake_client)

    assert gpt_agent.gpt_classify_issue("s", "b") is None


def test_extract_history_id_invalid(app_setup):
    app = app_setup["app"]
    assert app.extract_history_id({}) is None
    assert app.extract_history_id({"historyId": "abc"}) is None
