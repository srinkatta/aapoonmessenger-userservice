import re
import time
from datetime import datetime, timezone
from email import charset

import distance
import requests
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from rest_framework import serializers

from user.helpers.aadhar import AadharValidate

MESSAGES = {
    "FIRST_ATTEMPTS_FAILURE": """We have some technical issues with the quality of the image. Let's try again.""",
    "SECOND_ATTEMPTS_FAILURE": """Sorry, automatic verification is not possible with the information provided. Our
    verification team will respond within 12 hrs. Thanks for your patience. """,
}


def failure_attempt_check(self, verification, user):
    user_kyc_setting = user.settings.filter().first()
    logs = user.logs.get().kyc_logs
    attempts = re.findall(r"<b>Target Image: https://", logs) if logs else ""

    verification["attempts"] = 2 - (len(attempts) + 1)
    if verification["attempts"] == 0 and len(attempts) == 1:
        user_kyc_setting.status = 6
        user_kyc_setting.manual_verify = True
        user_kyc_setting.save()

        verification["error"] = (
            "Sorry, automatic verification is not possible with the information provided. Our verification "
            "team will respond within 12 hrs. Thanks for your patience. "
        )
        verification["code"] = 3
        verification["manual_verify"] = True
        subject = "KYC Failure Max Attempts Reached"
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = ["santosh@aapoon.com"]
        context = {
            "name": user.name,
            "email": user.phone_number,
            "module": "Social Proof",
        }
        text_content = render_to_string("config/email/kyc_failed_user.html", context)
        charset.add_charset("utf-8", charset.SHORTEST, None, "utf-8")
        send_mail(subject, text_content, from_email, to_email)
    return verification


def distance_finder(user, matches, string, log_message, field_name=None):
    log_message = info_message(user, log_message, "comparision started", field_name)
    match_result = False

    if string and string != "0":
        for match in matches:
            string = string.lower()
            match = match.lower()
            ml = match.replace(" ", "")

            if string not in ml and distance.levenshtein(string, ml) > 3:
                log_message = error_message(
                    user,
                    log_message,
                    ("%s - %s" % (string, match)),
                    "Does not matched given",
                )
                match_result = False

            else:
                log_message = info_message(
                    user,
                    log_message,
                    ("%s - %s" % (string, match)),
                    "Matched with String",
                )
                match_result = True
    add_log_entries(user, log_message)
    return match_result


def find_match(user, matches, string, log_message, field_name=None):
    log_message = info_message(user, log_message, "comparision started", field_name)
    for match in matches:
        if (match in string) or (string in match):
            log_message = info_message(
                user, log_message, ("%s - %s" % (string, match)), "Matched with String"
            )
            return True
        log_message = error_message(
            user, log_message, ("%s - %s" % (string, match)), "Does not matched given"
        )
    return False, log_message


def add_log_entries(user, messages):
    logs = user.logs.get()
    try:
        messages = messages + str(logs.kyc_logs)
        logs.kyc_logs = messages
        logs.save()
    except Exception:
        logs.kyc_logs = messages
        logs.save()
    return user


def info_message(user, log_message, info, key=None):
    if not key:
        log_message = "%s <br/> <br/><span style='color:#1abc9c'><b>%s</b></span>" % (
            log_message,
            info,
        )
    else:
        log_message = (
            "%s <br/> <br/><span style='color:#1abc9c'><b>%s: %s</b></span>"
            % (log_message, key, info)
        )
    return log_message


def error_message(user, log_message, error, key=None):
    if not key:
        log_message = "%s <br/> <br/><span style='color:#c0392b'><b>%s</b></span>" % (
            log_message,
            error,
        )
    else:
        log_message = (
            "%s <br/> <br/><span style='color:#c0392b'><b>%s: %s</b></span>"
            % (log_message, key, error)
        )
    return log_message


