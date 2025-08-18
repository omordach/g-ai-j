# Validation Plan

This repository includes a pytest suite that exercises the core workflows of
`g-ai-j` using mocked external services.  The tests cover:

* **Pub/Sub handler** – happy path, duplicate history IDs, and duplicate message
  IDs.  Verifies Gmail parsing, client mapping, Jira payloads, Firestore updates
  and idempotency.
* **Gmail MIME parsing** – extraction of text from HTML bodies and nested
  multipart structures.
* **Jira ADF building** – multi-line body to ADF paragraphs and correct custom
  field/label formatting when creating issues.
* **Firestore state** – reading/writing `last_history_id`, tracking processed
  message IDs with pruning.
* **Gmail watch renewal** – registering a watch and renewing when expiration is
  near.

All external dependencies (Gmail API, Jira, Firestore, OpenAI) are replaced with
in-memory fakes or mocks, so the suite runs offline and is deterministic.

## Running the tests locally

```bash
pip install -r requirements.txt
pytest
```

## Running with Docker

```bash
docker build -t g-ai-j .
docker run --rm -v "$PWD":/app g-ai-j pytest
```

## Running in CI

Configure the CI job to install dependencies and execute `pytest` in the project
root.  No network access or secrets are required for the tests.
