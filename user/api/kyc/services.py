import re
from email import charset
from typing import Dict, Any, List

import distance
from django.core.mail import send_mail
from django.template.loader import render_to_string

from user.helpers.aadhar import AadharValidate
from user.models import User
from user.services import KYC
from datetime import datetime, timezone

from user_service import settings


MESSAGES = {
    "FIRST_ATTEMPTS_FAILURE": """We have some technical issues with the quality of the image. Let's try again.""",
    "SECOND_ATTEMPTS_FAILURE": """Sorry, automatic verification is not possible with the information provided. Our
    verification team will respond within 12 hrs. Thanks for your patience. """,
}


def validate_selfie(user: User, selfie_url: str):
    user_kyc_setting = user.settings.filter().first()
    verification = {
        "id_number_matched": user_kyc_setting.id_matched,
        "is_verified": False,
    }
    log_message = __get_logs()
    log_message = __info_message(log_message, selfie_url, "Selfie Image")
    verification["is_verified"] = True
    verification["selfie"] = True
    log_message = __info_message(log_message, "Selfie is added successfully")
    __add_log_entries(user, log_message)  # type: ignore
    return verification


def update_profile_picture(user: User, profile_pic_url: str):
    user_kyc_setting = user.settings.filter().first()
    verification = {
        "id_number_matched": user_kyc_setting.id_matched,
        "is_verified": False,
    }
    log_message = __get_logs()

    log_message = __info_message(log_message, profile_pic_url, "Profile Image")

    verification["is_verified"] = True
    verification["message"] = "Profile Picture Updated Successfully."
    log_message = __info_message(log_message, "Profile is successFull")
    __add_log_entries(user, log_message)  # type: ignore
    return verification


def validate_and_compare_photo_id(user: User, photo_id_input: str) -> Dict[str, any]:
    user_kyc_setting = user.settings.filter().first()
    verification = {
        "id_number_matched": user_kyc_setting.id_matched,
        "is_verified": False,
    }

    log_message = __get_logs(data={"source_key": photo_id_input})

    verification = __gif_validation(
        photo_id_input,
        user,
        log_message,
        verification,
    )

    face_detect_response = KYC().face_detect(target_image=photo_id_input)
    text_extract_response = KYC().text_extract(source_image=photo_id_input)

    is_face_detected, extracted_ocr_text = __process_face_and_text_response(
        user,
        photo_id_input,
        face_detect_response,
        text_extract_response,
    )

    if not is_face_detected:
        if user_kyc_setting.id_match_attempts == 1:
            verification["face_id_detected"] = False
            verification["exception"] = "Please upload the side of the ID with photo"
            log_message = __error_message(
                log_message, "Text reading is successful from AWS"
            )
            log_message = __error_message(
                log_message, "Text is detected for photo id uploaded"
            )
            log_message = __error_message(
                log_message,
                "face id is not detected for source image. Hence verification stopped",
            )
            __add_log_entries(user, log_message)  # type: ignore
            user_kyc_setting.id_match_attempts = user_kyc_setting.id_match_attempts + 1
            user_kyc_setting.save()
        else:
            verification["face_id_detected"] = False
            verification["id_number_matched"] = False
            verification["code"] = 3
            verification["attempts"] = user_kyc_setting.id_match_attempts
            verification["back"] = False
            verification["is_verified"] = False
            verification["exception"] = "Uploaded Aadhar is not Valid"
            log_message = __error_message(
                log_message, "Text reading is successful from AWS"
            )
            log_message = __error_message(
                log_message, "Text is detected for photo id uploaded"
            )
            log_message = __error_message(
                log_message,
                "face id is not detected for source image. Hence verification stopped",
            )
            __add_log_entries(user, log_message)  # type: ignore
            user_kyc_setting.id_match_attempts = user_kyc_setting.id_match_attempts + 1
            user_kyc_setting.save()
        return verification

    elif (
        is_face_detected
        and not extracted_ocr_text
        or (user.country_code == "91" and not __aadhar_verify(extracted_ocr_text))
    ):
        verification["exception"] = "Uploaded Aadhar is not Valid"
        verification["is_verified"] = False
        verification["face_id_detected"] = False
        verification["id_number_matched"] = False
        log_message = __error_message(
            log_message,
            "image and text detected for Photo Id uploaded but ID is not Aadhar",
        )
        __handle_id_verification_failure(
            user,  # type: ignore
            user_kyc_setting,
            verification,
            log_message,
            extracted_ocr_text,
            photo_id_input,
        )
        return verification
    else:
        verification["is_verified"] = False
        verification["id_number_matched"] = True
        verification["face_id_detected"] = False

    return verification


