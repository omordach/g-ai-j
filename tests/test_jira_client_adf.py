
def test_build_adf(app_setup):
    jira_client = app_setup["jira_client"]
    text = "Line1\nLine2"
    adf = jira_client.build_adf(text)
    assert adf["content"][0]["content"][0]["text"] == "Line1"
    assert adf["content"][1]["content"][0]["text"] == "Line2"


def test_create_ticket_payload(monkeypatch, app_setup):
    jira_client = app_setup["jira_client"]
    captured = {}

    def fake_post(url, auth=None, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        class Resp:
            status_code = 201
            def json(self):
                return {"key": "ABC-1"}
        return Resp()

    monkeypatch.setattr(jira_client.requests, "post", fake_post)
    key = jira_client.create_ticket(
        "Summary",
        {"type": "doc", "content": []},
        "OETraining",
        labels=["Billable", "email_msgid_abc"],
    )
    assert key == "ABC-1"
    fields = captured["json"]["fields"]
    assert fields[jira_client.CLIENT_FIELD_ID] == [{"value": "OETraining"}]
    assert "email_msgid_abc" in fields["labels"]
