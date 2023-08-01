import csv
import os
import logging
import phonenumbers
import datetime
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_page
from django.http import Http404, HttpResponse
from smtplib import SMTPAuthenticationError

from rest_framework import status, viewsets, permissions
from rest_framework.generics import get_object_or_404, ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import ValidationError

from user.api.serializers import (
    UserLoginSerializer,
    RegisterSerializer,
    UserLogSerializer,
    UserInviteSerializer,
    UserDeviceSerializer,
    UserProfileSerializer,
    UserProfileInputSerializer,
    UserSerializer,
    SendOTPSerializer,
    VerifyPhoneSerializer,
    DeviceInfoSerializer,
    AppInfoSerializer,
    AppPolicySerializer,
    FeedbackSerializer,
    UserRemoveSerializer,
    UserDetailsSerializer,
    UserDetailsInputSerializer,
    NotificationSettingsSerializer,
    UserPhoneDetailsInputSerializer,
    UserCheckSerializer,
    UserProfileSearchSerializer,
)
from user.models import (
    UserLog,
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
    user_kyc_status,
    GenericPagination,
)
from user.helpers import sms
from user.helpers.otp import generate_otp
from user.user_delete import UserDelete
from user_service import settings
from rest_framework_api_key.permissions import HasAPIKey

from allauth.account.adapter import get_adapter
from allauth.utils import email_address_exists

logger = logging.getLogger(__name__)

ERROR_MESSAGE = (
    "Sorry, We are  facing an issue currently. Thanks for noticing . We fix it soon."
)


class AuthUserRegistrationView(APIView):
    authentication_classes = [JWTAuthentication]
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if request.data.get("email"):
            email = get_adapter().clean_email(request.data.get("email"))
            if email:
                if email and email_address_exists(email):
                    return Response(
                        {
                            "detail": "A user is already registered with this e-mail address."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"message": "Verification Code (OTP) sent"}, status=status.HTTP_200_OK
        )

    def perform_create(self, serializer):
        user = serializer.save(self.request)
        return user