def __handle_exception_message_on_logs(
    logs,
    verification,
    user_kyc_setting,
    log_message,
):
    attempts = re.findall(r"<b>Target Image: https://", logs) or []
    if not attempts:
        verification["is_verified"] = False
        verification["exception"] = (
            "aapoon is unable to verify your selfie due to poor lighting or "
            "resolution. Please try again."
        )
        log_message = __error_message(
            log_message,
            "face id is not detected for target image. Hence verification stopped",
        )
        user_kyc_setting.id_match_attempts = user_kyc_setting.id_match_attempts + 1
        user_kyc_setting.save()
    else:
        verification["is_verified"] = False
        verification["pictures_match"] = False
        verification["id_number_matched"] = user_kyc_setting.id_matched
        log_message = __error_message(
            log_message,
            "face id is not detected for target image. Hence verification stopped",
        )
        verification["exception"] = MESSAGES["SECOND_ATTEMPTS_FAILURE"]
        verification["error"] = MESSAGES["SECOND_ATTEMPTS_FAILURE"]
        verification["code"] = 3
        verification["manual_verify"] = True
        user_kyc_setting.manual_verify = True
        user_kyc_setting.save()
    return verification, log_message


def compare_faces(user: User, request_data: Dict[str, Any]):
    user_kyc_setting = user.settings.filter().first()
    verification = {
        "id_number_matched": user_kyc_setting.id_matched,
        "is_verified": False,
    }
    log_message = __get_logs(request_data)
    verification = __gif_validation(
        request_data.get("source_key"),
        user,
        log_message,
        verification,
    )
    # Source key validation
    source_face_detect_response = KYC().face_detect(
        target_image=request_data.get("source_key")
    )
    source_text_extract_response = KYC().text_extract(
        source_image=request_data.get("source_key")
    )

    is_source_face_detected, extracted_ocr_text = __process_face_and_text_response(
        user,
        request_data.get("source_key"),
        source_face_detect_response,
        source_text_extract_response,
    )

    if not is_source_face_detected:
        verification["face_id_detected"] = False
        verification["exception"] = "Please upload the side of the ID with photo"
        log_message = __error_message(
            log_message, "Text reading is successful from AWS"
        )
        log_message = __error_message(
            log_message, "Text is detected for photo id uploaded"
        )
        log_message = __error_message(
            log_message,
            "face id is not detected for source image. Hence verification stopped",
        )
        __add_log_entries(user, log_message)  # type: ignore
        return verification

    elif (
        is_source_face_detected
        and not extracted_ocr_text
        or (user.country_code == "91" and not __aadhar_verify(extracted_ocr_text))
    ):
        verification["exception"] = "Uploaded Aadhar is not Valid"
        verification["is_verified"] = False
        verification["face_id_detected"] = False
        verification["id_number_matched"] = False
        log_message = __error_message(
            log_message,
            "image and text detected for Photo Id uploaded but ID is not Aadhar",
        )
        __handle_id_verification_failure(
            user,  # type: ignore
            user_kyc_setting,
            verification,
            log_message,
            extracted_ocr_text,
            request_data.get("source_key"),
        )
        return verification
    else:
        verification["is_verified"] = False
        verification["id_number_matched"] = True
        verification["exception"] = (
            "aapoon is unable to verify your selfie due to poor lighting or "
            "resolution. Please try again."
        )
        log_message = __error_message(
            log_message,
            "face id is not detected for target image. Hence verification stopped",
        )
        __add_log_entries(user, log_message)  # type: ignore
        user_kyc_setting.id_match_attempts = user_kyc_setting.id_match_attempts + 1
        user_kyc_setting.save()

    logs = user.logs.get().kyc_logs

    if request_data.get("target_key"):
        verification = __gif_validation(
            request_data.get("target_key"),
            user,
            log_message,
            verification,
        )

        target_face_detect_response = KYC().face_detect(
            target_image=request_data.get("target_key")
        )
        target_text_extract_response = KYC().text_extract(
            source_image=request_data.get("target_key")
        )

        is_target_face_detected = (
            True if target_face_detect_response.get("FaceDetails") else False
        )

        if not is_target_face_detected:
            verification, log_message = __handle_exception_message_on_logs(
                logs=logs,
                verification=verification,
                user_kyc_setting=user_kyc_setting,
                log_message=log_message,
            )
            log_message = __error_message(user, log_message, verification)
            __add_log_entries(user, log_message)  # type: ignore
            return verification

        elif (is_target_face_detected and target_text_extract_response) and (
            is_source_face_detected,
            source_face_detect_response,
        ):
            if (
                user.country_code == "1"
                and len(source_face_detect_response["FaceDetails"]) > 2
            ) or (
                user.country_code != "1"
                and len(source_face_detect_response["FaceDetails"]) > 1
            ):
                log_message = __error_message(
                    log_message,
                    "looks like you have uploaded a group photo. Hence verification stopped",
                )
                __add_log_entries(user, log_message)  # type: ignore
                verification["is_verified"] = False
                verification["pictures_match"] = True
                verification["exception"] = (
                    "Oops! It looks like you have uploaded a group photo.Please take a selfie to "
                    "resolve the issue. "
                )
                return verification

        log_message = __info_message(
            log_message, "source face and target face is detected"
        )

        face_compare_response = KYC().face_comparison(
            target_image=request_data.get("target_key"),
            source_image=request_data.get("source_key"),
        )
        face_match = face_compare_response.get("FaceMatches")
        face_compare_status: bool = False
        if not face_match:
            log_message = __error_message(
                log_message,
                "Face verification is not done as confidence is less then 40%. Hence "
                "Verification stopped ",
            )
            verification["status"] = False
            verification["confidence"] = face_match[0]["Similarity"]
            __add_log_entries(user, log_message)  # type: ignore
        else:
            if len(face_match) > 2:
                log_message = __error_message(
                    log_message,
                    "Multiple Face detected while comparison. Hence Verification stopped",
                )
                face_compare_status = False
            else:
                log_message = __info_message(
                    user,
                    log_message,
                    "Face verification success as confidence is more then 40%",
                )

                face_compare_status = True
                verification["confidence"] = face_match[0]["Similarity"]

        if face_compare_status:
            verification["message"] = "You have been Verified Successfully."
            verification["is_verified"] = True
            verification["code"] = 3
            verification["manual_verify"] = False
            verification["id_number_matched"] = True
            user_kyc_setting.manual_verify = False
            user_kyc_setting.id_match_attempts = 0
            user_kyc_setting.save()
            log_message = __info_message(
                log_message,
                "Facial Comparison is successFull",
            )
            verification["pictures_match"] = True
            __add_log_entries(user, log_message)  # type: ignore
            return verification
        else:
            verification["pictures_match"] = False
            if logs:
                attempts = re.findall(r"<b>Target Image: https://", logs)
                if not attempts:
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
            else:
                verification = __failure_attempt_check(verification, user)  # type: ignore
                log_message = __error_message(
                    log_message,
                    "KYC verification has stopped as faces are not matched.",
                )
                __add_log_entries(user, log_message)  # type: ignore
                return verification

    return verification