class BaseKYCSerializer(serializers.Serializer):
    def __init__(self, *args, **kwargs):
        self.aws_access_key = settings.S3_AWS_ACCESS_KEY_ID
        self.aws_secret_key = settings.S3_AWS_SECRET_ACCESS_KEY
        self.threshold = 0
        self.region = "us-east-1"
        self.subscription_key = "a3d28bc8888240c78570d1ca378da9bf"
        self.computer_vision_subscription_key = "aefb44866678438992b4e205965f4c4d"
        self.face_api_url = (
            "https://westcentralus.api.cognitive.microsoft.com/face/v1.0/detect"
        )
        self.face_verify_api_url = (
            "https://westcentralus.api.cognitive.microsoft.com/face/v1.0/verify"
        )
        self.vision_base_url = (
            "https://westcentralus.api.cognitive.microsoft.com/vision/v2.0/"
        )
        self.text_recognition_url = self.vision_base_url + "recognizeText"
        self.headers = {"Ocp-Apim-Subscription-Key": self.subscription_key}
        self.vision_headers = {
            "Ocp-Apim-Subscription-Key": self.computer_vision_subscription_key
        }
        super(BaseKYCSerializer, self).__init__(*args, **kwargs)

    def get_logs(self, user):
        log_message = "<br/><br/>"
        log_message = info_message(user, log_message, datetime.now(timezone.utc))
        if self.data.get("source_key"):
            log_message = info_message(
                user, log_message, self.data["source_key"], "Source Image"
            )
        if self.data.get("target_key"):
            log_message = info_message(
                user, log_message, self.data["target_key"], "Target Image"
            )
        if self.data.get("source_key_back_side"):
            log_message = info_message(
                user,
                log_message,
                self.data["source_key_back_side"],
                "Source Back Image",
            )

        return log_message

    def gif_validation(self, key, user, log_message, verification):
        if str(self.data[key]).split(".")[-1] == "gif":
            verification[
                "exception"
            ] = "Supported Image formats are JPEG, PNG, or BMP format."
            verification["is_verified"] = False
            verification["face_id_detected"] = False
            log_message = error_message(
                user, log_message, "Unsupported Image formats for Photo id Uploaded"
            )
            add_log_entries(user, log_message)
        return verification

    def source_key_ocr(self, user, log_message):
        text_response, recognitionResult = self.text_recognition(
            user, self.data["source_key"], log_message
        )
        return text_response, recognitionResult

    def source_key_face_identification(self, user, log_message):
        target_face_id, target_faceid_response = self.face_identification(
            "Source Image", self.data["source_key"], user, log_message
        )
        return target_face_id, target_faceid_response

    def invalid_image_error_check(self, user, log_message, text_response, verification):
        if text_response["error"]["code"] == "InvalidImageDimension":
            verification["exception"] = text_response["error"]["message"].replace(
                "4200 x 4200", "4200 x 4200 pixels"
            )
            log_message = error_message(
                user,
                log_message,
                "verification is stopping here as image is not in context with Azure API",
            )
            verification["is_verified"] = False
            verification["face_id_detected"] = False
            add_log_entries(user, log_message)
        return verification

    def unsupported_image_error_check(
        self, user, log_message, source_faceid_response, verification
    ):
        if (
            source_faceid_response["error"]["code"] == "UnsupportedImageFormat"
            or source_faceid_response["error"]["code"] == "InvalidImage"
        ):
            verification[
                "exception"
            ] = "Supported Image formats are JPEG, PNG, or BMP format."
        elif source_faceid_response["error"]["code"] == "InvalidImageSize":
            verification["exception"] = "Uploaded image should be less than 4 MB"
        else:
            verification["exception"] = source_faceid_response["error"]["message"]
        log_message = error_message(
            user,
            log_message,
            "verification is stopping here as image is not in context with Azure API",
        )
        verification["is_verified"] = False
        verification["face_id_detected"] = False
        add_log_entries(user, log_message)
        return verification

    def faceId_validation(self, user, log_message, verification):
        verification["face_id_detected"] = False
        verification["exception"] = "Please upload the side of the ID with photo"
        log_message = error_message(
            user, log_message, "Text reading is successful from Azure"
        )
        log_message = error_message(
            user, log_message, "Text is detected for photo id uploaded"
        )
        log_message = error_message(
            user,
            log_message,
            "face id is not detected for source image. Hence verification stopped",
        )
        add_log_entries(user, log_message)
        return verification

    def ocr_recognition_validation(self, user, log_message, verification, exception):
        log_message = error_message(
            user,
            log_message,
            "Azure has not returned any data from the uploaded image. Uploaded ID might "
            "be not valid",
        )
        verification["valid_id_proof"] = False
        verification["exception"] = exception
        add_log_entries(user, log_message)
        return verification

    def invalid_image_validation(self, user, log_message, text_response, verification):
        if text_response.json()["error"]["code"] == "InvalidImageDimension":
            verification["exception"] = text_response.json()["error"][
                "message"
            ].replace("4200 x 4200", "4200 x 4200 pixels")
        if text_response.json()["error"]["code"] == "UnsupportedImageFormat":
            verification[
                "exception"
            ] = "Supported Image formats are JPEG, PNG, or BMP format."
        if (
            text_response.json["error"]["code"] != "InvalidImageSize"
            and text_response.json["error"]["code"] != "InvalidImageDimension"
            and text_response.json["error"]["code"] != "UnsupportedImageFormat"
        ):
            verification["exception"] = text_response.json()["error"]["message"]
        log_message = error_message(
            user,
            log_message,
            (
                "Text reading is not successful got error from Azure %s"
                % text_response.json()
            ),
        )
        log_message = error_message(
            user,
            log_message,
            "verification is stopping here as text is not extracted from image or some "
            "error from Azure API",
        )
        add_log_entries(user, log_message)
        return verification

    def empty_face(self, user, log_message, verification):
        verification["exception"] = "Please upload the clear photo ID"
        verification["is_verified"] = False
        verification["face_id_detected"] = False
        log_message = error_message(
            user, log_message, "No image and text detected for Photo Id uploaded"
        )
        add_log_entries(user, log_message)
        return verification

    def id_text_match(self, user, log_message, verification):
        user_kyc_setting = user.settings.get()
        verification["is_verified"] = False
        verification["face_id_detected"] = False
        verification["id_number_matched"] = True
        user_kyc_setting.attachment = self.data["source_key"]
        user_kyc_setting.save()
        log_message = error_message(
            user,
            log_message,
            "image and text detected for Photo Id uploaded and ID is matched",
        )
        add_log_entries(user, log_message)
        return verification

    def id_text_not_match(self, user, log_message, verification, matches):
        user_kyc_setting = user.settings.get()
        verification["is_verified"] = False
        verification["face_id_detected"] = False
        verification["id_number_matched"] = False
        user_kyc_setting.id_match_attempts = user_kyc_setting.id_match_attempts + 1
        user_kyc_setting.save()
        if user_kyc_setting.id_match_attempts == 1:
            verification[
                "exception"
            ] = "Looks like the quality of the picture is low. Please try again."
        if user_kyc_setting.id_match_attempts >= 2:
            verification["code"] = 3
            verification["attempts"] = 0
            # Max_attempts Email
            self.max_attempts_notification(user, verification, matches)
        log_message = error_message(
            user,
            log_message,
            "image and text detected for Photo Id uploaded but ID is not matched",
        )
        add_log_entries(user, log_message)
        return verification

    def max_attempts_notification(self, user, verification, matches):
        user_kyc_setting = user.settings.get()
        verification["code"] = 3
        verification["back"] = True
        user_kyc_setting.attachment = self.data["source_key"]
        user_kyc_setting.save()
        subject = "ID Number Match Max Attempts Reached"
        from_email = settings.DEFAULT_FROM_EMAIL
        toemail = ["santosh@aapoon.com"]
        context = {
            "name": user.name,
            "email": user.phone_number,
            "module": "ID Number Match",
            "id_number": user_kyc_setting.photo_id,
            "text_extracted": matches,
        }
        text_content = render_to_string("config/email/id_failed_user.html", context)
        charset.add_charset("utf-8", charset.SHORTEST, None, "utf-8")
        send_mail(subject, text_content, from_email, toemail)

    def target_image_validation(
        self,
        user,
        log_message,
        verification,
        target_face_id,
        target_faceid_response,
        source_faceid_response,
    ):
        if not isinstance(target_face_id, dict):
            verification["target_image_detected"] = False
            if "picture" not in self.instance:
                verification["exception"] = (
                    "aapoon is unable to verify your selfie due to poor lighting or "
                    "resolution. Please try again."
                )
            else:
                verification["exception"] = (
                    "aapoon is unable to verify your selfie due to poor lighting or "
                    "resolution. Please try again."
                )
            log_message = error_message(
                user,
                log_message,
                "face id is not detected for target image. Hence verification stopped",
            )
        elif target_faceid_response["error"]["message"] == "Image size is too big.":
            verification["exception"] = "Uploaded file should be less than 4 MB."
        elif target_faceid_response["error"]["code"] == "InvalidImageDimension":
            verification["exception"] = target_faceid_response["error"][
                "message"
            ].replace("4200 x 4200", "4200 x 4200 pixels")
        elif (
            target_faceid_response["error"]["code"] == "UnsupportedImageFormat"
            or source_faceid_response["error"]["code"] == "InvalidImage"
        ):
            verification[
                "exception"
            ] = "Supported Image formats are JPEG, PNG, JPG, or BMP format."
        else:
            verification["exception"] = target_faceid_response["error"]["message"]
        if "query" not in self.instance:
            verification = failure_attempt_check(self, verification, user)
        log_message = error_message(user, log_message, verification)
        add_log_entries(user, log_message)
        return verification

    def multiple_face_detected(self, user, log_message, verification):
        log_message = error_message(
            user,
            log_message,
            "looks like you have uploaded a group photo. Hence verification stopped",
        )
        if "query" not in self.instance:
            verification = failure_attempt_check(self, verification, user)
        add_log_entries(user, log_message)
        verification["is_verified"] = False
        verification["pictures_match"] = True
        verification["exception"] = (
            "Oops! It looks like you have uploaded a group photo.Please take a selfie to "
            "resolve the issue. "
        )
        return verification

    def check_image_dimensions(self, user, log_message, verification, text_response):
        verification["exception"] = text_response["error"]["message"].replace(
            "4200 x 4200", "4200 x 4200 pixels"
        )
        log_message = error_message(
            user,
            log_message,
            "verification is stopping here as image is not in context with Azure "
            "API",
        )
        verification["is_verified"] = False
        verification["face_id_detected"] = False
        add_log_entries(user, log_message)
        return verification

    def facial_compare_failed(self, user, log_message, verification, logs):
        user_kyc_setting = user.settings.get()
        verification["pictures_match"] = False
        if logs:
            attempts = re.findall(r"<b>Target Image: https://", logs)
            if attempts:
                verification["exception"] = MESSAGES["FIRST_ATTEMPTS_FAILURE"]
            elif len(attempts) == 1:
                verification["exception"] = MESSAGES["SECOND_ATTEMPTS_FAILURE"]
                verification["code"] = 3
                verification["manual_verify"] = True
                user_kyc_setting.manual_verify = True
                user_kyc_setting.save()
            else:
                verification["exception"] = MESSAGES["SECOND_ATTEMPTS_FAILURE"]
                verification["code"] = 3
                verification["manual_verify"] = True
                user_kyc_setting.manual_verify = True
                user_kyc_setting.save()
        verification = failure_attempt_check(self, verification, user)
        log_message = error_message(
            user, log_message, "KYC verification has stopped as faces are not matched."
        )
        add_log_entries(user, log_message)
        return verification

    def facial_compare_success(self, user, log_message, verification):
        user_kyc_setting = user.settings.get()
        verification["is_verified"] = True
        if "query" not in self.instance:
            log_message = info_message(user, log_message, "Verification is successFull")
            verification["message"] = "You have been Verified Successfully."
        if "query" not in self.instance:
            verification["code"] = 3
            verification["manual_verify"] = True
            user_kyc_setting.manual_verify = True
            user_kyc_setting.save()
            log_message = info_message(
                user, log_message, "Facial Comparison is successFull"
            )
        verification["pictures_match"] = True
        add_log_entries(user, log_message)
        return verification

    def target_key_ocr(self, user, log_message):
        text_response, recognitionResult = self.text_recognition(
            user, self.data["target_key"], log_message
        )
        return text_response, recognitionResult

    def target_key_face_identification(self, user, log_message):
        target_face_id, target_faceid_response = self.face_identification(
            "Target Image", self.data["target_key"], user, log_message
        )
        return target_face_id, target_faceid_response

    def face_identification(self, image_type, key, user, log_message):
        params = {
            "returnFaceId": "true",
            # 'recognitionModel': 'recognition_02',
            "detectionModel": "detection_03",
        }
        log_message = info_message(user, log_message, "verifying %s image" % image_type)
        data = {"url": key}
        face_response = requests.post(
            self.face_api_url, params=params, headers=self.headers, json=data
        )
        faceid_response = face_response.json()
        faceId = None

        if faceid_response:
            if "error" in faceid_response:
                log_message = error_message(
                    user, log_message, "face id is not detected for %s" % image_type
                )
            else:
                log_message = info_message(
                    user, log_message, "face id detected for %s" % image_type
                )
                faceId = faceid_response[0]["faceId"]
        else:
            log_message = error_message(
                user, log_message, "face id is not detected for %s" % image_type
            )
        return faceId, faceid_response

    def text_recognition(self, user, key, log_message):
        text_params = {"mode": "Handwritten"}
        text_data = {"url": key}
        recognitionResult = None
        response = requests.post(
            self.text_recognition_url,
            headers=self.vision_headers,
            params=text_params,
            json=text_data,
        )
        if response.status_code < 250 and response.ok:
            analysis = {}
            while "recognitionResult" not in analysis:
                response_final = requests.get(
                    response.headers["Operation-Location"], headers=self.vision_headers
                )
                analysis = response_final.json()
                time.sleep(1)
                if analysis["status"] == "Succeeded":
                    recognitionResult = analysis["recognitionResult"]["lines"]
        text_response = response.json() if response.status_code > 250 else None
        return text_response, recognitionResult

    def aadharverify(self, user, log_message):
        number = {}
        result = False
        text_response, recognitionResult = self.text_recognition(
            user, self.data["source_key"], log_message
        )
        if recognitionResult:
            text = [i["text"] for i in recognitionResult]
            # full aadhar
            aadhar_full = [
                text[i + 1]
                for i, elem in enumerate(text)
                if "Your Aadhaar No. :" in elem
            ]
            aadhar_full = str("".join(aadhar_full).replace(" ", ""))
            number["aadhar_number"] = aadhar_full
            # half aadhar
            if not aadhar_full:
                for i in text:
                    if len(i) == 14 and i.isnumeric:
                        aadhar = i
                        aadhar = str("".join(aadhar).replace(" ", ""))
                        number["aadhar_number"] = aadhar
                vid = [elem for i, elem in enumerate(text) if "VID" in elem]
                if vid:
                    aadhar = text[-2]
                    aadhar = str("".join(aadhar).replace(" ", ""))
                    number["aadhar_number"] = aadhar
                if not vid:
                    aadhar = text[-1]
                    aadhar = str("".join(aadhar).replace(" ", ""))
                    number["aadhar_number"] = aadhar

            aadhar_number = number["aadhar_number"]

            if len(aadhar_number) == 12 and aadhar_number.isdigit():
                result = AadharValidate(aadhar_number)
        return result

    def face_compare(self, source_faceid, target_faceid, user, log_message):
        request_body = {"faceId1": source_faceid, "faceId2": target_faceid}
        status = False
        log_message = info_message(
            user, log_message, "source face id and target face id is detected"
        )
        log_message = info_message(user, log_message, "face comparision started")
        face_verify = requests.post(
            self.face_verify_api_url, headers=self.headers, json=request_body
        )
        face_verify_resp = face_verify.json()
        log_message = info_message(
            user, log_message, face_verify_resp["isIdentical"], "Faces are Identical"
        )
        log_message = info_message(
            user, log_message, face_verify_resp["confidence"], "Face confidence"
        )

        if face_verify_resp["isIdentical"] or not face_verify_resp["isIdentical"]:
            log_message = error_message(
                user,
                log_message,
                face_verify_resp["isIdentical"],
                "Faces Identical Response",
            )
            if face_verify_resp["confidence"] * 100 >= 40:
                log_message = info_message(
                    user,
                    log_message,
                    "Face verification success as confidence is more then 40%",
                )
                status = True
            else:
                log_message = error_message(
                    user,
                    log_message,
                    "Face verification is not done as confidence is less then 40%. Hence "
                    "Verification stopped ",
                )

        return {
            "confidence": face_verify_resp["confidence"],
            "status": status,
            "log_message": log_message,
        }


