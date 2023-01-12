import csv
import re
import os
import logging
from random import randint
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.http import Http404, HttpResponse
from smtplib import SMTPAuthenticationError

from rest_framework import status, viewsets, permissions
from rest_framework.generics import get_object_or_404, ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from user.api.serializers import (
    UserLoginSerializer,
    RegisterSerializer,
    UserLogSerializer,
    UserFeedbackSerializer,
    UserInviteSerializer,
    UserDeviceSerializer,
    UserProfileSerializer,
    UserProfileInputSerializer,
    UserSerializer,
    SendOTPSerializer,
    VerifyPhoneSerializer,
    DeviceInfoSerializer,
    AppInfoSerializer,
    LanguageSerializer,
    FeedbackSerializer,
    UserRemoveSerializer,
    UserDetailsSerializer,
    UserDetailsInputSerializer,
    NotificationSettingsSerializer,
)
from user.models import (
    UserLog,
    UserFeedback,
    UserInvite,
    UserDevice,
    UserProfile,
    User,
    DeviceInfo,
    AppInfo,
    Languages,
    DeletedUser,
)
from user.utils import (
    make_request,
    phone_failure,
    send_sms_message,
    send_email_notification,
    feedback_mail,
)
from user.helpers import sms, hotp
from user.user_delete import UserDelete
from user_service import settings
from rest_framework_api_key.permissions import HasAPIKey


logger = logging.getLogger(__name__)


class AuthUserRegistrationView(APIView):
    authentication_classes = [JWTAuthentication]
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        user = serializer.save(self.request)
        return user


class AuthUserLoginView(APIView):
    authentication_classes = [JWTAuthentication]
    serializer_class = UserLoginSerializer
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class UserLogsViewSet(viewsets.ModelViewSet):
    """
    Viewset to create, list, update and delete UserLogs.
    """

    serializer_class = UserLogSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return UserLog.objects.filter(user=self.request.user)


class UserFeedbackViewSet(viewsets.ModelViewSet):
    """
    Viewset to create, list, update and delete UserFeedback.
    """

    serializer_class = UserFeedbackSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return UserFeedback.objects.filter(user=self.request.user)


