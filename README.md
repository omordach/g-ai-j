# g-ai-j

## Overview

`g-ai-j` fetches the latest email from a Gmail inbox, classifies the message using OpenAI, then creates a matching ticket in Jira. The application is composed of small modules and logs to both the console and a log file.

### Processing flow
1. **Gmail** – retrieve the most recent message from a specified sender.
2. **GPT classification** – send the subject and body to OpenAI to determine the issue type and client.
3. **Jira** – create a ticket with the email details and the data returned by GPT.

## Code structure

| File | Purpose |
| ---- | ------- |
| `main.py` | Orchestrates the whole workflow: reads configuration, fetches the email, calls GPT, and finally creates the Jira ticket. |
| `gmail_client.py` | Wraps the Gmail API. Loads credentials from `token.json`, retrieves the latest message from the configured sender and extracts its plain text or HTML body. |
| `gpt_agent.py` | Uses the OpenAI Chat Completions API to classify the email into an issue type (`Bug`, `Task`, or `Story`) and to guess the client based on the email content. |
| `jira_client.py` | Builds the Atlassian Document Format (ADF) description and sends a REST request to create an issue in Jira using the required custom client field. |
| `logger_setup.py` | Configures logging so that messages go to STDOUT and to `/data/g-ai-j.log`. Ensure the `/data` directory exists in the runtime environment. |

## Configuration

Set the following environment variables (for local runs they can be placed in a `.env` file):

* `OPENAI_API_KEY` – key for the OpenAI API.
* `EMAIL_SENDER` – Gmail address from which to pull messages.
* `JIRA_URL` – base URL of the Jira instance.
* `JIRA_PROJECT_KEY` – key of the Jira project.
* `JIRA_USER` – Jira username.
* `JIRA_API_TOKEN` – Jira API token.
* `JIRA_CLIENT_FIELD_ID` – custom field ID that stores the client value.

A `token.json` file containing Gmail OAuth credentials must reside in the project root.

## Running locally

1. Ensure Python 3.11 is installed.
2. Copy `.env.example` to `.env` and fill in the values above.
3. Place `token.json` in the project root.
4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Create a directory for logs and run the app:

   ```bash
   mkdir -p data
   python main.py
   ```

The application processes the most recent email from `EMAIL_SENDER` and writes a log file to `/data/g-ai-j.log`.

## Running with Docker

### Build

```bash
docker build -t g-ai-j .
```

### Run

```bash
docker run --rm \
  -e OPENAI_API_KEY=... \
  -e EMAIL_SENDER=... \
  -e JIRA_URL=... \
  -e JIRA_PROJECT_KEY=... \
  -e JIRA_USER=... \
  -e JIRA_API_TOKEN=... \
  -e JIRA_CLIENT_FIELD_ID=... \
  -v $(pwd)/token.json:/app/token.json:ro \
  -v $(pwd)/logs:/data \
  g-ai-j
```

### docker-compose

```bash
cp .env.example .env  # fill in values
docker-compose up
```

The compose file mounts `token.json` and a local `logs` directory to `/data` inside the container.

## Deploying to GCP Cloud Run

1. **Build and push the image**

   ```bash
   gcloud builds submit --tag gcr.io/PROJECT_ID/g-ai-j
   ```

2. **Deploy**

   ```bash
   gcloud run deploy g-ai-j \
     --image gcr.io/PROJECT_ID/g-ai-j \
     --set-env-vars OPENAI_API_KEY=...,EMAIL_SENDER=...,JIRA_URL=...,JIRA_PROJECT_KEY=...,JIRA_USER=...,JIRA_API_TOKEN=...,JIRA_CLIENT_FIELD_ID=... \
     --set-secrets token.json=TOKEN_JSON:latest \
     --region REGION
   ```

   Store the Gmail `token.json` in Secret Manager as `TOKEN_JSON` and mount it at `/app/token.json` via `--set-secrets`. Cloud Run writes logs to STDOUT; the file log in `/data` is optional.
