import json
import logging
import re
import ipaddress
import socket
from collections import OrderedDict
from datetime import datetime

import requests
from requests.exceptions import HTTPError

try:
    from email import Charset
except Exception as e:
    from email import charset as Charset

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from user.choices import COUNTRIES_CHOICES
from user.helpers import sms
from user_service import settings

logging = logging.getLogger(__name__)

DATE_FORMATS = [
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d%m%Y",
    "%m%d%Y",
    "%d %m %Y",
    "%Y %m %d",
    "%Y/%m/%d",
    "%m/%d/%Y",
    "%Y%m%d",
    "%d/%m/%Y",
]


def s3_url_extract(url):
    """
    Extract a base URL based on the input URL.

    Args:
        url (str): The input URL.

    Returns:
        str: A base URL determined by the input URL.
    """
    if settings.AWS_S3_BUCKET_NAME in url or settings.AWS_CDN_DOMAIN in url:
        return f"https://{settings.AWS_CDN_DOMAIN}.{settings.HOST_DOMAIN}"
    return f"https://{settings.AWS_CDN_DOMAIN}.{settings.HOST_DOMAIN}"


def clear_bucket_from_path(path):
    """
    Remove specific prefixes from a given path.

    Args:
        path (str): The input path.

    Returns:
        str: The path with specified prefixes removed.
    """
    if settings.AWS_S3_BUCKET_NAME in path:
        return path.replace(f"/{settings.AWS_S3_BUCKET_NAME}", "")
    return path


def make_request(url, method, data={}, params={}):
    """
    Make an HTTP request to a specified URL.

    Args:
        url (str): The target URL for the HTTP request.
        method (str): The HTTP method to use (e.g., 'GET', 'POST', etc.).
        data (dict, optional): The request payload data in JSON format. Default is an empty dictionary.
        params (dict, optional): Query parameters to include in the request. Default is an empty dictionary.

    Returns:
        requests.Response: The HTTP response object.

    Raises:
        HTTPError: If the HTTP request returns a non-200 status code.
        Exception: For other unexpected errors during the request.
    """
    print(settings.XMPP_AUTHORIZATION)
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
    """
    Send an SMS message using the Twilio SMS service.

    Args:
        message (str): The text of the SMS message to send.
        user: The user associated with the SMS (e.g., sender).
        number (str): The recipient's phone number in E.164 format.

    Returns:
        None
    """
    sms_client = sms.TWILIO_SMS(number, message, user)
    sms_client.send_generic_message()


def send_email_notification(user, template, subject):
    """
    Send an email notification to a user using an HTML template.

    Args:
        user: The user to whom the email is sent.
        template (str): The path to the HTML template for the email content.
        subject (str): The subject line of the email.

    Returns:
        None
    """
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
    """
    Send an email notification about phone verification failure.

    Args:
        user: The user associated with the phone verification.
        subject (str): The subject line of the email.

    Returns:
        None
    """
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
    """
    Send an email with user feedback.

    Args:
        request: The HTTP request object.
        data (dict): Feedback data including message, topic, URL, email, name, phone.

    Returns:
        None
    """
    user = request.user
    subject = _("Feedback")
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = settings.SUPPORT_EMAIL
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

    html_message = render_to_string("config/email/feedback.html", context)
    plain_message = strip_tags(html_message)
    send_mail(subject, plain_message, from_email, [to_email], html_message=html_message)


def calculate_age(dob):
    """
    Calculate age based on the provided date of birth.

    Args:
        dob (str): Date of birth in the format 'YYYY-MM-DD'.

    Returns:
        int: Calculated age.
    """
    dob = datetime.strptime(dob, "%Y-%m-%d")
    today = datetime.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return age


def check_special(value):
    """
    Check if a string contains a special character from a predefined set.

    Args:
        value (str): The string to be checked.

    Returns:
        bool: True if a special character is found, False otherwise.
    """
    result = re.match("^[`@?^%*={}|\\?/]", value)
    return bool(result)


def is_english(value):
    """
    Check if a string consists only of English characters (ASCII).

    Args:
        value (str): The string to be checked.

    Returns:
        bool: True if the string consists only of English characters, False otherwise.
    """
    try:
        value.encode(encoding="utf-8").decode("ascii")
    except UnicodeDecodeError:
        return False
    else:
        return True


def user_kyc_status(user):
    """
    Determine the KYC status of a user based on various criteria.

    Args:
        user: The user for whom the KYC status is determined.

    Returns:
        str: The KYC status of the user ('Pending', 'Fully Verified', 'Basic Verified', 'Phone Registered').
    """
    status = ""
    try:
        logs = user.logs.filter().first()
        logs = logs.kyc_logs
        if logs:
            attempts = re.findall(r"<b>Target Image: https://", logs)
    except Exception as err:
        logging.debug("User kyc logs not found: %s", err)
    try:
        user_kyc_settings = user.settings.filter().first()
        kyc_done = user_kyc_settings.kyc_done
        if logs and len(attempts) >= 2 and user.phone_number_verified and not kyc_done:
            status = "Pending"
        elif kyc_done:
            status = "Fully Verified"
        elif (
            user.phone_number_verified
            and user_kyc_settings.account_details
            and not kyc_done
        ):
            status = "Basic Verified"
        else:
            status = "Phone Registered"
    
        return status
    except Exception as err:
        logging.debug("User kyc settings not found: %s", err)
        return status


