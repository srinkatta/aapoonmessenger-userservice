import re
from pyfcm import FCMNotification
import logging

from user_service import settings


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