class SelfieSerializer(BaseKYCSerializer):
    url = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def selfie(self, user):
        user_kyc_setting = user.settings.filter().first()
        verification = {
            "id_number_matched": user_kyc_setting.id_matched,
            "is_verified": False,
        }
        log_message = self.get_logs(user)
        log_message = info_message(user, log_message, self.data["url"], "Selfie Image")
        verification["is_verified"] = True
        verification["selfie"] = True
        log_message = info_message(user, log_message, "Selfie is successFull")
        add_log_entries(user, log_message)
        return verification


class PhotoIDSerializer(BaseKYCSerializer):
    source_key = serializers.CharField(required=True)

    def photo_id_verification(self, user):
        user_kyc_setting = user.settings.filter().first()
        verification = {
            "id_number_matched": user_kyc_setting.id_matched,
            "is_verified": False,
        }
        log_message = self.get_logs(user)

        verification = self.gif_validation(
            "source_key", user, log_message, verification
        )

        source_face_id, source_faceid_response = self.source_key_face_identification(
            user, log_message
        )

        text_response, recognitionResult = self.source_key_ocr(user, log_message)

        source_recognitionResult = recognitionResult

        verification = self.check_photo_id_validation(
            user,
            log_message,
            text_response,
            user_kyc_setting,
            verification,
            source_face_id,
            source_faceid_response,
            recognitionResult,
        )
        verification = self.check_aadhar_verification(
            user,
            log_message,
            text_response,
            user_kyc_setting,
            verification,
            source_face_id,
            source_faceid_response,
            source_recognitionResult,
        )

        return verification

    def check_photo_id_validation(
        self,
        user,
        log_message,
        text_response,
        user_kyc_setting,
        verification,
        source_face_id,
        source_faceid_response,
        recognitionResult,
    ):
        if isinstance(text_response, dict):
            verification = self.invalid_image_error_check(
                user, log_message, text_response, verification
            )
            return verification
        if isinstance(source_faceid_response, dict):
            verification = self.unsupported_image_error_check(
                user, log_message, source_faceid_response, verification
            )
            return verification
        if not source_face_id and recognitionResult:
            verification = self.faceId_validation(user, log_message, verification)
        if source_face_id and not recognitionResult:
            exception = "Please upload the side of the ID with photo"
            verification = self.ocr_recognition_validation(
                user, log_message, verification, exception
            )
            return verification
        elif source_face_id and len(recognitionResult) < 3:
            exception = "Please upload the side of the ID with photo"
            verification = self.ocr_recognition_validation(
                user, log_message, verification, exception
            )
            return verification
        return verification

    def check_aadhar_verification(
        self,
        user,
        log_message,
        text_response,
        user_kyc_setting,
        verification,
        source_face_id,
        source_faceid_response,
        source_recognitionResult,
    ):
        verify_aadhar = self.aadharverify(user, log_message)
        if source_recognitionResult and source_faceid_response:
            # aadhar not valid
            if user.country_code == "91" and not verify_aadhar:
                verification["exception"] = "Uploaded Aadhar is not Valid"
                verification["is_verified"] = False
                verification["face_id_detected"] = False
                verification["id_number_matched"] = False
                log_message = error_message(
                    user,
                    log_message,
                    "image and text detected for Photo Id uploaded but ID is not Aadhar",
                )
                add_log_entries(user, log_message)
                matches = [rec["text"] for rec in source_recognitionResult]
                text_match = distance_finder(
                    user, matches, user_kyc_setting.photo_id, log_message
                )
                if not text_match:
                    verification = self.id_text_not_match(
                        user, log_message, verification, matches
                    )
                return verification

            verification["is_verified"] = False
            verification["face_id_detected"] = False
            verification["id_number_matched"] = True
            user_kyc_setting.attachment = self.data["source_key"]
            user_kyc_setting.id_matched = True
            log_message = info_message(
                user,
                log_message,
                "image and text detected for Photo Id uploaded ID is Aadhar",
            )
            add_log_entries(user, log_message)
            user_kyc_setting.save()
            return verification
        self.check_text_response_match(
            user,
            log_message,
            text_response,
            verification,
            source_face_id,
            source_recognitionResult,
            user_kyc_setting,
        )

        return verification

    def check_text_response_match(
        self,
        user,
        log_message,
        text_response,
        verification,
        source_face_id,
        source_recognitionResult,
        user_kyc_setting,
    ):
        if text_response:
            verification = self.invalid_image_validation(
                user, log_message, text_response, verification
            )
            return verification

        if not source_face_id and not text_response:
            verification = self.empty_face(user, log_message, verification)
            return verification

        matches = [rec["text"] for rec in source_recognitionResult]
        text_match = distance_finder(
            user, matches, user_kyc_setting.photo_id, log_message
        )
        if text_match:
            verification = self.id_text_match(user, log_message, verification)

        if not text_match:
            verification = self.id_text_not_match(
                user, log_message, verification, matches
            )
        return verification


