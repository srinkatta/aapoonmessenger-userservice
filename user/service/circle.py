import requests
from typing import (
    List,
    Dict,
)

from requests import Response
from user_service import settings


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
        self.headers = {"Authorization": settings.CIRCLE_MICROSERVICE_API_KEY}

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
        result = {}
        request_data = {
            "user_id": user_id,
            "user_jid": user_jid,
            "user_type": user_type,
            "fcm_token": fcm_token,
            "category": {
                "university": university,
                "college": college,
                "stream": stream,
                "program": program,
                "department": department,
                "specialization": specialization,
            },
        }
        try:
            response: Response = requests.post(
                self.user_subscribe_room_topic,
                json=request_data,
                headers=self.headers,
            )
            response.raise_for_status()
            result = response.json()
        except (requests.exceptions.RequestException, requests.exceptions.HTTPError):
            result = {}
        return result
