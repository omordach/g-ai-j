import os

from gmail_client import get_latest_email_from
from gpt_agent import gpt_classify_issue
from jira_client import create_jira_ticket
from logger_setup import logger


def main():
    logger.info("g-ai-j started")

    sender = os.getenv("EMAIL_SENDER")
    if not sender:
        logger.error("EMAIL_SENDER environment variable not set")
        return

    email = get_latest_email_from(sender)
    if not email:
        logger.warning("No email found from the specified sender.")
        return

    logger.info(f"Processing email: {email['subject']}")
    gpt_data = gpt_classify_issue(email['subject'], email['body'])

    if not gpt_data.get("issueType"):
        logger.error("GPT could not classify the issue. Skipping ticket creation.")
        return

    logger.info(f"Email body for Jira:\n{email['body']}")

    create_jira_ticket(
        summary=email['subject'],
        body=email['body'],
        issue_type=gpt_data["issueType"],
        client=gpt_data.get("client", "N/A"),
        gpt_data=gpt_data,
        attachments=email.get("attachments", [])
    )


if __name__ == "__main__":
    main()
