# g-ai-j

Utility that turns Gmail messages into Jira tickets. In addition to the original one-shot script, the application now supports real-time processing on Google Cloud Run using Gmail push notifications delivered via Pub/Sub and Firestore for deduplication.

## Components

| File | Purpose |
| --- | --- |
| `app.py` | Flask service for Cloud Run. Handles `/healthz` and `/pubsub` endpoints. |
| `gmail_client.py` | Wrapper around Gmail API. Fetches messages, lists history updates, and extracts headers including `Message-ID` for deduplication. |
| `jira_client.py` | Creates Jira issues with ADF descriptions and client custom field. |
| `firestore_state.py` | Persists last processed history ID and recent message IDs in Firestore. |
| `gmail_watch.py` | Helper script to register or renew Gmail `users.watch`. |
| `main.py` | Legacy one-shot runner for manual local tests. |
| `logger_setup.py` | Configures logging to stdout. |
| `gpt_agent.py` | Uses OpenAI to classify emails and infer client names. |


## Running locally

1. Install dependencies and configure environment variables in `.env` (see below).
2. Obtain Gmail OAuth credentials and save as `token.json` in the project root.
3. Run the one-shot script:
   ```bash
   python main.py
   ```

## Cloud Run deployment

1. **Build image**
   ```bash
   gcloud builds submit --tag gcr.io/PROJECT_ID/g-ai-j
   ```
2. **Deploy service**
   ```bash
   gcloud run deploy g-ai-j \
     --image gcr.io/PROJECT_ID/g-ai-j \
     --region REGION \
     --set-env-vars $(cat .env | xargs)
   ```
3. **Create Pub/Sub topic and push subscription** targeting the Cloud Run URL.
4. **Register Gmail watch** using the helper script:
   ```bash
   python gmail_watch.py
   ```
   Re-run periodically (e.g. via Cloud Scheduler) to renew the watch before expiration.

The service validates its configuration at startup and will exit if required
Jira environment variables are missing or if `token.json` is absent. Ensure
these are set before deployment so the container fails fast on
misconfiguration.


When Gmail pushes a notification to Pub/Sub, `app.py` retrieves new messages, asks GPT to classify the issue and determine the client from the email body, creates Jira tickets, and records processed message IDs in Firestore to avoid duplicates. The `Message-ID` header is used to track each email reliably.


## Required environment variables

```
GCP_PROJECT_ID=...
GCP_FIRESTORE_COLLECTION=gaij_state
PUBSUB_TOPIC=gmail-notifications
GMAIL_USER_ID=me
JIRA_URL=...
JIRA_USER=...
JIRA_API_TOKEN=...
JIRA_PROJECT_KEY=...
JIRA_ASSIGNEE=...
JIRA_CLIENT_FIELD_ID=...
DOMAIN_TO_CLIENT_JSON={"example.com":"Example"}
CLIENT_LIST_JSON=["Example","N/A"]
ALLOWED_SENDERS_JSON=["forwarder@example.com"]
OPENAI_API_KEY=...

```

### Gmail token configuration

The application reads Gmail OAuth credentials from the path given by
`GMAIL_TOKEN_FILE_PATH`. At start-up the token file must exist at that
location; otherwise the service will fail fast.

To check which path is in use, inspect the environment variable:

```
echo $GMAIL_TOKEN_FILE_PATH
```

If you prefer to inject the token content directly, set
`GMAIL_TOKEN_FILE` to the JSON contents and the application will write
the file to `GMAIL_TOKEN_FILE_PATH` on boot. A typical configuration
inside Docker is:

```
export GMAIL_TOKEN_FILE_PATH=/app/token.json
export GMAIL_TOKEN_FILE="$(cat token.json)"
```

Verify that the file exists before running the service:

```
[ -f "$GMAIL_TOKEN_FILE_PATH" ] && echo "Token present" || echo "Missing token"
```

## Docker

```
docker build -t g-ai-j .
docker run --rm -p 8080:8080 g-ai-j
```

Cloud Run reads logs from stdout; the application does not write to local files.

## Continuous Integration / Deployment

This repository includes a GitHub Actions workflow that runs the test suite on
every push and pull request. Pushes to the `main` branch will deploy the
application to Cloud Run after tests pass.

### GitHub configuration

Store the following secrets in your repository settings:

| Secret | Purpose |
| --- | --- |
| `GCP_PROJECT_ID` | Google Cloud project that hosts Cloud Run |
| `GCP_REGION` | Region for the Cloud Run service (e.g. `us-central1`) |
| `CLOUD_RUN_SERVICE` | Name of the Cloud Run service |
| `GCP_SA_KEY` | JSON key for a service account used for deployment |

### Google Cloud configuration

1. Create a service account and download a JSON key. Grant it **Cloud Run
   Admin**, **Service Account User**, and **Cloud Build Editor** roles.
2. Enable the Cloud Run and Cloud Build APIs.
3. Pre-create the Cloud Run service or allow the workflow to create it on the
   first deploy. Configure required environment variables in Cloud Run.

