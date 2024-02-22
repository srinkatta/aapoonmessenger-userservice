import requests
import json
from typing import (
    List,
    Dict,
)

from requests import Response
from user_service import settings
from loguru import logger


class Circle:
    """
    Class for interacting with the Circle microservice.
    """

    def __init__(self):
        """
        Initialize Circle microservice client.
        """
        self.base_url = settings.CIRCLE_MICROSERVICE_URL
        self.user_subscribe_room_topic = (
            f"{self.base_url}api/circles/assign_user_room_topic/"
        )
        self.headers = {"x-api-key": settings.CIRCLE_MICROSERVICE_API_KEY}

    def assign_user_room_topic(
        self,
        user_id: int,
        user_jid: str = "",
        user_type: str = "",
        fcm_token: str = "",
        university: str = "",
        college: str = "",
        stream: str = "",
        program: List[str] = [],
        department: List[str] = [],
        specialization: List[str] = [],
    ) -> Dict:
        """
        Assigns a user to a room and topic in the Circle microservice.

        Args:
            user_jid (str): The JID of the user.
            fcm_token (str): The FCM token of the user.
            university (str): The university of the user.
            college (str): The college of the user.
            stream (str): The stream of the user.
            program (List[str]): The programs of the user.
            department (List[str]): The departments of the user.
            specialization (List[str]): The specializations of the user.

        Returns:
            Dict: A dictionary containing the result of the operation.
        """
        print("Triggered circle assign_user_room_topic method")
        result = {}
        request_data: dict = {
            "user_id": user_id,
            "user_jid": user_jid,
            "user_type": user_type,
            "fcm_token": fcm_token,
            "university": university,
            "college": college,
            "stream": stream,
            "program": program,
            "department": department,
            "specialization": specialization,
        }
        for key, value in request_data.items():
            if isinstance(value, list) and not value:
                request_data[key] = None

        print(request_data)
        try:
            response: Response = requests.post(
                self.user_subscribe_room_topic,
                json=request_data,
                headers=self.headers,
            )
            response.raise_for_status()
            result = response.json()
            print(result)
        except (
            requests.exceptions.RequestException,
            requests.exceptions.HTTPError,
        ) as exc:
            logger.exception(
                f"Error while subscribing Circle room and FCM topic: {exc}"
            )
            result = {}
        return result