def __add_log_entries(user, messages):
    logs = user.logs.get()
    try:
        messages = messages + str(logs.kyc_logs)
        logs.kyc_logs = messages
        logs.save()
    except Exception:
        logs.kyc_logs = messages
        logs.save()
    return user


def __info_message(log_message, info, key=None):
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


def __error_message(log_message, error, key=None):
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


def __get_logs(data=None):
    log_message = "<br/><br/>"
    log_message = __info_message(log_message, datetime.now(timezone.utc))
    if data and data.get("source_key"):
        log_message = __info_message(log_message, data["source_key"], "Source Image")
    if data and data.get("target_key"):
        log_message = __info_message(log_message, data["target_key"], "Target Image")
    if data and data.get("source_key_back_side"):
        log_message = __info_message(
            log_message,
            data["source_key_back_side"],
            "Source Back Image",
        )

    return log_message


def __gif_validation(url, user, log_message, verification):
    if str(url).split(".")[-1] == "gif":
        verification[
            "exception"
        ] = "Supported Image formats are JPEG, PNG, or BMP format."
        verification["is_verified"] = False
        verification["face_id_detected"] = False
        log_message = __error_message(
            log_message, "Unsupported Image formats for Photo id Uploaded"
        )
        __add_log_entries(user, log_message)
    return verification


