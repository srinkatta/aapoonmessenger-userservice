import logging
import re

from pyfcm import FCMNotification

from user_service import settings
from user.helpers.v2 import notification as notification_v2

logging = logging.getLogger(__name__)


def extract_media(xml):
    media = re.findall(r'<MEDIA (\S+)=[""]?((?:.(?![""]?\s+(?:\S+)=|\s*\/?[>""]))+.)[""]?>', xml)
    return media


def extract_command_action(xml):
    command_action = re.findall(
        r'<COMMANDACTION (\S+)=[""]?((?:.(?![""]?\s+(?:\S+)=|\s*\/?[>""]))+.)[""]?>',
        xml,
    )
    return command_action


def extract_bubble_type(xml):
    """
    Extracts the bubble type from the provided XML string.
    Args:
        xml (str): The XML string containing message details.
    Returns:
        str: The bubble type extracted from the XML, or an empty string if not found.
    """
    bubble_type = re.search(r"<Bubble>(.*?)</Bubble>", xml)
    if bubble_type:
        return bubble_type.group(1)
    return ""


def extract_message_id(xml):
    """
    Extracts the message id from the provided XML string.
    Args:
        xml (str): The XML string containing message details.
    Returns:
        str: The data extracted from the XML, or an empty string if not found.
    """
    message_id_match = re.search(r"id=['\"]([^'\"]+)['\"]", xml)
    if message_id_match:
        return message_id_match.group(1)
    return ""


def extract_data(xml):
    """
    Extracts the data from the provided XML string.
    Args:
        xml (str): The XML string containing message details.
    Returns:
        str: The data extracted from the XML, or an empty string if not found.
    """
    data_match = re.findall(r"<Data>(.*?)</Data>", xml, re.DOTALL)
    if not data_match:
        pattern = r"<Data(?: xmlns='urn:xmpp:(?:Data|data)')?>(.*?)</Data>"
        data_match = re.findall(pattern, xml, re.DOTALL)
    if data_match:
        return data_match[0]
    return ""


def process_media(xml):
    media = extract_media(xml)
    if media and media[0][0] == "xmlns" and media[0][1] == "'urn:xmpp:media'":
        xml = xml.replace("<body>!~~!</body>", "<body>Media</body>")
        thumbnail = xml.find("<Thumbnail>")
        if thumbnail > 0:
            start_index = thumbnail + len("<Thumbnail>")
            end_index = xml.find("</Thumbnail>")
            thumbnail_content = xml[start_index:end_index]
            xml = xml.replace(thumbnail_content, "")
    return xml


def process_command_action(xml, message_value):
    command_action = extract_command_action(xml)
    if command_action and message_value == "Contact":
        if command_action[0][0] == "xmlns" and command_action[0][1] == "'urn:xmpp:commandaction'":
            xml = xml.replace("<body>!~~!</body>", "<body>Contact</body>")
            command_message = xml.find("<CommandMessage>")
            if command_message > 0:
                start_index = command_message + len("<CommandMessage>")
                end_index = xml.find("</CommandMessage>")
                actual_content = xml[start_index:end_index]
                updated_content = actual_content.replace("&quot;", '"')
                xml = xml.replace(actual_content, updated_content)
    return xml


def notify_android_device(token, name, data_message):
    push_service = FCMNotification(api_key=settings.ANDROID_FCM_API_KEY)
    android_data_message = {
        "Nick": name,
        "body": data_message["body"],
        "priority": "high",
        "sender_jid": data_message["notification"]["sender_jid"],
        "room_id": data_message["notification"]["room_id"],
        "bubble_type": data_message["notification"]["bubble_type"],
        "data": data_message["notification"]["data"],
        "message_id": data_message["notification"]["message_id"],
    }
    android_result = push_service.notify_single_device(
        registration_id=token,
        data_message=android_data_message,
        content_available=True,
    )
    print(f"Android Notification - Token: {token}, Data: {android_data_message}")
    print(f"Android Result:  {android_result}")
    logging.info(f"Android result: , {android_result}")


def notify_ios_device(token, name, message_value, data_message):
    push_service = FCMNotification(api_key=settings.FCM_API_KEY)
    result = push_service.notify_single_device(
        registration_id=token,
        message_title=name,
        message_body=message_value,
        data_message=data_message,
        content_available=True,
        extra_kwargs={"mutable_content": True},
    )
    print(
        f"iOS Notification - Token: {token}, Message: {message_value}, Title: {name}, Data: {data_message}"
    )
    print(f"IOS Result:  {result}")
    logging.info(f"IOS result: , {result}")


def prepare_data_message(to_user, from_user, message, xml, body):
    print(f"xml message: {xml}")
    name = from_user.name
    message_value = extract_message_value(xml)
    message_value = body[0] if message_value == "Text" else message_value
    bubble_type = extract_bubble_type(xml)
    data = extract_data(xml)
    message_id = extract_message_id(xml)

    data_message = {
        "notification": {
            "click_action": "ReplyOrRead",
            "title": name,
            "body": message_value,
            "sender_jid": from_user.jid,
            "room_id": "",
            "bubble_type": bubble_type,
            "data": data,
            "message_id": message_id,
            "sound": "default",
            "mutable-content": 1,
            "content-available": True,
        },
        "to": to_user.fcm_token,
        "Nick": name,
        "body": message_value,
        "priority": "high",
        "content_available": True,
    }
    print(f"data_message: {data_message}")
    return data_message