def get_month(dob):
    """
    Retrieve the abbreviated month name from a date-related string.

    Args:
        dob (str): The input string, possibly containing a date.

    Returns:
        str or None: The abbreviated month name ('Jan', 'Feb', ..., 'Dec') if found, or None if not found.
    """
    months = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]

    for month in months:
        if month in dob:
            return month

    return None


def month_checker(month):
    """
    Convert an abbreviated month name into its corresponding numeric representation.

    Args:
        month (str): The abbreviated month name (e.g., 'Jan', 'Feb', ..., 'Dec').

    Returns:
        int: The numeric representation of the month (1 for Jan, 2 for Feb, ..., 12 for Dec).
    """
    month_dict = {
        "Jan": 1,
        "Feb": 2,
        "Mar": 3,
        "Apr": 4,
        "May": 5,
        "Jun": 6,
        "Jul": 7,
        "Aug": 8,
        "Sep": 9,
        "Oct": 10,
        "Nov": 11,
        "Dec": 12,
    }
    return month_dict.get(month, 1)


def get_dob(dateofbirth):
    """
    Process a date of birth (DOB) string, attempting to standardize its format.

    Args:
        dateofbirth (str): The date of birth string in various formats.

    Returns:
        str: A standardized date of birth string.
    """

    month = get_month(dateofbirth)
    if month:
        numeric_month = month_checker(month)
        dateofbirth = dateofbirth.replace(month, f"{numeric_month:02d}")

    return dob_format(dateofbirth)


def dob_format(dateofbirth):
    """
    Process a date of birth (DOB) string, attempting to standardize its format.

    Args:
        dateofbirth (str): The date of birth string in various formats.

    Returns:
        str: A standardized date of birth string.
    """

    for format in DATE_FORMATS:
        try:
            return datetime.strptime(dateofbirth, format).strftime("%Y-%m-%d")
        except ValueError:
            continue

    raise ValueError("Invalid date format provided for dateofbirth")


def get_key_from_choices(data, CHOICES):
    """
    Get the corresponding key from a list of choices based on a given data value.

    Args:
        data: The data value to match.
        CHOICES: A list of tuples representing choices where the first element is the key and the second is the value.

    Returns:
        str: The corresponding key based on the matched data value, or an empty string if no match is found.
    """
    match = ""
    data = data[:-1]

    for value in CHOICES:
        if data == value[1]:
            match += value[0]
    return match


def get_data_from_choices(key, CHOICES):
    """
    Retrieve data from a list of choices based on a given key.

    Args:
        key: The key to match.
        CHOICES: A list of tuples representing choices where the first element is the key and the second is the value.

    Returns:
        str: The extracted data based on the matched key, or an empty string if no match is found.
    """
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
    """
    Custom pagination class that modifies the structure of the paginated response.

    Instead of the default structure, this class returns the paginated data under a "results" key.

    Example usage:
    pagination_class = CustomPagination
    """

    def get_paginated_response(self, data):
        """
        Customize the structure of the paginated response.

        Args:
            data: The paginated data.

        Returns:
            Response: A Response object containing the paginated data under a "results" key.
        """
        return Response({"results": data})


class GenericPagination(PageNumberPagination):
    """
    Custom pagination class that modifies the structure and content of the paginated response.

    This class includes additional metadata in the paginated response, such as count, next, previous, and results.

    Example usage:
    pagination_class = GenericPagination
    """

    page_size = 50
    page_size_query_param = "page_size"

    def get_paginated_response(self, data):
        """
        Customize the structure and content of the paginated response.

        Args:
            data: The paginated data.

        Returns:
            Response: A Response object containing metadata and the paginated data.
        """
        next_link = self.get_next_link() or None
        if next_link and "https" not in next_link:
            next_link = self.get_next_link().replace("http", "https")

        previous_link = self.get_previous_link() or None
        if previous_link and "https" not in previous_link:
            previous_link = self.get_previous_link().replace("http", "https")

        return Response(
            OrderedDict(
                [
                    ("count", self.page.paginator.count),
                    ("next", next_link),
                    ("previous", previous_link),
                    ("results", data),
                ]
            )
        )
    
class PreventSSRF:
    def is_ip_in_network(ip: str, network: str) -> bool:
        """
        Check if an IP address is in a network.
        """
        return ipaddress.ip_address(ip) in ipaddress.ip_network(network)

    def get_ip_from_hostname(hostname: str) -> str | None:
        """
        Get IP address from a hostname.
        """
        try:
            return socket.gethostbyname(hostname)
        except socket.gaierror:
            return None

    def is_host_allowed(hostname: str) -> bool:
        """
        Check if a host is allowed based on whitelist and blacklist.
        """
        ip = PreventSSRF.get_ip_from_hostname(hostname)

        try:
            if not ip:
                return False

            for network in settings.FORBIDDEN_HOSTS_BLACKLIST:
                if PreventSSRF.is_ip_in_network(ip, network):
                    return False

            if hostname not in settings.ALLOWED_HOSTS_WHITELIST:
                return False
        except Exception:
            return False

        return True

    def is_valid_url(url: str) -> bool:
        """
        Check if the given URI is valid.
        """
        regex = re.compile(
            r'^(?:http|ftp)s?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|'
            r'\[?[A-F0-9]*:[A-F0-9:]+\]?)'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        return re.match(regex, url) is not None
