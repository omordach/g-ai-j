
# One-click Infra for Gmail-AI-Jira (GCP)

This folder contains a single-command installer that:
- Enables required Google Cloud APIs
- Creates Artifact Registry and builds your image with Cloud Build
- Creates runtime & deployer Service Accounts and grants minimal roles
- Creates/updates Secret Manager entries from your local `.env`
- Sets up Pub/Sub (topic + push subscription)
- Initializes Firestore (Native) and grants the runtime SA `roles/datastore.user`
- Deploys to Cloud Run with secrets wired exactly like your current setup

## Prereqs

- Google Cloud project with billing enabled
- Authenticated `gcloud` (`gcloud auth login` + `gcloud auth application-default login`)
- Ansible 2.15+ (`pipx install ansible-core` recommended)
- A local `.env` at repo root with keys (non-empty values become secrets):



JIRA_URL=
JIRA_PROJECT_KEY=
JIRA_USER=
JIRA_API_TOKEN=
JIRA_CLIENT_FIELD_ID=
JIRA_ASSIGNEE=

GMAIL_TOKEN_FILE_PATH=/workspace/token.json
GMAIL_TOKEN_FILE=
GMAIL_USER_ID=me

DOMAIN_TO_CLIENT_JSON={}
ALLOWED_SENDERS_JSON=[]

APP_HOST=127.0.0.1
APP_PORT=8080

GCP_PROJECT_ID=
GCP_FIRESTORE_COLLECTION=gaij_state
PUBSUB_TOPIC=

OPENAI_API_KEY=
EMAIL_SENDER=

CLIENT_LIST=
CLIENT_LIST_JSON=


> Tip: If you don’t have a Gmail refresh token yet, deploy first, run your auth flow once, then update the `GMAIL_TOKEN_FILE` secret with the minted token JSON.

## Run

```bash
export PROJECT_ID=<your-project-id>  # or set GCP_PROJECT_ID in .env
./infra/install.sh
```

Re-running is idempotent (safe). It will only create what’s missing and update secrets when your .env values change.

Notes

Firestore runs in EU multi-region eur3; change in install.yml if needed.

Pub/Sub push subscription authenticates with the runtime SA using OIDC.

If you later want Filestore or a Serverless VPC Access connector, add a small role and redeploy with the relevant flags (left out here to keep costs and complexity low).