def __aadhar_verify(extracted_ocr_text: List[Any]):
    number = {}
    result = False
    # full aadhar
    aadhar_full = [
        extracted_ocr_text[i + 1]
        for i, elem in enumerate(extracted_ocr_text)
        if "Your Aadhaar No. :" in elem
    ]
    aadhar_full = str("".join(aadhar_full).replace(" ", ""))
    number["aadhar_number"] = aadhar_full
    # half aadhar
    if not aadhar_full:
        for i in extracted_ocr_text:
            if len(i) == 14 and i.isnumeric:
                aadhar = i
                aadhar = str("".join(aadhar).replace(" ", ""))
                number["aadhar_number"] = aadhar
        vid = [elem for i, elem in enumerate(extracted_ocr_text) if "VID" in elem]
        if vid and not number["aadhar_number"]:
            aadhar = extracted_ocr_text[-2]
            aadhar = str("".join(aadhar).replace(" ", ""))
            number["aadhar_number"] = aadhar
        if not vid and not number["aadhar_number"]:
            aadhar = extracted_ocr_text[-1]
            aadhar = str("".join(aadhar).replace(" ", ""))
            number["aadhar_number"] = aadhar

    aadhar_number = number["aadhar_number"]

    if len(aadhar_number) == 12 and aadhar_number.isdigit():
        result = AadharValidate(aadhar_number)
    return result


def __distance_finder(user, matches, string, log_message, field_name=None):
    log_message = __info_message(log_message, "comparison started", field_name)
    match_result = False
    if string and string != "0":
        for match in matches:
            string = string.lower()
            match = match.lower()
            ml = match.replace(" ", "")

            if string not in ml and distance.levenshtein(string, ml) > 3:
                log_message = __error_message(
                    log_message,
                    ("%s - %s" % (string, match)),
                    "Does not matched given",
                )
                match_result = False

            else:
                log_message = __info_message(
                    log_message,
                    ("%s - %s" % (string, match)),
                    "Matched with String",
                )
                match_result = True
                break
    __add_log_entries(user, log_message)
    return match_result


def __max_attempts_notification(user, verification, matches, photo_id_input):
    user_kyc_setting = user.settings.get()
    verification["code"] = 3
    verification["back"] = True
    user_kyc_setting.attachment = photo_id_input
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


def __process_face_and_text_response(
    user,
    photo_id_input,
    face_detect_response,
    text_extract_response,
):
    is_face_detected = False
    if face_detect_response.get("FaceDetails"):
        is_face_detected = True

    extracted_ocr_text = []

    if not is_face_detected:
        return is_face_detected, extracted_ocr_text

    if user.country_code == "91":
        extracted_ocr_text = [
            i["Text"]
            for i in text_extract_response["Blocks"]
            if i["BlockType"] == "LINE"
        ]
    else:
        extracted_ocr_text = __extract_ocr_text_from_analyze_id_response(photo_id_input)

    return is_face_detected, extracted_ocr_text


def __extract_ocr_text_from_analyze_id_response(photo_id_input):
    analyze_id_response = KYC().analyze_id(source_image=photo_id_input)
    extracted_ocr_text = []
    for identity_documents in analyze_id_response["IdentityDocuments"]:
        if identity_documents:
            for identity_fields in identity_documents["IdentityDocumentFields"]:
                if identity_fields["Type"]["Text"] == "DOCUMENT_NUMBER":
                    extracted_ocr_text.append(identity_fields["ValueDetection"]["Text"])
    return extracted_ocr_text


def __handle_id_verification_failure(
    user,
    user_kyc_setting,
    verification,
    log_message,
    extracted_ocr_text,
    photo_id_input,
):
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
        __max_attempts_notification(
            user, verification, extracted_ocr_text, photo_id_input
        )
    log_message = __error_message(
        log_message,
        "image and text detected for Photo Id uploaded but ID is not matched",
    )
    __add_log_entries(user, log_message)


def __failure_attempt_check(verification, user):
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
