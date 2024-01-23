from typing import Dict, Optional, Any
import requests
from requests.models import Response
import logging

from user_service import settings

logger = logging.getLogger(__name__)


class KYC:
    """
    Utility class to interact with the user microservice and retrieve user details.

    Attributes:
        base_url (str): Base URL of the user microservice.

    Methods:
        - face_detect(target_image: str) -> Dict: Retrieve user details based on a user ID or JID.
        - face_comparison(target_image: str, source_image: str) -> Dict: Compare two face images.

    Note:
        - This class is designed to interact with the user microservice API.
        - The methods 'face_detect' and 'face_comparison' use the 'requests' library to make HTTP requests.
    """

    def __init__(self):
        self.base_url = settings.KYC_MICROSERVICE_URL

    def face_detect(self, target_image: str) -> Dict:
        """
        Retrieve user details based on the target_image (either user ID or JID).

        Args:
            target_image (str): The user ID or JID of the user.

        Returns:
            dict: A dictionary containing the user details.
        """
        request_data: dict = self._prepare_request(target_image=target_image)
        try:
            response: Response = requests.post(
                f"{self.base_url}/api/kyc/face-detect",
                json=request_data,
            )
            response.raise_for_status()
            face_detect_response = self._prepare_response_body(response)
        except requests.exceptions.RequestException as exc:
            logger.exception(f"Error while face detection: {exc}")
            face_detect_response = {}
        return face_detect_response

    def face_comparison(self, target_image: str, source_image: str) -> Dict:
        """
        Compare two face images.

        Args:
            target_image (str): The target user's image.
            source_image (str): The source image for comparison.

        Returns:
            dict: A dictionary containing the result of the face comparison.
        """
        request_data: dict = self._prepare_request(
            target_image=target_image,
            source_image=source_image,
        )
        try:
            response: Response = requests.post(
                f"{self.base_url}/api/kyc/face-comparison",
                json=request_data,
            )
            response.raise_for_status()
            face_compare_response = self._prepare_response_body(response)
        except requests.exceptions.RequestException as exc:
            logger.exception(f"Error during face comparison: {exc}")
            face_compare_response = {}
        return face_compare_response

    def text_extract(self, source_image: str) -> Dict:
        """
        Extract Text

        Args:
            source_image (str): The source image for ocr.

        Returns:
            dict: A dictionary containing the result of the face comparison.
        """
        request_data: dict = self._prepare_request(
            source_image=source_image,
        )
        try:
            response: Response = requests.post(
                f"{self.base_url}/api/kyc/text-extract",
                json=request_data,
            )
            response.raise_for_status()
            text_extract_response = self._prepare_response_body(response)
        except requests.exceptions.RequestException as exc:
            logger.exception(f"Error during face comparison: {exc}")
            text_extract_response = {}
        return text_extract_response

    def analyze_id(self, source_image: str) -> Dict:
        """
        Analyze ID Text

        Args:
            source_image (str): The source image for ocr.

        Returns:
            dict: A dictionary containing the result of the face comparison.
        """
        request_data: dict = self._prepare_request(
            source_image=source_image,
        )
        try:
            response: Response = requests.post(
                f"{self.base_url}/api/kyc/analyze-id",
                json=request_data,
            )
            response.raise_for_status()
            text_extract_response = self._prepare_response_body(response)
        except requests.exceptions.RequestException as exc:
            logger.exception(f"Error during face comparison: {exc}")
            text_extract_response = {}
        return text_extract_response

    def _prepare_request(
        self,
        target_image: Optional[str] = None,
        source_image: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Prepare the request body for sending to the user microservice.

        Args:
            target_image (str): The target user's image.
            source_image (str): The source image for comparison.

        Returns:
            dict: A dictionary containing the request data.
        """
        request_data: Dict[str, Any] = {}
        if target_image:
            request_data["target_image"] = target_image
        if source_image:
            request_data["source_image"] = source_image

        return request_data

    def _prepare_response_body(self, response: Response) -> Dict:
        """
        Prepare the response body received from the user microservice.

        Args:
            response (Response): The HTTP response object from the user microservice.

        Returns:
            dict: The response body as a dictionary.
        """
        result = response.json()
        return result
