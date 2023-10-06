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


def info_message(log_message, info, key=None):
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


def error_message(log_message, error, key=None):
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


def get_logs(data=None):
    log_message = "<br/><br/>"
    log_message = info_message(log_message, datetime.now(timezone.utc))
    if data and data.get("source_key"):
        log_message = info_message(log_message, data["source_key"], "Source Image")
    if data and data.get("target_key"):
        log_message = info_message(log_message, data["target_key"], "Target Image")
    if data and data.get("source_key_back_side"):
        log_message = info_message(
            log_message,
            data["source_key_back_side"],
            "Source Back Image",
        )

    return log_message


def gif_validation(url, user, log_message, verification):
    if str(url).split(".")[-1] == "gif":
        verification[
            "exception"
        ] = "Supported Image formats are JPEG, PNG, or BMP format."
        verification["is_verified"] = False
        verification["face_id_detected"] = False
        log_message = error_message(
            log_message, "Unsupported Image formats for Photo id Uploaded"
        )
        add_log_entries(user, log_message)
    return verification


def aadhar_verify(extracted_ocr_text: List[Any]):
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
    print(aadhar_number)

    if len(aadhar_number) == 12 and aadhar_number.isdigit():
        result = AadharValidate(aadhar_number)
    return result


def distance_finder(user, matches, string, log_message, field_name=None):
    log_message = info_message(log_message, "comparison started", field_name)
    match_result = False
    if string and string != "0":
        for match in matches:
            string = string.lower()
            match = match.lower()
            ml = match.replace(" ", "")

            if string not in ml and distance.levenshtein(string, ml) > 3:
                log_message = error_message(
                    log_message,
                    ("%s - %s" % (string, match)),
                    "Does not matched given",
                )
                match_result = False

            else:
                log_message = info_message(
                    log_message,
                    ("%s - %s" % (string, match)),
                    "Matched with String",
                )
                match_result = True
                break
    add_log_entries(user, log_message)
    return match_result


def max_attempts_notification(user, verification, matches, photo_id_input):
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


def validate_and_compare_photo_id(user: User, photo_id_input: str) -> Dict[str, any]:
    user_kyc_setting = user.settings.filter().first()
    verification = {
        "id_number_matched": user_kyc_setting.id_matched,
        "is_verified": False,
    }

    log_message = get_logs(data={"source_key": photo_id_input})

    verification = gif_validation("source_key", user, log_message, verification)

    face_detect_response = KYC().face_detect(target_image=photo_id_input)
    text_extract_response = KYC().text_extract(source_image=photo_id_input)

    is_face_detected, extracted_ocr_text = process_face_and_text_response(
        user,
        photo_id_input,
        face_detect_response,
        text_extract_response,
    )

    if not is_face_detected:
        verification["face_id_detected"] = False
        verification["exception"] = "Please upload the side of the ID with photo"
        log_message = error_message(log_message, "Text reading is successful from AWS")
        log_message = error_message(
            log_message, "Text is detected for photo id uploaded"
        )
        log_message = error_message(
            log_message,
            "face id is not detected for source image. Hence verification stopped",
        )
        add_log_entries(user, log_message)  # type: ignore
        return verification

    if not extracted_ocr_text or (
        user.country_code == "91" and not aadhar_verify(extracted_ocr_text)
    ):
        verification["exception"] = "Uploaded Aadhar is not Valid"
        verification["is_verified"] = False
        verification["face_id_detected"] = False
        verification["id_number_matched"] = False
        log_message = error_message(
            log_message,
            "image and text detected for Photo Id uploaded but ID is not Aadhar",
        )
        handle_id_verification_failure(
            user,  # type: ignore
            user_kyc_setting,
            verification,
            log_message,
            extracted_ocr_text,
            photo_id_input,
        )
        return verification

    text_match = distance_finder(
        user,  # type: ignore
        extracted_ocr_text,
        user_kyc_setting.photo_id,
        log_message,
    )

    if text_match:
        user_kyc_setting = user.settings.get()
        verification["is_verified"] = False
        verification["face_id_detected"] = False
        verification["id_number_matched"] = True
        user_kyc_setting.attachment = photo_id_input
        user_kyc_setting.save()
        log_message = error_message(
            user,
            log_message,
            "image and text detected for Photo Id uploaded and ID is matched",
        )
        add_log_entries(user, log_message)  # type: ignore
    else:
        handle_id_verification_failure(
            user,  # type: ignore
            user_kyc_setting,
            verification,
            log_message,
            extracted_ocr_text,
            photo_id_input,
        )

    return verification


def process_face_and_text_response(
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
        extracted_ocr_text = extract_ocr_text_from_analyze_id_response(photo_id_input)

    return is_face_detected, extracted_ocr_text


def extract_ocr_text_from_analyze_id_response(photo_id_input):
    analyze_id_response = KYC().analyze_id(source_image=photo_id_input)
    extracted_ocr_text = []
    for identity_documents in analyze_id_response["IdentityDocuments"]:
        if identity_documents:
            for identity_fields in identity_documents["IdentityDocumentFields"]:
                if identity_fields["Type"]["Text"] == "DOCUMENT_NUMBER":
                    extracted_ocr_text.append(identity_fields["ValueDetection"]["Text"])
    return extracted_ocr_text


def handle_id_verification_failure(
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
        max_attempts_notification(
            user, verification, extracted_ocr_text, photo_id_input
        )
    log_message = error_message(
        log_message,
        "image and text detected for Photo Id uploaded but ID is not matched",
    )
    add_log_entries(user, log_message)


def validate_selfie(user: User, selfie_url: str):
    user_kyc_setting = user.settings.filter().first()
    verification = {
        "id_number_matched": user_kyc_setting.id_matched,
        "is_verified": False,
    }
    log_message = get_logs()
    log_message = info_message(log_message, selfie_url, "Selfie Image")
    verification["is_verified"] = True
    verification["selfie"] = True
    log_message = info_message(log_message, "Selfie is added successfully")
    add_log_entries(user, log_message)  # type: ignore
    return verification


def update_profile_picture(user: User, profile_pic_url: str):
    user_kyc_setting = user.settings.filter().first()
    verification = {
        "id_number_matched": user_kyc_setting.id_matched,
        "is_verified": False,
    }
    log_message = get_logs()

    log_message = info_message(log_message, profile_pic_url, "Profile Image")

    verification["is_verified"] = True
    verification["message"] = "Profile Picture Updated Successfully."
    log_message = info_message(log_message, "Profile is successFull")
    add_log_entries(user, log_message)
    return verification