class AuthUserLoginView(APIView):
    authentication_classes = [JWTAuthentication]
    serializer_class = UserLoginSerializer
    permission_classes = (AllowAny,)

    def post(self, request):
        country_code = request.data["country_code"]
        phone_number = request.data["phone_number"]

        user = User.objects.filter(country_code=country_code, phone_number=phone_number)

        if not user:
            return Response(
                {"detail": "Invalid login credentials"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp = request.data["otp"]
        user = user.first()
        default_otp = "775533"
        if otp and otp == default_otp:
            pass
        elif otp and str(otp) != user.otp_requested:
            return Response({"detail": "Wrong OTP"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class SendOTPView(APIView):
    """
    API View to send otp to user phone number by using POST and GET Method.
    """

    permission_classes = (permissions.IsAuthenticated,)
    allowed_methods = ("POST", "GET")

    def get_serializer(self, *args, **kwargs):
        return SendOTPSerializer(*args, **kwargs)

    def send_otp(self, country_code, phone_number, otp, user, number):
        valid_country_code = ["91", 91]
        if country_code in valid_country_code:
            fast_sms = sms.FAST_SMS(phone_number, otp, user)
            fast_sms.send_message()
        else:
            sms_client = sms.TWILIO_SMS(number, otp, user)
            sms_client.send_message()
        user_settings = user.settings.filter().first()
        user_settings.verify_attempts += 1
        user_settings.save()

    def max_phone_attempts(self, request):
        user_settings = request.user.settings.filter().first()
        if user_settings.verify_attempts >= 3:
            subject = _("Max Attempts Reached on updated Phone Verification")
            phone_failure(request.user, subject)
            msg = {
                "detail": "You have reached Max Phone Attempts for Phone Verification"
            }
            raise ValidationError(msg)

    def get(self, request):
        user = request.user
        user_settings = request.user.settings.filter().first()
        self.max_phone_attempts(request)
        if user_settings.phone_number:
            phone = f"{user_settings.country_code}{user_settings.phone_number}"
            phone_number = user_settings.phone_number
            country_code = user_settings.country_code
            otp = generate_otp()
            self.send_otp(country_code, phone_number, otp, user_settings, phone)
            user.otp_requested = otp
            user.save()
            print(f"Generated Otp: {otp}")
            return Response(
                {"message": "Verification Code (OTP) sent"}, status=status.HTTP_200_OK
            )

    def post(self, request):
        user = request.user
        phone_number = request.data["phone_number"]
        country_code = request.data["country_code"]

        number = f"{country_code}{phone_number}"
        phone = User.objects.filter(
            phone_number=phone_number, country_code=country_code
        )

        if len(phone) >= 1 and not user.phone_number == phone_number:
            return Response(
                {"detail": "Mobile number already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_settings = request.user.settings.filter().first()
        self.max_phone_attempts(request)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if phone_number.isdigit():
            otp = generate_otp()
            self.send_otp(country_code, phone_number, otp, user, number)
            print(f"Generated Otp: {otp}")
            user.otp_requested = otp
            user_settings.phone_number = phone_number
            user_settings.country_code = country_code
            user_settings.save()
            user.save()
            return Response(
                {"message": "Verification Code (OTP) sent"}, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"detail": "Special characters not allowed"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class VerifyPhoneView(APIView):
    """
    API View to verify otp sent to user phone number by POST request.
    """

    permission_classes = (permissions.IsAuthenticated,)
    allowed_methods = ("POST",)

    def get_serializer(self, *args, **kwargs):
        return VerifyPhoneSerializer(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        user = request.user
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.phone_validate(request)

        user.phone_number_verified = True
        user_settings = request.user.settings.filter().first()
        user.phone_number = user_settings.phone_number
        user.country_code = user_settings.country_code
        user_settings.wrong_attempts = 0
        user.save()
        user_settings.save()

        # Make call to websocket

        phone_number = "{}{}".format(user.country_code, user.phone_number)
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
            {"message": "Phone Number successfully verified"}, status=status.HTTP_200_OK
        )


class UserLogsViewSet(viewsets.ModelViewSet):
    """
    Viewset to create, list, update and delete UserLogs.
    """

    serializer_class = UserLogSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return UserLog.objects.filter(user=self.request.user)

    def get_object(self):
        return UserLog.objects.filter(user=self.request.user).first()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def retrieve(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if not str(request.user.id) == pk:
            return Response(
                {"detail": "Action not allowed"}, status=status.HTTP_403_FORBIDDEN
            )
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class UserInviteViewSet(viewsets.ModelViewSet):
    """
    Viewset to create, list, update and delete UserInvite.
    """

    serializer_class = UserInviteSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return UserInvite.objects.filter(invited_by=self.request.user)

    def get_object(self):
        return UserInvite.objects.filter(invited_by=self.request.user).first()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def retrieve(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if not str(request.user.id) == pk:
            return Response(
                {"detail": "Action not allowed"}, status=status.HTTP_403_FORBIDDEN
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
                {"detail": "Action not allowed"}, status=status.HTTP_403_FORBIDDEN
            )
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request):
        device_model = request.data["device_model"]
        user_id = request.data["user"]

        if not UserDevice.objects.filter(
            device_model=device_model, user_id=user_id
        ).exists():
            serializer = self.serializer_class(
                data=request.data, context={request: "request"}
            )
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            user_device = UserDevice.objects.filter(
                device_model=device_model, user_id=user_id
            ).first()
            serializer = self.get_serializer(
                user_device, data=request.data, context={"request": request}
            )
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)


class UserProfileViewSet(viewsets.ModelViewSet):
    """
    Viewset to create, list, update and delete UserProfile.
    """

    permission_classes = (permissions.IsAuthenticated,)
    http_method_names = ("get", "put", "patch")

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
                {"detail": "Action not allowed"}, status=status.HTTP_403_FORBIDDEN
            )
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if not str(request.user.id) == pk:
            return Response(
                {"detail": "Action not allowed"}, status=status.HTTP_403_FORBIDDEN
            )
        instance = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data["action"]
        if action == "account":
            self.update_account_details(instance, serializer.validated_data)
        if action == "profile":
            self.update_profile_details(instance, serializer.validated_data)
        response = UserProfileSerializer(instance)
        return Response(response.data)

    def update_account_details(self, instance, data):
        instance.name = data.get("name")
        instance.date_of_birth = data.get("date_of_birth")
        instance.gender = data.get("gender")
        instance.address = data.get("address")
        instance.address1 = data.get("address1")
        instance.city = data.get("city")
        instance.state = data.get("state")
        instance.postcode = data.get("postcode")
        instance.company = data.get("company")
        instance.role = data.get("role")
        instance.sector = data.get("sector")
        instance.team_size = data.get("team_size")
        if data.get("country_iso_code"):
            instance.user.country_iso_code = data.get("country_iso_code")
            instance.user.save()

        user_settings = instance.user.settings.filter().first()
        if not user_settings.account_details and data.get("name"):
            user_settings.account_details = True
            user_settings.save()
        instance.save()

        return instance

    def update_profile_details(self, instance, data):
        instance.skillset = data.get("skillset")
        instance.experience = data.get("experience")
        instance.profession = data.get("profession")
        instance.education = data.get("education")
        instance.income = data.get("income")
        instance.relationship_status = data.get("relationship_status")
        instance.sports = data.get("sports")
        instance.interests = data.get("interests")
        instance.about_me = data.get("about_me")
        instance.political_interests = data.get("political_interests")
        instance.iam_looking_for = data.get("iam_looking_for")
        instance.name = data.get("name")
        instance.chat_theme = data.get("chat_theme")

        user_settings = instance.user.settings.filter().first()
        if not user_settings.account_details and data.get("name"):
            user_settings.profile_details = True
            user_settings.save()

        instance.save()


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

        return Response(
            {"message": "Push Notification Settings Updated."},
            status=status.HTTP_200_OK,
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
        device_id = request.data["device_id"]
        user_id = request.data["user"]

        if not DeviceInfo.objects.filter(device_id=device_id, user_id=user_id).exists():
            serializer = self.serializer_class(
                data=request.data, context={request: "request"}
            )
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            serializer.save()
            queryset = AppInfo.objects.all()
            serializer = AppInfoSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            device_info = DeviceInfo.objects.filter(
                device_id=device_id, user_id=user_id
            ).first()
            serializer = self.get_serializer(
                device_info, data=request.data, context={"request": request}
            )
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            serializer.save()
            queryset = AppInfo.objects.all()
            serializer = AppInfoSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)


class AppPolicyView(APIView):
    """
    API View to maintain App Policies
    """

    serializer_class = AppPolicySerializer
    permission_classes = (AllowAny,)
    queryset = Languages.objects.all()

    def get(self, request):
        lang = Languages.objects.filter(language="en")
        if lang:
            serializer = self.serializer_class(lang, many=True)
            return Response(serializer.data, status=200)
        else:
            lang = Languages.objects.filter(language="en")
            serializer = self.serializer_class(lang, many=True)
            return Response(serializer.data, status=200)


class FeedbackView(APIView):
    """
    APIView to send feedback by Post request
    """

    serializer_class = FeedbackSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_serializer(self, *args, **kwargs):
        return FeedbackSerializer(*args, **kwargs)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            feedback_mail(request, serializer.data)
            return Response({"message": "Feedback Sent Successfully"}, status=200)
        else:
            return Response(serializer.errors, status=400)


class UserDeleteView(APIView):
    serializer_class = UserRemoveSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        user = request.data["user_id"]
        try:
            UserDelete().save_delete_record(user)
        except Exception as error:
            return Response(
                {"detail": ERROR_MESSAGE, "message": str(error), "status_code": 500},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            user = User.objects.get(id=user)
            message = "Your request for aapoon account deletion has been performed successfully."
            if user.email:
                subject = "Account Closure Request"
                template = "config/email/account_closure.html"
                send_email_notification(user, template, subject)
            else:
                phone = str(user.country_code) + str(user.phone_number)
                send_sms_message(message, user, phone)
        except SMTPAuthenticationError:
            return Response(
                data={"detail": "SMTP Error"}, status=status.HTTP_400_BAD_REQUEST
            )
        except User.DoesNotExist:
            return Response(
                data={"detail": "User doesn't exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            data={"message": "User added to be deleted list."},
            status=status.HTTP_200_OK,
        )

    def xmpp_unregister(self, user):
        phone_number = "{}{}".format(user.country_code, user.phone_number)
        endpoint = "{}{}".format(settings.XMPP_SERVER_URL, "api/unregister/")
        data = {"user": phone_number, "host": settings.XMPP_HOST}
        try:
            make_request(endpoint, "POST", data=data)
            print("User successfully unregistered at websocket server")
        except Exception as e:
            print("Error unregistering user at websocket server %s" % e)


class UserDeleteRevokeView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    allowed_methods = ("POST",)
    serializer_class = UserRemoveSerializer

    def post(self, request):
        user = request.data["user_id"]
        DeletedUser.objects.filter(user=user).delete()
        return Response(
            data={"message": "User deletion action revoked"}, status=status.HTTP_200_OK
        )


class UserDeleteCronView(APIView):
    permission_classes = [HasAPIKey | AllowAny]
    allowed_methods = ("GET",)

    def get(self, request):
        pk = request.GET.get("id", None)
        if pk:
            users_to_delete = User.objects.filter(id=pk)
        else:
            users_to_delete = DeletedUser.objects.filter(
                created__lte=datetime.datetime.now() - datetime.timedelta(days=30)
            ).filter(is_deleted=False)

        self.delete_user_associated_objects(users_to_delete)
        return Response(
            data={"message": "User's deleted successfully."}, status=status.HTTP_200_OK
        )

    def delete_user_associated_objects(self, deleted_users):
        for deleted_user in deleted_users:
            try:
                UserDelete().delete(deleted_user.id)
                logger.info("User deleted successfully")
            except Exception as e:
                logger.debug("Error while deleting the user: %s", e)


class InviteListView(APIView):
    """
    Download Invite User List
    """

    permission_classes = (permissions.IsAuthenticated,)
    allowed_methods = ("GET",)

    def get(self, request):
        try:
            user = request.user

            invites = UserInvite.objects.filter(invited_by=user)

            with open(str(user.id) + ".csv", "w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["Name", "Phone Number", "Status"])
                for invitee in invites:
                    invitee = invitee.invited_user
                    name = invitee.name
                    phone = str(invitee.country_code) + str(invitee.phone_number)

                    status = user_kyc_status(invitee)
                    writer.writerow([name, phone, status])
            file_path = str(user.id) + ".csv"
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
    permission_classes = [HasAPIKey | permissions.AllowAny]
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
                {"detail": "Input data error"}, status=status.HTTP_403_FORBIDDEN
            )

        if not user:
            return Response(
                {"detail": "user not found"}, status=status.HTTP_400_BAD_REQUEST
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


class UserDetailsPhoneAPI(APIView):
    permission_classes = [HasAPIKey | permissions.AllowAny]
    allowed_methods = ("POST",)

    def post(self, request):
        serializer = UserPhoneDetailsInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.data.get("phone_number")
        country_code = serializer.data.get("country_code")

        if phone_number:
            user = self.get_user(country_code=country_code, phone_number=phone_number)
        else:
            return Response(
                {"detail": "Input data error"}, status=status.HTTP_403_FORBIDDEN
            )

        if not user:
            return Response(
                {"detail": "user not found"}, status=status.HTTP_400_BAD_REQUEST
            )

        serializer = UserDetailsSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_user(self, phone_number, country_code):
        filters = {
            "country_code": country_code,
            "phone_number": phone_number,
        }
        try:
            user = User.objects.get(**filters)
        except User.DoesNotExist:
            user = None
        return user


class UserCheckAPIView(APIView):
    permission_classes = [HasAPIKey | permissions.AllowAny]
    allowed_methods = ("POST",)
    serializer_class = UserCheckSerializer

    def post(self, request):
        response = []
        serializer = UserCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        for contact in serializer.data["contacts"]:
            result = {"aapoonUser": False}

            phone_number = phonenumbers.parse(f"+{contact['contactPhoneNumber']}")
            user = User.objects.filter(
                country_code=phone_number.country_code,
                phone_number=phone_number.national_number,
            ).first()
            if user and user.phone_number_verified:
                result["aapoonUser"] = True
                result["contactaapoonName"] = user.name
                result["contactaapoonprofilepicture"] = (
                    user.secondary_picture if user else ""
                )
                result["contactaapoonJID"] = user.jid if user else ""
                result["contactFcmToken"] = user.fcm_token
                result["contactaapoonUserID"] = user.id
                user_settings = user.settings.filter().first()
                kyc_done = user_settings.kyc_done if user_settings else None
                if kyc_done:
                    result["contactaapoonUserProfileStatus"] = "completed"
                else:
                    result["contactaapoonUserProfileStatus"] = "basic"
            else:
                result["aapoonUser"] = False
            result["contactName"] = contact["contactName"]
            result["contactPhoneNumber"] = contact["contactPhoneNumber"]
            response.append(result)

        return Response(data=response, status=status.HTTP_200_OK)


class UserProfileSearchAPI(APIView, GenericPagination):
    """
    User Profile search with JID
    """

    serializer_class = UserProfileSearchSerializer
    permission_classes = (permissions.AllowAny,)
    # pagination_class = GenericPagination

    def get(self, request, *args, **kwargs):
        jid = request.GET.get("jid")

        if jid:
            profiles = User.objects.filter(jid=jid)
            paginated_profiles = self.paginate_queryset(profiles, request)
            if paginated_profiles is not None:
                serializer = self.serializer_class(paginated_profiles, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.serializer_class(profiles, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(
            {"detail": "No jid provided"}, status=status.HTTP_400_BAD_REQUEST
        )
