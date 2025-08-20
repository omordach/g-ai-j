import importlib

REQUIRED_ENV = {
    "JIRA_URL": "https://example.atlassian.net",
    "JIRA_PROJECT_KEY": "UIV4",
    "JIRA_USER": "user@example.com",
    "JIRA_API_TOKEN": "token",
    "JIRA_CLIENT_FIELD_ID": "customfield_10000",
    "OPENAI_API_KEY": "sk-test",
    "EMAIL_SENDER": "foo@example.com",
}


def setup_env(monkeypatch):
    for k, v in REQUIRED_ENV.items():
        monkeypatch.setenv(k, v)


def import_main(monkeypatch):
    import gaij.settings as settings
    importlib.reload(settings)
    import gaij.main as main
    importlib.reload(main)
    return main


def test_main_creates_ticket(monkeypatch):
    setup_env(monkeypatch)
    main = import_main(monkeypatch)
    called = {}

    monkeypatch.setattr(
        main,
        "get_latest_email_from",
        lambda sender: {"subject": "Sub", "body": "Body"},
    )
    monkeypatch.setattr(
        main,
        "gpt_classify_issue",
        lambda subject, body: {"issueType": "Bug", "client": "Acme"},
    )

    def fake_create_ticket(summary, adf_description, client, issue_type):
        called.update(
            summary=summary,
            adf=adf_description,
            client=client,
            issue_type=issue_type,
        )

    monkeypatch.setattr(main, "create_ticket", fake_create_ticket)
    main.main()
    assert called == {
        "summary": "Sub",
        "adf": "Body",
        "client": "Acme",
        "issue_type": "Bug",
    }


def test_main_missing_sender(monkeypatch, caplog):
    setup_env(monkeypatch)
    monkeypatch.delenv("EMAIL_SENDER", raising=False)
    main = import_main(monkeypatch)
    with caplog.at_level("ERROR"):
        main.main()
    assert "EMAIL_SENDER environment variable not set" in caplog.text


def test_main_no_email(monkeypatch, caplog):
    setup_env(monkeypatch)
    main = import_main(monkeypatch)
    monkeypatch.setattr(main, "get_latest_email_from", lambda sender: None)
    with caplog.at_level("WARNING"):
        main.main()
    assert "No email found" in caplog.text
