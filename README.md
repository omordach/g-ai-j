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
