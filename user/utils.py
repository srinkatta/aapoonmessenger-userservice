import re
import requests
import json
from datetime import datetime
import logging
from requests.exceptions import HTTPError

try:
    from email import Charset
except Exception as e:
    from email import charset as Charset

from django.core.mail import send_mail
from django.utils.html import strip_tags
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from user.helpers import sms
from user.choices import COUNTRIES_CHOICES
from user_service import settings


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
            "Authorization": settings.XMPP_AUTHORIZATION,
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
    to_email = f"{user.email}"

    context = {
        "name": user.name,
    }
    html_message = render_to_string(template, context)
    plain_message = strip_tags(html_message)
    send_mail(subject, plain_message, from_email, [to_email], html_message=html_message)


def phone_failure(user, subject):

    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = ["support@aapoon.net"]
    context = {
        "phone_number": user.phone_number,
        "module": "Phone Verification",
    }

    text_content = render_to_string("config/email/max_attempts_otp.html", context)
    Charset.add_charset("utf-8", Charset.SHORTEST, None, "utf-8")
    send_mail(subject, text_content, from_email, to_email)


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

    text_content = render_to_string("config/email/feedback.html", context)
    Charset.add_charset("utf-8", Charset.SHORTEST, None, "utf-8")
    send_mail(subject, text_content, from_email, [toemail])


def calculate_age(dob):
    dob = datetime.strptime(dob, "%Y-%m-%d")
    today = datetime.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return age


def check_special(value):
    result = re.match("^[`@?^%*={}|\\?/]", value)
    return bool(result)


def is_english(value):
    try:
        value.encode(encoding="utf-8").decode("ascii")
    except UnicodeDecodeError:
        return False
    else:
        return True


def user_kyc_status(user):
    status = ""
    try:
        logs = user.logs.filter().first()
        logs = logs.kyc_logs
        if logs:
            attempts = re.findall(r"<b>Target Image: https://", logs)
    except Exception as err:
        logging.debug("User kyc logs not found: %s", err)
    user_kyc_settings = user.settings.filter().first()
    kyc_done = user_kyc_settings.kyc_done
    if logs and len(attempts) >= 2:
        if user.phone_number_verified and len(attempts) >= 2 and not kyc_done:
            status = "Pending"
    elif kyc_done:
        status = "Fully Verified"
    elif user.phone_number_verified:
        status = "Basic Verified"
    else:
        status = "Phone Registered"

    return status


def get_month(dob):
    if "Jan" in dob:
        return "Jan"
    elif "Feb" in dob:
        return "Feb"
    elif "Mar" in dob:
        return "Mar"
    elif "Apr" in dob:
        return "Apr"
    elif "May" in dob:
        return "May"
    elif "Jun" in dob:
        return "Jun"
    elif "Jul" in dob:
        return "Jul"
    elif "Aug" in dob:
        return "Aug"
    elif "Sep" in dob:
        return "Sep"
    elif "Oct" in dob:
        return "Oct"
    elif "Nov" in dob:
        return "Nov"
    elif "Dec" in dob:
        return "Dec"
    else:
        pass


def month_checker(month):
    import calendar

    months = dict((v, k) for k, v in enumerate(calendar.month_abbr))
    return months[month]


def get_dob(dateofbirth):
    # check date of birth

    months = [
        "Jan",
        "Jun",
        "Feb",
        "Apr",
        "Nov",
        "Oct",
        "Mar",
        "Sep",
        "Jul",
        "Aug",
        "May",
        "Dec",
    ]
    try:
        month = get_month(dateofbirth)
        if any(x in month for x in months):
            numeric_month = month_checker(month)
            dateofbirth = dateofbirth.replace(month, str(numeric_month))
            date_of_birth = dob_format_check_1(dateofbirth)

    except:
        date_of_birth = dob_format_check_2(dateofbirth)

    return date_of_birth


def dob_format_check_1(dateofbirth):
    try:
        date_of_birth = datetime.strptime(dateofbirth, "%Y-%m-%d").strftime("%Y-%m-%d")
    except:
        try:
            date_of_birth = datetime.strptime(dateofbirth, "%d-%m-%Y").strftime(
                "%Y-%m-%d"
            )
        except:
            try:
                date_of_birth = datetime.strptime(dateofbirth, "%d%m%Y").strftime(
                    "%Y-%m-%d"
                )
            except:
                try:
                    date_of_birth = datetime.strptime(dateofbirth, "%m%d%Y").strftime(
                        "%Y-%m-%d"
                    )
                except:
                    try:
                        date_of_birth = datetime.strptime(
                            dateofbirth, "%d %m %Y"
                        ).strftime("%Y-%m-%d")
                    except:
                        try:
                            date_of_birth = datetime.strptime(
                                dateofbirth, "%Y %m %d"
                            ).strftime("%Y-%m-%d")
                        except:
                            try:
                                date_of_birth = datetime.strptime(
                                    dateofbirth, "%Y/%m/%d"
                                ).strftime("%Y-%m-%d")
                            except:
                                try:
                                    date_of_birth = datetime.strptime(
                                        dateofbirth, "%m/%d/%Y"
                                    ).strftime("%Y-%m-%d")
                                except:
                                    date_of_birth = datetime.strptime(
                                        dateofbirth, "%d/%m/%Y"
                                    ).strftime("%Y-%m-%d")
    return date_of_birth


def dob_format_check_2(dateofbirth):
    try:
        date_of_birth = datetime.strptime(dateofbirth, "%Y-%m-%d").strftime("%Y-%m-%d")
    except:
        try:
            date_of_birth = datetime.strptime(dateofbirth, "%d-%m-%Y").strftime(
                "%Y-%m-%d"
            )
        except:
            try:
                date_of_birth = datetime.strptime(dateofbirth, "%d%m%Y").strftime(
                    "%Y-%m-%d"
                )
            except:
                try:
                    date_of_birth = datetime.strptime(dateofbirth, "%m%d%Y").strftime(
                        "%Y-%m-%d"
                    )
                except:
                    try:
                        date_of_birth = datetime.strptime(
                            dateofbirth, "%d %m %Y"
                        ).strftime("%Y-%m-%d")
                    except:
                        try:
                            date_of_birth = datetime.strptime(
                                dateofbirth, "%Y %m %d"
                            ).strftime("%Y-%m-%d")
                        except:
                            try:
                                date_of_birth = datetime.strptime(
                                    dateofbirth, "%Y/%m/%d"
                                ).strftime("%Y-%m-%d")
                            except:
                                try:
                                    date_of_birth = datetime.strptime(
                                        dateofbirth, "%m/%d/%Y"
                                    ).strftime("%Y-%m-%d")
                                except:
                                    try:
                                        date_of_birth = datetime.strptime(
                                            dateofbirth, "%Y%m%d"
                                        ).strftime("%Y-%m-%d")
                                    except:
                                        date_of_birth = datetime.strptime(
                                            dateofbirth, "%d/%m/%Y"
                                        ).strftime("%Y-%m-%d")
    return date_of_birth


def get_key_from_choices(data, CHOICES):
    match = ""
    data = data[:-1]

    for value in CHOICES:
        if data == value[1]:
            match += value[0]
    return match


def get_data_from_choices(key, CHOICES):
    country = ""
    match = ""

    for value in CHOICES:
        if key == value[0]:
            match += value[1]
            for s in match:
                if s == "(":
                    break
                else:
                    country += s

    country_index = get_key_from_choices(country, COUNTRIES_CHOICES)

    return country_index


class CustomPagination(PageNumberPagination):
    def get_paginated_response(self, data):
        return Response({"results": data})
