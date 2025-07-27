import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from logger_setup import logger

load_dotenv()

JIRA_URL = os.getenv("JIRA_URL")
PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")
ASSIGNEE = os.getenv("JIRA_USER")
CLIENT_FIELD_ID = os.getenv("JIRA_CLIENT_FIELD_ID")


def build_jira_description(body, gpt_data):
    content_blocks = []

    if body and body.strip():
        content_blocks.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": f"📩 Email Body:\n{body.strip()}"}]
        })
    else:
        content_blocks.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": "No email body found."}]
        })

    adf = {
        "type": "doc",
        "version": 1,
        "content": content_blocks
    }

    logger.info(f"ADF Description payload:\n{adf}")
    return adf


def create_jira_ticket(summary, body, issue_type, client, gpt_data, attachments=[]):
    url = f"{JIRA_URL}/rest/api/3/issue"
    auth = HTTPBasicAuth(os.getenv("JIRA_USER"), os.getenv("JIRA_API_TOKEN"))
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    payload = {
        "fields": {
            "project": {"key": PROJECT_KEY},
            "summary": summary,
            "description": build_jira_description(body, gpt_data),
            "issuetype": {"name": issue_type},
            CLIENT_FIELD_ID: [{"value": client}],
            "assignee": {"name": ASSIGNEE},
            "labels": ["Billable"],
            "priority": {"name": "Medium"},
        }
    }

    response = requests.post(url, auth=auth, headers=headers, json=payload)
    if response.status_code == 201:
        logger.info(f"Jira ticket created: {response.json()['key']}")
    else:
        logger.error(f"Failed to create Jira ticket: {response.status_code} {response.text}")
