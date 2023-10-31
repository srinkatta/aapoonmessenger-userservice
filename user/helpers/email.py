import logging

from django.conf import settings
from postmarker.core import PostmarkClient
from postmarker.exceptions import ClientError


def send_email_with_postmark(subject, html_content, from_email, to_email):
    """
    Send an email using Postmark.

    Parameters:
    subject (str): The subject of the email.
    html_content (str): The HTML content of the email.
    from_email (str): The sender's email address.
    to_email (str): The recipient's email address.

    Returns:
    bool: True if the email was sent successfully, False otherwise.
    """
    try:
        client = PostmarkClient(server_token=settings.POSTMARK_SERVER_TOKEN)
        response = client.emails.send(
            From=from_email, To=to_email, Subject=subject, HtmlBody=html_content
        )
        if response["Message"] == "OK":
            return True
        else:
            logging.info("Error while sending Email from Postmark")
            return False

    except ClientError as e:
        logging.exception("Error while sending Email from Client %s" % e)