def extract_message_value(xml):
    message_value_dict = {
        "-6": "Reply",
        "-1": "Forward",
        "-3": "Like",
        "-4": "Dislike",
        "1": "Text",
        "2": "Image",
        "3": "Video",
        "4": "Audio",
        "5": "Document",
        "11": "Contact",
    }
    bubble_start = xml.find("<Bubble>") + len("<Bubble>")
    bubble_end = xml.find("</Bubble>")
    message_value = xml[bubble_start:bubble_end]
    return message_value_dict.get(message_value, None)


def notify_dm_v2(
    to_user=None,
    from_user=None,
    message=None,
    xml=None,
):
    """Refactored version of notify_dm function"""
    if xml:
        body = re.findall(r"<body>(.*?)</body>", xml)
        if body:
            data_message = prepare_data_message(to_user, from_user, message, xml, body)

            if not to_user.fcm_token:
                raise ValueError("FCM token is not available for the recipient user")

            notification = notification_v2.FirebaseNotificationService()
            if to_user.fcm_token and not to_user.apns_token:
                token = to_user.fcm_token
                print("Result for DM")
                print("Android")

                notification.notify_android_device(token, from_user.name, data_message)
            else:
                token = to_user.fcm_token
                print("iPhone")
                notification.notify_ios_device(token, data_message)
    return True


def notify_dm(
    to_user=None,
    from_user=None,
    message=None,
    xml=None,
):
    """
    Send a direct message notification to a user.

    This function sends a direct message notification to a specified user. The notification contains information
    about the sender, the type of message (e.g., text, image, video), and the content of the message.

    Args:
        to_user (User): The recipient user for the direct message.
        from_user (User): The sender user for the direct message.
        message (str): The text content of the direct message.
        xml (str): The XML representation of the direct message. It contains additional metadata about the message.

    Returns:
        bool: True if the notification was sent successfully, False otherwise.

    Note:
        - The `xml` parameter is used to extract additional information about the direct message, such as message type and media.
        - This function sends both Android and iOS notifications to the specified `to_user`.
        - The notifications are sent using Firebase Cloud Messaging (FCM) for Android and Apple Push Notification Service (APNs) for iOS.
    """
    if xml:
        body = re.findall(r"<body>(.*?)</body>", xml)
        if body:
            message_value_dict = {
                "-6": "Reply",
                "-1": "Forward",
                "-3": "Like",
                "-4": "Dislike",
                "2": "Image",
                "3": "Video",
                "4": "Audio",
                "5": "Document",
                "11": "Contact",
            }
            a = xml.find("<Bubble>") + len("<Bubble>")
            b = xml.find("</Bubble>")
            c = xml[a:b]
            delay = re.findall("(<delay.*?>)(.*?)(<\\/delay>)", xml)

            if body and "-" not in c and not delay:
                try:
                    message = message_value_dict[c]
                except BaseException:
                    pass
                media = re.findall(
                    r'<MEDIA (\S+)=[""]?((?:.(?![""]?\s+(?:\S+)=|\s*\/?[>""]))+.)[""]?>',
                    xml,
                )
                commandaction = re.findall(
                    r'<COMMANDACTION (\S+)=[""]?((?:.(?![""]?\s+(?:\S+)=|\s*\/?[>""]))+.)[""]?>',
                    xml,
                )
                if media:
                    if media[0][0] == "xmlns" and media[0][1] == "'urn:xmpp:media'":
                        xml = xml.replace("<body>!~~!</body>", "<body>Media</body>")
                        thumbnail = xml.find("<Thumbnail>")
                        if thumbnail > 0:
                            start_index = thumbnail + len("<Thumbnail>")
                            end_index = xml.find("</Thumbnail>")
                            thumbnail_content = xml[start_index:end_index]
                            xml = xml.replace(thumbnail_content, "")
                if commandaction and c == "11":
                    if (
                        commandaction[0][0] == "xmlns"
                        and commandaction[0][1] == "'urn:xmpp:commandaction'"
                    ):
                        xml = xml.replace("<body>!~~!</body>", "<body>Contact</body>")
                        commandmessage = xml.find("<CommandMessage>")
                        if commandmessage > 0:
                            start_index = commandmessage + len("<CommandMessage>")
                            end_index = xml.find("</CommandMessage>")
                            actual_content = xml[start_index:end_index]
                            updated_content = actual_content.replace("&quot;", '"')
                            xml = xml.replace(actual_content, updated_content)

                name = from_user.name
                data_message = {
                    "notification": {
                        "click_action": "ReplyOrRead",
                        "xml": xml,
                        "title": name,
                        "body": message,
                        "sound": "default",
                    },
                    "to": to_user.fcm_token,
                    "Nick": name,
                    "body": message,
                    "priority": "high",
                    "content_available": True,
                }
                print(data_message)
                if to_user.fcm_token and not to_user.apns_token:
                    token = to_user.fcm_token
                    push_service = FCMNotification(api_key=settings.FCM_API_KEY)
                    print("Result for DM")
                    print("Android")
                    android_data_message = {
                        "Nick": name,
                        "body": message,
                        "priority": "high",
                    }
                    android_result = push_service.notify_single_device(
                        registration_id=token,
                        data_message=android_data_message,
                        content_available=True,
                    )
                    print(android_result)
                    logging.info(f"Android result: , {android_result}")
                else:
                    token = to_user.fcm_token
                    push_service = FCMNotification(api_key=settings.FCM_API_KEY)
                    print("iPhone")
                    result = push_service.notify_single_device(
                        registration_id=token,
                        message_title=name,
                        message_body=message,
                        data_message=data_message,
                        content_available=True,
                        extra_kwargs={"mutable_content": True},
                    )
                    print(result)
                    logging.info(f"IOS result: , {result}")
                return True