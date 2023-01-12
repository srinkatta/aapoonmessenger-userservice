import requests
import json
from user_service import settings

try:
    from email import Charset
except Exception as e:
    from email import charset as Charset

import logging
from requests.exceptions import HTTPError
from user.helpers import sms
from django.core.mail import send_mail
from django.template import loader
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _


def s3_url_extract(url):
    if "socialchain-dev" in url or "mediadev" in url:
        return "https://mediadev.aapoon.com"
    elif "socialchain-prod" in url or "media.aapoon.com" in url:
        return "https://media.aapoon.com"
    else:
        return "https://media.aapoon.com"


def clear_bucket_from_path(path):
    if "socialchain-dev" in path:
        path = path.replace("/socialchain-dev", "")
        return path
    elif "socialchain-prod" in path:
        path = path.replace("/socialchain-prod", "")
        return path
    else:
        return path


def make_request(url, method, data={}, params={}):
    try:
        headers = {
            "content-type": "application/json",
            "Authorization": settings.AUTHORIZATION,
        }
        response = requests.request(
            method, url, data=json.dumps(data), params=params, headers=headers
        )
        response.raise_for_status()
        return response
    except (HTTPError, Exception) as e:
        logging.error(e)
        raise e


def send_sms_message(message, user, number):
    sms_client = sms.SMS(number, message, user)
    sms_client.send_generic_message()


def send_email_notification(user, template, subject):
    subject = _(f"{subject}")
    from_email = "support@aapoon.net"
    toemail = f"{user.email}"

    Charset.add_charset("utf-8", Charset.SHORTEST, None, "utf-8")

    html_message = loader.render_to_string(
        template,
        {
            "first_name": user.first_name,
        },
    )
    text_content = "Content"
    Charset.add_charset("utf-8", Charset.SHORTEST, None, "utf-8")
    send_mail(
        subject,
        text_content,
        from_email,
        [
            toemail,
        ],
        html_message=html_message,
    )


def phone_failure(self, request):
    subject = _("Max Attempts Reached on updated Phone Verification")

    from_email = settings.DEFAULT_FROM_EMAIL
    toemail = ["santosh@aapoon.net"]
    user = request.user
    name = f"{user.first_name} {user.last_name}"
    context = {
        "name": name,
        "email": user.email,
        "phone_number": user.phone_number,
        "module": "Phone Verification",
    }

    # text_content = render_to_string('config/email/kyc_failed_user.html', context)
    Charset.add_charset("utf-8", Charset.SHORTEST, None, "utf-8")
    send_mail(subject, context, from_email, toemail)


def feedback_mail(request, data):
    user = request.user
    subject = _("Feedback")
    from_email = settings.DEFAULT_FROM_EMAIL
    toemail = settings.SUPPORT_EMAIL
    text = data.get("message")
    topic = data.get("topic")
    url = data.get("url")
    email = data.get("email")
    try:
        name = data.get("name")
        phone = data.get("phone")
    except Exception as e:
        name = user.name
        phone = user.phone

    context = {
        "user_id": user.id,
        "content": text,
        "name": name,
        "email": email,
        "phone": phone,
        "country_code": user.country_code,
        "topic": topic,
        "url": url,
    }
    # text_content = render_to_string('config/email/feedback.html',context)
    Charset.add_charset("utf-8", Charset.SHORTEST, None, "utf-8")
    send_mail(subject, context, from_email, [toemail])