class UserInviteViewSet(viewsets.ModelViewSet):
    """
    Viewset to create, list, update and delete UserInvite.
    """

    serializer_class = UserInviteSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return UserInvite.objects.filter(user=self.request.user)

    def get_object(self):
        return get_object_or_404(UserInvite.objects.all(), user=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def retrieve(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if not str(request.user.id) == pk:
            return Response(
                {"error": "Action not allowed"}, status=status.HTTP_403_FORBIDDEN
            )
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class UserDeviceViewSet(viewsets.ModelViewSet):
    """
    Viewset to create, list, update and delete UserDevice.
    """

    serializer_class = UserDeviceSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return UserDevice.objects.filter(user=self.request.user)

    def get_object(self):
        return UserDevice.objects.filter(user=self.request.user).first()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def retrieve(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if not str(request.user.id) == pk:
            return Response(
                {"error": "Action not allowed"}, status=status.HTTP_403_FORBIDDEN
            )
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class UserProfileViewSet(viewsets.ModelViewSet):
    """
    Viewset to create, list, update and delete UserProfile.
    """

    permission_classes = (permissions.IsAuthenticated,)

    def get_serializer_class(self):
        if self.request.method in ["POST", "PUT"]:
            return UserProfileInputSerializer
        else:
            return UserProfileSerializer

    def get_queryset(self):
        return UserProfile.objects.filter(user=self.request.user)

    def get_object(self):
        return UserProfile.objects.filter(user=self.request.user).first()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def retrieve(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if not str(request.user.id) == pk:
            return Response(
                {"error": "Action not allowed"}, status=status.HTTP_403_FORBIDDEN
            )
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class UserViewSet(viewsets.ModelViewSet):
    """
    Viewset to create, list, update and delete User.
    """

    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)
    http_method_names = ["get", "patch", "head"]

    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)

    def get_object(self):
        return get_object_or_404(User.objects.all(), id=self.request.user.id)


class PushNotificationSettings(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = NotificationSettingsSerializer

    def post(self, request):
        user_id = request.data.get("user_id")
        user = User.objects.get(id=user_id)
        user.fcm_token = request.data.get("fcm_token", "")
        user.apns_token = request.data.get("apns_token", "")
        user.save()

        return Response({"Data": "Push Notification Settings Updated."}, status=200)


class SendOTPView(APIView):
    """
    API View to send otp to user phone number by using POST and GET Method.
    """

    permission_classes = (permissions.IsAuthenticated,)
    allowed_methods = ("POST", "GET")

    def get_serializer(self, *args, **kwargs):
        return SendOTPSerializer(*args, **kwargs)

    def send_sms_message(self, request, phone_number, otp, user, number):
        if user.country_code == "91":
            fast_sms = sms.FAST_SMS(phone_number, otp, user)
            fast_sms.send_message()
        else:
            sms_client = sms.SMS(number, otp, user)
            sms_client.send_message()

    def get(self, request, *args, **kwargs):

        user = request.user
        if user.phone_attempts >= 3:
            phone_failure(self, request)
            return Response(
                {
                    "detail": "You have reached Max Phone Attempts for Phone Verification"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        rand_int = randint(0, 100)
        if user.updated_phone_number:
            phone = str(user.updated_country_code) + str(user.updated_phone_number)
            updated_ph = user.updated_phone_number
            otp = hotp.HOTP(phone, rand_int)
            self.send_sms_message(request, updated_ph, otp, user, phone)
            user.otp_requested = otp
        else:
            otp = hotp.HOTP(str(user.country_code) + str(user.phone_number), rand_int)
            ph_number = user.phone_number
            number = str(user.country_code) + str(user.phone_number)
            self.send_sms_message(request, ph_number, otp, user, number)
            user.otp_requested = otp

        print(f"Generated Otp: {otp}")
        user.phone_attempts = user.phone_attempts + 1
        user.save()
        return Response(
            {"message": "Verification Code (OTP) sent"}, status=status.HTTP_200_OK
        )

    def post(self, request, *args, **kwargs):
        user = request.user
        phone_number = request.data["phone_number"]
        phone_number = phone_number.replace("-", r"")
        phone_number = phone_number.replace("(", r"")
        phone_number = phone_number.replace(")", r"")
        number = request.data["country_code"] + phone_number
        phone = User.objects.filter(
            phone_number=phone_number, country_code=request.data["country_code"]
        )

        if len(phone) >= 1 and not user.phone_number == phone_number:
            print("hello")
            return Response(
                {"detail": "Mobile number already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if user.login_attempts >= 3:
            phone_failure(self, request)

            return Response(
                {
                    "detail": "You have reached Max Phone Attempts for Phone Verification"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if phone_number.isdigit():
            user.updated_phone_number = phone_number
            user.updated_country_code = request.data["country_code"]
            rand_int = randint(0, 100)

            if "country_iso_code" in request.data:
                user.country_iso_code = request.data["country_iso_code"]

            if user.updated_phone_number:
                otp = hotp.HOTP(str(number), rand_int)
                updated_ph = user.updated_phone_number
                self.send_sms_message(request, updated_ph, otp, user, number)
                user.otp_requested = otp
            else:
                otp = hotp.HOTP(
                    str(user.country_code) + str(user.phone_number), rand_int
                )
                phone_number = user.phone_number
                self.send_sms_message(request, phone_number, otp, user, number)
                user.otp_requested = otp
            print(f"Generated Otp: {otp}")
            user.login_attempts = user.login_attempts + 1
            user.save()
            return Response(
                {"message": "Verification Code (OTP) sent"}, status=status.HTTP_200_OK
            )
        else:
            error = "Special characters not allowed"
            error_response = {"error": error}
            return Response(error_response, status=status.HTTP_400_BAD_REQUEST)


class VerifyPhoneView(APIView):
    """
    API View to verify otp sent to user phone number by POST request.
    """

    permission_classes = (permissions.IsAuthenticated,)
    allowed_methods = ("POST",)

    def get_serializer(self, *args, **kwargs):
        return VerifyPhoneSerializer(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.phone_number_verified = True
        user_ph = request.user.phone_verification.get()
        user_ph.verify_attempts = 0
        user_ph.wrong_attempts = 0
        user.save()
        user_ph.save()

        # Make call to websocket

        phone_number = "{}{}".format(
            user.updated_country_code, user.updated_phone_number
        )
        url = "{}{}".format(settings.XMPP_SERVER_URL, "api/register/")
        data = {
            "user": phone_number,
            "host": settings.XMPP_HOST,
            "password": "{}@{}".format(phone_number, settings.XMPP_HOST),
        }
        try:
            make_request(url, "POST", data=data)
            logger.info("User successfully registered at websocket server")
        except Exception as e:
            logger.debug("Error registering user at websocket server %s" % e)
        return Response(
            {"detail": "Phone Number successfully verified"}, status=status.HTTP_200_OK
        )


class DeviceInfoView(APIView):
    """
    API View to maintain App versioning
    """

    permission_classes = (AllowAny,)
    serializer_class = DeviceInfoSerializer
    queryset = DeviceInfo.objects.all()
    http_method_names = ["get", "post"]

    def get_serializer(self, *args, **kwargs):
        return DeviceInfoSerializer(*args, **kwargs)

    @method_decorator(cache_page(60))
    def get(self, request):
        queryset = AppInfo.objects.all()
        serializer = AppInfoSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            if serializer.validated_data["user"] is not None:
                serializer.save()
                queryset = AppInfo.objects.all()
                serializer = AppInfoSerializer(queryset, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            queryset = AppInfo.objects.all()
            serializer = AppInfoSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LanguageView(ListAPIView):
    """
    API View to list all available languages
    """

    serializer_class = LanguageSerializer
    permission_classes = (AllowAny,)
    queryset = Languages.objects.all()

    @method_decorator(cache_page(settings.CACHE_TTL))
    def list(self, request):
        lang = Languages.objects.filter(language="en")
        if lang:
            serializer = LanguageSerializer(lang, many=True)
            return Response(serializer.data, status=200)
        else:
            lang = Languages.objects.filter(language="en")
            serializer = LanguageSerializer(lang, many=True)
            return Response(serializer.data, status=200)


class FeedbackView(APIView):
    """
    APIView to send feedback by Post request
    """

    serializer_class = UserFeedbackSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_serializer(self, *args, **kwargs):
        return UserFeedbackSerializer(*args, **kwargs)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            feedback_mail(request, serializer.data)
            return Response({"data": "Feedback Sent Successfully"}, status=200)
        else:
            return Response(serializer.errors, status=400)


class UserDeleteView(APIView):
    serializer_class = UserRemoveSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        user = request.data["user_id"]
        UserDelete().save_delete_record(user)
        try:
            user = User.objects.get(id=user)
            message = "Your request for aapoon account deletion has been performed successfully."
            if user.email:
                subject = "Account Closure Request"
                # template = "account/email/account_closure.html"
                # send_email_notification(user, template, subject)
            else:
                phone = str(user.updated_country_code) + str(user.updated_phone_number)
                send_sms_message(message, user, phone)
        except SMTPAuthenticationError:
            return Response(
                data={"data": "SMTP Error"}, status=status.HTTP_400_BAD_REQUEST
            )
        except User.DoesNotExist:
            return Response(
                data={"data": "User doesn't exist."}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            data={"data": "User added to be deleted list."}, status=status.HTTP_200_OK
        )


class UserDeleteRevokeView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    allowed_methods = ("POST",)
    serializer_class = UserRemoveSerializer

    def post(self, request):
        user = request.data["user_id"]
        DeletedUser.objects.filter(user=user).delete()
        return Response(
            data={"data": "User deletion action revoked"}, status=status.HTTP_200_OK
        )


class InviteListView(APIView):
    """
    Download Invite User List
    """

    permission_classes = (permissions.IsAuthenticated,)
    allowed_methods = ("GET",)

    def get(self, request):
        try:
            user = request.user

            invites = UserInvite.objects.filter(user=user)

            with open(str(user.id) + ".csv", "w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["Name", "Phone Number", "Status"])
                for invitee in invites:
                    invitees = User.objects.filter(
                        phone_number=invitee.invited_phone_number,
                        country_code=invitee.invited_country_code,
                    )

                    invitees = invitees[0]
                    name = invitees.name
                    phone = str(invitees.country_code) + str(invitees.phone_number)
                    status = False
                    try:
                        logs = invitees.logs.get().kyc_logs
                        attempts = re.findall(r"<b>Target Image: https://", logs)
                    except:
                        pass
                    kyc_done = invitees.kyc.get().completed
                    if logs and len(attempts) >= 2:
                        if (
                            invitees.phone_number_verified
                            and len(attempts) >= 2
                            and not kyc_done
                        ):
                            status = "pending"
                    elif kyc_done:
                        status = "Fully Verified"
                    elif invitees.phone_number_verified:
                        status = "Basic Verified"
                    elif invitees.phone_number_verified:
                        status = "Phone  Verified"
                    writer.writerow([name, phone, status])
            file_path = "/tmp/" + str(user.id) + ".csv"
            if os.path.exists(file_path):
                with open(file_path, "rb") as fh:
                    response = HttpResponse(
                        fh.read(), content_type="application/vnd.ms-excel"
                    )
                    response[
                        "Content-Disposition"
                    ] = "inline; filename=" + os.path.basename(file_path)
                    return response
            raise Http404

        except Exception as e:
            logger.error(e)
            return Response([], status=200)


class UserDetailsAPI(APIView):
    permission_classes = (HasAPIKey,)
    allowed_methods = ("POST",)

    def post(self, request):
        serializer = UserDetailsInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.data.get("user_id")
        user_jid = serializer.data.get("user_jid")

        if user_id:
            user = self.get_user("id", user_id)
        elif user_jid:
            user = self.get_user("jid", user_jid)
        else:
            return Response(
                {"error": "Input data error"}, status=status.HTTP_403_FORBIDDEN
            )

        if not user:
            return Response(
                {"error": "user not found"}, status=status.HTTP_400_BAD_REQUEST
            )

        serializer = UserDetailsSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_user(self, key, value):
        filters = {key: value}
        try:
            user = User.objects.get(**filters)
        except User.DoesNotExist:
            user = None
        return user
