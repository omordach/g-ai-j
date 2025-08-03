# g-ai-j

This project fetches an email from Gmail, classifies it using OpenAI, and then
creates a corresponding Jira ticket. Environment variables are used for API
credentials and configuration.

## Required environment variables

* `OPENAI_API_KEY` - API key for OpenAI
* `EMAIL_SENDER` - email address to search for in Gmail
* `JIRA_URL` - base URL of the Jira instance
* `JIRA_PROJECT_KEY` - key of the Jira project
* `JIRA_USER` and `JIRA_API_TOKEN` - credentials for Jira
* `JIRA_CLIENT_FIELD_ID` - custom field ID for the client value

Ensure a `token.json` file for Gmail API credentials is present in the project
root.

Install the requirements and run `python main.py` to process the latest email
from the configured sender.

## Running with Docker

Build the image:

```bash
docker build -t g-ai-j .
```

Run the container, providing the required environment variables and mounting the
`token.json` file into the container:

```bash
docker run --rm \
  -e OPENAI_API_KEY=... \
  -e EMAIL_SENDER=... \
  -e JIRA_URL=... \
  -e JIRA_PROJECT_KEY=... \
  -e JIRA_USER=... \
  -e JIRA_API_TOKEN=... \
  -e JIRA_CLIENT_FIELD_ID=... \
  -v $(pwd)/token.json:/app/token.json \
  g-ai-j
```

### Running with docker-compose

If you prefer using `docker-compose`, ensure a `docker-compose.yml` file is
present and then run:

```bash
docker-compose up
```

`docker-compose` will read variables from a `.env` file in the same directory,
allowing you to store the required environment variables there. Mount the
`token.json` file as a volume in the compose file so the container can access it.