class ProfileSerializer(BaseKYCSerializer):
    target_key = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )

    def profile(self, user):
        user_kyc_setting = user.settings.filter().first()
        verification = {
            "id_number_matched": user_kyc_setting.id_matched,
            "is_verified": False,
        }
        log_message = self.get_logs(user)

        log_message = info_message(
            user, log_message, self.data["target_key"], "Profile Image"
        )

        verification["is_verified"] = True
        verification["message"] = "Profile Picture Updated Successfully."
        log_message = info_message(user, log_message, "Profile is successFull")
        add_log_entries(user, log_message)
        return verification


class CompareFacesV2Serializer(BaseKYCSerializer):
    source_key = serializers.CharField(required=True)
    target_key = serializers.CharField(required=True)
    source_key_back_side = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )

    def compare_faces(self, user):
        user_kyc_setting = user.settings.filter().first()
        verification = {
            "id_number_matched": user_kyc_setting.id_matched,
            "is_verified": False,
        }
        log_message = self.get_logs(user)
        verification = self.gif_validation(
            "source_key", user, log_message, verification
        )
        source_face_id, source_faceid_response = self.source_key_face_identification(
            user, log_message
        )
        text_response, recognitionResult = self.source_key_ocr(user, log_message)

        self.compare_verification_step_1(
            user,
            log_message,
            verification,
            text_response,
            source_face_id,
            source_faceid_response,
            recognitionResult,
        )

        self.compare_verification_step_2(
            user,
            log_message,
            verification,
            source_face_id,
            source_faceid_response,
            text_response,
        )
        return verification

    def compare_verification_step_1(
        self,
        user,
        log_message,
        verification,
        text_response,
        source_face_id,
        source_faceid_response,
        recognitionResult,
    ):
        if isinstance(text_response, dict):
            verification = self.invalid_image_error_check(
                user, log_message, text_response, verification
            )
            return verification
        if isinstance(source_faceid_response, dict):
            verification = self.unsupported_image_error_check(
                user, log_message, source_faceid_response, verification
            )
            return verification

        if not source_face_id and recognitionResult:
            verification = self.faceId_validation(user, log_message, verification)

        if source_face_id and not recognitionResult:
            exception = "Please upload the side of the ID with photo"
            verification = self.ocr_recognition_validation(
                user, log_message, verification, exception
            )
            return verification
        elif source_face_id and len(recognitionResult) < 3:
            exception = "Please upload the side of the ID with photo"
            verification = self.ocr_recognition_validation(
                user, log_message, verification, exception
            )
            return verification

        if text_response:
            verification = self.invalid_image_validation(
                user, log_message, text_response, verification
            )
            return verification

        if not source_face_id and not text_response:
            verification = self.empty_face(user, log_message, verification)
            return verification

    def compare_verification_step_2(
        self,
        user,
        log_message,
        verification,
        source_face_id,
        source_faceid_response,
        text_response,
    ):
        logs = user.logs.get().kyc_logs
        target_face_id = None
        target_faceid_response = None

        if self.data["target_key"] != "":

            verification = self.gif_validation(
                "target_key", user, log_message, verification
            )
            (
                target_face_id,
                target_faceid_response,
            ) = self.target_key_face_identification(user, log_message)
            text_response, recognitionResult = self.target_key_ocr(user, log_message)

            if not target_face_id:
                verification["is_verified"] = False
                verification = self.target_image_validation(
                    user,
                    log_message,
                    verification,
                    target_face_id,
                    target_faceid_response,
                    source_faceid_response,
                )

        if (target_face_id and target_faceid_response) and (
            source_face_id,
            source_faceid_response,
        ):
            if len(target_faceid_response) > 1:
                verification = self.multiple_face_detected(
                    user, log_message, verification
                )
                return verification

            if isinstance(text_response, dict):
                if text_response["error"]["code"] == "InvalidImageDimension":
                    verification = self.check_image_dimensions(
                        user, log_message, verification, text_response
                    )
                    return verification

            face_comparision = self.face_compare(
                source_face_id, target_face_id, user, log_message
            )
            verification["confidence"] = face_comparision["confidence"]
            log_message = face_comparision["log_message"]
            if face_comparision["status"]:
                verification = self.facial_compare_success(
                    user, log_message, verification
                )
            else:
                verification = self.facial_compare_failed(
                    user, log_message, verification, logs
                )
        return verification
