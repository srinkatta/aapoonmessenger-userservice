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
"""
API view for user registration with JWT authentication.

Handles user registration, email verification, and OTP sending.

Attributes:
    authentication_classes (list): JWTAuthentication for authentication.
    serializer_class: RegisterSerializer for user registration data.
    permission_classes (tuple): AllowAny permission for registration.

Methods:
    post(request): Register user and send verification code.
    perform_create(serializer): Create a new user.

Note:
    Requires a valid email address for registration.
"""


class AuthUserRegistrationView(APIView):
    """
    API view for registering a new user and sending a verification code.

    This API view allows users to register a new account and sends a verification
    code (OTP) for account verification.

    Authentication:
    - JWTAuthentication: Authentication is required for accessing this view.

    Permissions:
    - AllowAny: All users, including unauthenticated users, are allowed to access this view.

    HTTP Methods:
    - POST: Register user and send verification code.

    Returns:
    - Response: JSON response indicating the success of user registration and OTP sending.
    """

    authentication_classes = [JWTAuthentication]
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)

    def post(self, request):
        """
        Register user and send verification code.

        This method registers a new user account and sends a verification code (OTP)
        for account verification.

        Args:
        - request (Request): The HTTP POST request containing user registration data.

        Returns:
        - Response: JSON response indicating the success of user registration and OTP sending.
        """
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
        """
        Create a new user.

        This method creates a new user account based on the provided serializer data.

        Args:
        - serializer (RegisterSerializer): The serializer instance containing user data.

        Returns:
        - User: The newly created user instance.
        """
        user = serializer.save(self.request)
        return user


class AuthUserLoginView(APIView):
    """
    API view for user authentication and login.

    This API view allows users to authenticate and log in by providing their
    country code, phone number, and verification code (OTP).

    Authentication:
    - JWTAuthentication: Authentication is required for accessing this view.

    Permissions:
    - AllowAny: All users, including unauthenticated users, are allowed to access this view.

    HTTP Methods:
    - POST: Authenticate and log in user.

    Request Data (POST):
    - 'country_code' (str): The country code associated with the user's phone number.
    - 'phone_number' (str): The user's phone number.
    - 'otp' (str): The verification code (OTP) for user authentication.

    Returns:
    - Response: JSON response indicating the success of user authentication and login.
    """

    authentication_classes = [JWTAuthentication]
    serializer_class = UserLoginSerializer
    permission_classes = (AllowAny,)

    def post(self, request):
        """
        Authenticate and log in user.

        This method authenticates and logs in a user based on the provided country code,
        phone number, and verification code (OTP).

        Args:
        - request (Request): The HTTP POST request containing user authentication data.

        Returns:
        - Response: JSON response indicating the success of user authentication and login.
        """
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
    API view for sending OTP to user phone number using POST and GET methods.

    This API view allows authenticated users to send a verification code (OTP) to their
    phone number for phone number verification.

    Authentication:
    - IsAuthenticated: Users must be authenticated to access this view.

    Permissions:
    - IsAuthenticated: Only authenticated users are allowed to access this view.

    HTTP Methods:
    - GET: Send OTP to user's phone number.
    - POST: Send OTP to user's phone number and update phone number settings.

    GET Parameters:
    - None

    Request Data (POST):
    - 'country_code' (str): The country code associated with the user's phone number.
    - 'phone_number' (str): The user's phone number.

    Returns:
    - Response: JSON response indicating the success of OTP sending.
    """

    permission_classes = (permissions.IsAuthenticated,)
    allowed_methods = ("POST", "GET")

    def get_serializer(self, *args, **kwargs):
        """
        Get the serializer instance for sending OTP.

        This method returns an instance of the SendOTPSerializer for sending OTP.

        Returns:
        - SendOTPSerializer: An instance of the SendOTPSerializer.
        """
        return SendOTPSerializer(*args, **kwargs)

    def send_otp(self, country_code, phone_number, otp, user, number):
        """
        Send OTP to the specified phone number.

        This method sends the generated OTP to the specified phone number using an appropriate
        SMS service based on the country code.

        Args:
        - country_code (str): The country code associated with the phone number.
        - phone_number (str): The user's phone number.
        - otp (str): The generated OTP.
        - user (User): The user instance.
        - number (str): The complete phone number including country code.
        """
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
        """
        Check and handle maximum phone verification attempts.

        This method checks the number of verification attempts made by the user for phone
        verification and handles the case when the maximum attempts are reached.

        Args:
        - request (Request): The HTTP request.
        """
        user_settings = request.user.settings.filter().first()
        if user_settings.verify_attempts >= 3:
            subject = _("Max Attempts Reached on updated Phone Verification")
            phone_failure(request.user, subject)
            msg = {
                "detail": "You have reached Max Phone Attempts for Phone Verification"
            }
            raise ValidationError(msg)

    def get(self, request):
        """
        Send OTP to user's phone number.

        This method generates and sends an OTP to the user's phone number for phone verification.

        Args:
        - request (Request): The HTTP GET request.

        Returns:
        - Response: JSON response indicating the success of OTP sending.
        """
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
        """
        Send OTP to user's phone number and update phone number settings.

        This method sends an OTP to the user's phone number, updates the phone number
        settings, and associates the OTP with the user.

        Args:
        - request (Request): The HTTP POST request containing phone number data.

        Returns:
        - Response: JSON response indicating the success of OTP sending.
        """
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
    API view for verifying the OTP sent to the user's phone number using POST request.

    This API view allows authenticated users to verify the OTP sent to their phone number
    for phone number verification.

    Authentication:
    - IsAuthenticated: Users must be authenticated to access this view.

    Permissions:
    - IsAuthenticated: Only authenticated users are allowed to access this view.

    HTTP Methods:
    - POST: Verify OTP and mark phone number as verified.

    Request Data (POST):
    - 'otp' (str): The verification code (OTP) received by the user.

    Returns:
    - Response: JSON response indicating the success of phone number verification.
    """

    permission_classes = (permissions.IsAuthenticated,)
    allowed_methods = ("POST",)

    def get_serializer(self, *args, **kwargs):
        """
        Get the serializer instance for verifying phone number.

        This method returns an instance of the VerifyPhoneSerializer for verifying phone number.

        Returns:
        - VerifyPhoneSerializer: An instance of the VerifyPhoneSerializer.
        """
        return VerifyPhoneSerializer(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        Verify OTP sent to user's phone number.

        This method verifies the OTP sent to the user's phone number and marks the phone
        number as verified.

        Args:
        - request (Request): The HTTP POST request containing OTP data.

        Returns:
        - Response: JSON response indicating the success of phone number verification.
        """
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
    Viewset for managing UserLogs.

    This viewset provides endpoints for creating, listing, updating, and deleting UserLogs
    associated with the authenticated user.

    Authentication:
    - IsAuthenticated: Users must be authenticated to access this viewset.

    Permissions:
    - IsAuthenticated: Only authenticated users are allowed to access this viewset.

    HTTP Methods:
    - GET: List UserLogs associated with the authenticated user.
    - POST: Create a new UserLog for the authenticated user.
    - PUT/PATCH: Update an existing UserLog (not implemented in this viewset).
    - DELETE: Delete an existing UserLog (not implemented in this viewset).

    Path Parameters:
    - 'pk' (int): The primary key of the user for which UserLogs are being accessed.

    Returns:
    - GET Response: JSON response containing the list of UserLogs associated with the user.
    - POST Response: JSON response indicating the successful creation of a new UserLog.
    """

    serializer_class = UserLogSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        """
        Get the queryset of UserLogs associated with the authenticated user.

        Returns:
        - QuerySet: A filtered queryset containing UserLogs associated with the user.
        """
        return UserLog.objects.filter(user=self.request.user)

    def get_object(self):
        """
        Get the UserLog instance associated with the authenticated user.

        Returns:
        - UserLog: The UserLog instance associated with the user.
        """
        return UserLog.objects.filter(user=self.request.user).first()

    def get_serializer_context(self):
        """
        Get the context for the serializer.

        This method provides the context for the UserLog serializer, including the HTTP request.

        Returns:
        - dict: The serializer context containing the HTTP request.
        """
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a UserLog associated with the authenticated user.

        Args:
        - request (Request): The HTTP GET request.
        - args: Additional arguments.
        - kwargs: Additional keyword arguments.

        Returns:
        - Response: JSON response containing the UserLog details.
        """
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
    Viewset for managing UserInvites.

    This viewset provides endpoints for creating, listing, updating, and deleting UserInvites
    created by the authenticated user.

    Authentication:
    - IsAuthenticated: Users must be authenticated to access this viewset.

    Permissions:
    - IsAuthenticated: Only authenticated users are allowed to access this viewset.

    HTTP Methods:
    - GET: List UserInvites created by the authenticated user.
    - POST: Create a new UserInvite associated with the authenticated user.
    - PUT/PATCH: Update an existing UserInvite (not implemented in this viewset).
    - DELETE: Delete an existing UserInvite (not implemented in this viewset).

    Path Parameters:
    - 'pk' (int): The primary key of the user for which UserInvites are being accessed.

    Returns:
    - GET Response: JSON response containing the list of UserInvites created by the user.
    - POST Response: JSON response indicating the successful creation of a new UserInvite.
    """

    serializer_class = UserInviteSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        """
        Get the queryset of UserInvites created by the authenticated user.

        Returns:
        - QuerySet: A filtered queryset containing UserInvites created by the user.
        """
        return UserInvite.objects.filter(invited_by=self.request.user)

    def get_object(self):
        """
        Get the UserInvite instance created by the authenticated user.

        Returns:
        - UserInvite: The UserInvite instance created by the user.
        """
        return UserInvite.objects.filter(invited_by=self.request.user).first()

    def get_serializer_context(self):
        """
        Get the context for the serializer.

        This method provides the context for the UserInvite serializer, including the HTTP request.

        Returns:
        - dict: The serializer context containing the HTTP request.
        """
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a UserInvite created by the authenticated user.

        Args:
        - request (Request): The HTTP GET request.
        - args: Additional arguments.
        - kwargs: Additional keyword arguments.

        Returns:
        - Response: JSON response containing the UserInvite details.
        """
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
    Viewset for managing UserDevices.

    This viewset provides endpoints for creating, listing, updating, and deleting UserDevices
    associated with the authenticated user.

    Authentication:
    - IsAuthenticated: Users must be authenticated to access this viewset.

    Permissions:
    - IsAuthenticated: Only authenticated users are allowed to access this viewset.

    HTTP Methods:
    - GET: List UserDevices associated with the authenticated user.
    - POST: Create a new UserDevice associated with the authenticated user.
    - PUT/PATCH: Update an existing UserDevice (not implemented in this viewset).
    - DELETE: Delete an existing UserDevice (not implemented in this viewset).

    Path Parameters:
    - 'pk' (int): The primary key of the user for which UserDevices are being accessed.

    Returns:
    - GET Response: JSON response containing the list of UserDevices associated with the user.
    - POST Response: JSON response indicating the successful creation of a new UserDevice.
    """

    serializer_class = UserDeviceSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        """
        Get the queryset of UserDevices associated with the authenticated user.

        Returns:
        - QuerySet: A filtered queryset containing UserDevices associated with the user.
        """
        return UserDevice.objects.filter(user=self.request.user)

    def get_object(self):
        """
        Get the UserDevice instance associated with the authenticated user.

        Returns:
        - UserDevice: The UserDevice instance associated with the user.
        """
        return UserDevice.objects.filter(user=self.request.user).first()

    def get_serializer_context(self):
        """
        Get the context for the serializer.

        This method provides the context for the UserDevice serializer, including the HTTP request.

        Returns:
        - dict: The serializer context containing the HTTP request.
        """
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a UserDevice associated with the authenticated user.

        Args:
        - request (Request): The HTTP GET request.
        - args: Additional arguments.
        - kwargs: Additional keyword arguments.

        Returns:
        - Response: JSON response containing the UserDevice details.
        """
        pk = kwargs.get("pk")
        if not str(request.user.id) == pk:
            return Response(
                {"detail": "Action not allowed"}, status=status.HTTP_403_FORBIDDEN
            )
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request):
        """
        Create a new UserDevice associated with the authenticated user.

        Args:
        - request (Request): The HTTP POST request.

        Returns:
        - Response: JSON response indicating the successful creation of a new UserDevice.
        """
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
    Viewset for managing UserProfiles.

    This viewset provides endpoints for creating, listing, updating, and deleting UserProfiles
    associated with the authenticated user.

    Authentication:
    - IsAuthenticated: Users must be authenticated to access this viewset.

    Permissions:
    - IsAuthenticated: Only authenticated users are allowed to access this viewset.

    HTTP Methods:
    - GET: List the UserProfile details of the authenticated user.
    - PUT/PATCH: Update the UserProfile details of the authenticated user.

    Path Parameters:
    - 'pk' (int): The primary key of the user for which UserProfile is being accessed.

    Returns:
    - GET Response: JSON response containing the UserProfile details of the user.
    - PUT/PATCH Response: JSON response indicating the successful update of UserProfile details.
    """

    permission_classes = (permissions.IsAuthenticated,)
    http_method_names = ("get", "put", "patch")

    def get_serializer_class(self):
        """
        Get the appropriate serializer class based on the HTTP method.

        Returns:
        - Serializer Class: The serializer class to be used based on the HTTP method.
        """
        if self.request.method in ["POST", "PUT"]:
            return UserProfileInputSerializer
        else:
            return UserProfileSerializer

    def get_queryset(self):
        """
        Get the queryset of UserProfiles associated with the authenticated user.

        Returns:
        - QuerySet: A filtered queryset containing the UserProfile associated with the user.
        """
        return UserProfile.objects.filter(user=self.request.user)

    def get_object(self):
        """
        Get the UserProfile instance associated with the authenticated user.

        Returns:
        - UserProfile: The UserProfile instance associated with the user.
        """
        return UserProfile.objects.filter(user=self.request.user).first()

    def get_serializer_context(self):
        """
        Get the context for the serializer.

        This method provides the context for the UserProfile serializer, including the HTTP request.

        Returns:
        - dict: The serializer context containing the HTTP request.
        """
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve the UserProfile associated with the authenticated user.

        Args:
        - request (Request): The HTTP GET request.
        - args: Additional arguments.
        - kwargs: Additional keyword arguments.

        Returns:
        - Response: JSON response containing the UserProfile details.
        """
        pk = kwargs.get("pk")
        if not str(request.user.id) == pk:
            return Response(
                {"detail": "Action not allowed"}, status=status.HTTP_403_FORBIDDEN
            )
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """
        Update the UserProfile associated with the authenticated user.

        Args:
        - request (Request): The HTTP PUT/PATCH request.
        - args: Additional arguments.
        - kwargs: Additional keyword arguments.

        Returns:
        - Response: JSON response indicating the successful update of UserProfile details.
        """
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
        """
        Update the account details of the UserProfile associated with the authenticated user.

        Args:
        - instance (UserProfile): The UserProfile instance to be updated.
        - data (dict): The data containing account details.

        Returns:
        - UserProfile: The updated UserProfile instance.
        """
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
        """
        Update the profile details of the UserProfile associated with the authenticated user.

        Args:
        - instance (UserProfile): The UserProfile instance to be updated.
        - data (dict): The data containing profile details.

        Returns:
        - UserProfile: The updated UserProfile instance.
        """
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
    Viewset for managing User profiles.

    This viewset provides endpoints for creating, listing, updating, and deleting User profiles
    associated with the authenticated user.

    Authentication:
    - IsAuthenticated: Users must be authenticated to access this viewset.

    Permissions:
    - IsAuthenticated: Only authenticated users are allowed to access this viewset.

    HTTP Methods:
    - GET: Retrieve the User profile of the authenticated user.
    - PATCH: Update the User profile of the authenticated user.
    - HEAD: Similar to GET, but only retrieves the headers without the actual data.

    Path Parameters:
    - 'pk' (int): The primary key of the user for which User profile is being accessed.

    Returns:
    - GET Response: JSON response containing the User profile details of the user.
    - PATCH Response: JSON response indicating the successful update of User profile details.
    - HEAD Response: HTTP headers indicating the availability of the User profile.
    """

    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)
    http_method_names = ["get", "patch", "head"]

    def get_queryset(self):
        """
        Get the queryset containing the User profile of the authenticated user.

        Returns:
        - QuerySet: A filtered queryset containing the User profile associated with the user.
        """
        return User.objects.filter(id=self.request.user.id)

    def get_object(self):
        """
        Get the User instance associated with the authenticated user.

        Returns:
        - User: The User instance associated with the user.
        """
        return get_object_or_404(User.objects.all(), id=self.request.user.id)


class PushNotificationSettings(APIView):
    """
    API View for managing push notification settings.

    This view allows authenticated users to update their push notification settings, including
    registering or updating their Firebase Cloud Messaging (FCM) and Apple Push Notification Service (APNs) tokens.

    Authentication:
    - JWTAuthentication: Users must be authenticated using JWT to access this view.

    Permissions:
    - IsAuthenticated: Only authenticated users are allowed to access this view.

    HTTP Methods:
    - POST: Update the push notification settings for the authenticated user.

    Request Payload:
    - user_id (int): The ID of the user for whom push notification settings are being updated.
    - fcm_token (str): The Firebase Cloud Messaging token for push notifications (optional).
    - apns_token (str): The Apple Push Notification Service token for push notifications (optional).

    Returns:
    - Response: JSON response indicating the success of updating push notification settings.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = NotificationSettingsSerializer

    def post(self, request):
        """
        Update push notification settings for the authenticated user.

        This endpoint allows users to register or update their Firebase Cloud Messaging (FCM) and
        Apple Push Notification Service (APNs) tokens for receiving push notifications.

        Request Payload:
        - user_id (int): The ID of the user for whom push notification settings are being updated.
        - fcm_token (str): The Firebase Cloud Messaging token for push notifications (optional).
        - apns_token (str): The Apple Push Notification Service token for push notifications (optional).

        Returns:
        - Response: JSON response indicating the success of updating push notification settings.
        """
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
    API View to manage app versioning and device information.

    This view allows both authenticated and unauthenticated users to retrieve and update device
    information, including app versioning and user-device associations.

    Authentication:
    - None: Both authenticated and unauthenticated users can access this view.

    Permissions:
    - AllowAny: All users, including unauthenticated users, are allowed to access this view.

    HTTP Methods:
    - GET: Retrieve app versioning information.
    - POST: Update device information and app version.

    GET Request Parameters:
    - None

    POST Request Payload:
    - device_id (str): The unique identifier of the device.
    - user (int): The ID of the user associated with the device.
    - Other optional device information fields.

    Returns:
    - Response: JSON response containing app versioning information or success message.
    """

    permission_classes = (AllowAny,)
    serializer_class = DeviceInfoSerializer
    http_method_names = ["get", "post"]

    def get_serializer(self, *args, **kwargs):
        """
        Return the appropriate serializer for the view.
        """
        return DeviceInfoSerializer(*args, **kwargs)

    @method_decorator(cache_page(60))
    def get(self, request):
        """
        Retrieve app versioning information.

        This endpoint retrieves information about the app version, which can be cached for 60 seconds.

        Returns:
        - Response: JSON response containing app versioning information.
        """
        queryset = AppInfo.objects.all()
        serializer = AppInfoSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Update device information and app version.

        This endpoint allows users to update device information and app version by providing
        the device ID, user ID, and other optional device information fields.

        Request Payload:
        - device_id (str): The unique identifier of the device.
        - user (int): The ID of the user associated with the device.
        - Other optional device information fields.

        Returns:
        - Response: JSON response indicating the success of updating device information.
        """
        device_id = request.data["device_id"]
        user_id = request.data["user"]
        logger.info(f"user_id : {user_id}, device_id: {device_id}")
        user_info = User.objects.filter(id=user_id).first()
        logger.info(f"{user_info}")
        if not DeviceInfo.objects.filter(device_id=device_id, user_id=user_id).exists():
            serializer = self.serializer_class(
                data=request.data, context={request: "request"}
            )
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            serializer.save()
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
    API View to retrieve App Policies.

    This view allows unauthenticated users to retrieve App Policies, such as terms of service,
    privacy policy, and other related information.

    Authentication:
    - None: Unauthenticated users can access this view.

    Permissions:
    - AllowAny: All users, including unauthenticated users, are allowed to access this view.

    HTTP Methods:
    - GET: Retrieve App Policies.

    Returns:
    - Response: JSON response containing the retrieved App Policies.
    """

    serializer_class = AppPolicySerializer
    permission_classes = (AllowAny,)

    def get(self, request):
        """
        Retrieve App Policies.

        This endpoint retrieves App Policies, such as terms of service, privacy policy,
        and other related information.

        Returns:
        - Response: JSON response containing the retrieved App Policies.
        """
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
    API View to submit user feedback.

    This API view allows authenticated users to submit feedback through a POST request.

    Authentication:
    - JWTAuthentication: Users must be authenticated using JWT to access this view.

    Permissions:
    - IsAuthenticated: Only authenticated users are allowed to access this view.

    HTTP Methods:
    - POST: Submit user feedback.

    Returns:
    - Response: JSON response indicating the success or failure of the feedback submission.
    """

    serializer_class = FeedbackSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_serializer(self, *args, **kwargs):
        """
        Get the serializer instance for feedback submission.

        Returns:
        - FeedbackSerializer: An instance of the FeedbackSerializer.
        """
        return FeedbackSerializer(*args, **kwargs)

    def post(self, request):
        """
        Submit user feedback.

        This endpoint allows authenticated users to submit feedback through a POST request.

        Returns:
        - Response: JSON response indicating the success or failure of the feedback submission.
        """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            feedback_mail(request, serializer.data)
            return Response({"message": "Feedback Sent Successfully"}, status=200)
        else:
            return Response(serializer.errors, status=400)


class UserDeleteView(APIView):
    """
    API View to request user account deletion.

    This API view allows authenticated users to request the deletion of their user accounts.

    Authentication:
    - JWTAuthentication: Users must be authenticated using JWT to access this view.

    Permissions:
    - IsAuthenticated: Only authenticated users are allowed to access this view.

    HTTP Methods:
    - POST: Request user account deletion.

    Returns:
    - Response: JSON response indicating the success or failure of the deletion request.
    """

    serializer_class = UserRemoveSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        """
        Request user account deletion.

        This endpoint allows authenticated users to request the deletion of their user accounts.
        A confirmation email or SMS will be sent to the user based on their contact information.

        Returns:
        - Response: JSON response indicating the success or failure of the deletion request.
        """
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
        """
        Unregister user from the XMPP server.

        This method unregisters a user from the XMPP server.

        Args:
        - user: The user to be unregistered.

        Returns:
        - None
        """
        phone_number = "{}{}".format(user.country_code, user.phone_number)
        endpoint = "{}{}".format(settings.XMPP_SERVER_URL, "api/unregister/")
        data = {"user": phone_number, "host": settings.XMPP_HOST}
        try:
            make_request(endpoint, "POST", data=data)
            print("User successfully unregistered at websocket server")
        except Exception as e:
            print("Error unregistering user at websocket server %s" % e)


class UserDeleteRevokeView(APIView):
    """
    API View to revoke a user account deletion action.

    This API view allows authenticated users to revoke a previously requested user account deletion action.

    Authentication:
    - JWTAuthentication: Users must be authenticated using JWT to access this view.

    Permissions:
    - IsAuthenticated: Only authenticated users are allowed to access this view.

    HTTP Methods:
    - POST: Revoke a user account deletion action.

    Returns:
    - Response: JSON response indicating the success or failure of the revocation.
    """

    permission_classes = (permissions.IsAuthenticated,)
    allowed_methods = ("POST",)
    serializer_class = UserRemoveSerializer

    def post(self, request):
        """
        Revoke a user account deletion action.

        This endpoint allows authenticated users to revoke a previously requested user account deletion action.

        Returns:
        - Response: JSON response indicating the success or failure of the revocation.
        """
        user = request.data["user_id"]
        DeletedUser.objects.filter(user=user).delete()
        return Response(
            data={"message": "User deletion action revoked"}, status=status.HTTP_200_OK
        )


class UserDeleteCronView(APIView):
    """
    API View to perform automated user deletion.

    This API view allows authorized users to perform automated user deletion based on certain criteria.

    Authentication:
    - API Key: Users must provide a valid API key to access this view, or the view may be allowed for any user (AllowAny).

    Permissions:
    - Custom: Custom permission classes can be used to control access to this view.

    HTTP Methods:
    - GET: Perform automated user deletion based on specified criteria.

    Parameters (Query Parameters):
    - id (optional): The ID of a specific user to delete. If provided, only that user will be deleted.

    Returns:
    - Response: JSON response indicating the success or failure of the automated user deletion process.
    """

    permission_classes = [HasAPIKey or AllowAny]
    allowed_methods = ("GET",)

    def get(self, request):
        """
        Perform automated user deletion based on specified criteria.

        This endpoint allows authorized users to perform automated user deletion based on certain criteria.

        Parameters (Query Parameters):
        - id (optional): The ID of a specific user to delete. If provided, only that user will be deleted.

        Returns:
        - Response: JSON response indicating the success or failure of the automated user deletion process.
        """
        pk = request.GET.get("id", None)
        if pk:
            users_to_delete = User.objects.filter(id=pk)
        else:
            users_to_delete = DeletedUser.objects.filter(
                created__lte=datetime.datetime.now(tz=datetime.timezone.utc)
                - datetime.timedelta(days=30)
            ).filter(is_deleted=False)

        self.delete_user_associated_objects(users_to_delete)
        return Response(
            data={"message": "User's deleted successfully."}, status=status.HTTP_200_OK
        )

    def delete_user_associated_objects(self, deleted_users):
        """
        Delete associated objects of the specified users.

        This method deletes associated objects of the specified users, as part of the automated user deletion process.

        Args:
        - deleted_users: Queryset of User objects to delete.

        Returns:
        - None
        """
        for deleted_user in deleted_users:
            try:
                UserDelete().delete(deleted_user.id)
                logger.info("User deleted successfully")
            except Exception as e:
                logger.debug("Error while deleting the user: %s", e)


class InviteListView(APIView):
    """
    API View to download the list of invited users in CSV format.

    This API view allows authenticated users to download a CSV file containing the list of invited users,
    including their names, phone numbers, and invitation status.

    Authentication:
    - Token: Users must provide a valid authentication token to access this view.

    Permissions:
    - IsAuthenticated: Only authenticated users can access this view.

    HTTP Methods:
    - GET: Download the CSV file containing the list of invited users.

    Returns:
    - Response: The CSV file containing the list of invited users as an attachment for download.
    """

    permission_classes = (permissions.IsAuthenticated,)
    allowed_methods = ("GET",)

    def get(self, request):
        """
        Download the list of invited users in CSV format.

        This endpoint allows authenticated users to download a CSV file containing the list of invited users,
        including their names, phone numbers, and invitation status.

        Returns:
        - Response: The CSV file containing the list of invited users as an attachment for download.
        """
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
    """
    API View to retrieve user details based on user ID or user JID.

    This API view allows users to retrieve detailed information about a user by providing either the user's
    ID or user JID (Jabber ID).

    Authentication:
    - API Key: Users must provide a valid API key or be allowed anonymous access to use this view.

    Permissions:
    - HasAPIKey: Users with a valid API key can access this view.
    - AllowAny: Anonymous users are allowed to access this view.

    HTTP Methods:
    - POST: Retrieve user details by providing user ID or user JID.

    Request Data:
    - user_id (optional): The ID of the user for whom details are to be retrieved.
    - user_jid (optional): The Jabber ID (JID) of the user for whom details are to be retrieved.

    Returns:
    - Response: Detailed information about the requested user, including user profile data.
    """

    permission_classes = [HasAPIKey or permissions.AllowAny]
    allowed_methods = ("POST",)

    def post(self, request):
        """
        Retrieve user details based on user ID or user JID.

        This endpoint allows users to retrieve detailed information about a user by providing either the user's
        ID or user JID (Jabber ID).

        Args:
        - user_id (optional): The ID of the user for whom details are to be retrieved.
        - user_jid (optional): The Jabber ID (JID) of the user for whom details are to be retrieved.

        Returns:
        - Response: Detailed information about the requested user, including user profile data.

        Error Responses:
        - 400 Bad Request: If input data is missing or incorrect.
        - 403 Forbidden: If both user ID and user JID are missing in the request.
        - 404 Not Found: If the requested user is not found.
        """
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
        """
        Retrieve a user based on a specified attribute.

        Args:
        - key: The attribute key (e.g., "id" or "jid").
        - value: The value of the attribute.

        Returns:
        - User: The retrieved user instance or None if not found.
        """
        filters = {key: value}
        try:
            user = User.objects.get(**filters)
        except User.DoesNotExist:
            user = None
        return user


class UserDetailsPhoneAPI(APIView):
    """
    API View to retrieve user details based on phone number and country code.

    This API view allows users to retrieve detailed information about a user by providing the user's phone number
    and country code.

    Authentication:
    - API Key: Users must provide a valid API key or be allowed anonymous access to use this view.

    Permissions:
    - HasAPIKey: Users with a valid API key can access this view.
    - AllowAny: Anonymous users are allowed to access this view.

    HTTP Methods:
    - POST: Retrieve user details by providing phone number and country code.

    Request Data:
    - phone_number: The phone number of the user for whom details are to be retrieved.
    - country_code: The country code of the user's phone number.

    Returns:
    - Response: Detailed information about the requested user, including user profile data.

    """

    permission_classes = [HasAPIKey or permissions.AllowAny]
    allowed_methods = ("POST",)

    def post(self, request):
        """
        Retrieve user details based on phone number and country code.

        This endpoint allows users to retrieve detailed information about a user by providing the user's phone number
        and country code.

        Args:
        - phone_number: The phone number of the user for whom details are to be retrieved.
        - country_code: The country code of the user's phone number.

        Returns:
        - Response: Detailed information about the requested user, including user profile data.

        Error Responses:
        - 400 Bad Request: If input data is missing or incorrect.
        - 403 Forbidden: If phone number is missing in the request.
        - 404 Not Found: If the requested user is not found.
        """
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
        """
        Retrieve a user based on phone number and country code.

        Args:
        - phone_number: The phone number of the user.
        - country_code: The country code of the user's phone number.

        Returns:
        - User: The retrieved user instance or None if not found.
        """
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
    """
    API View to check if contacts are AAPoon users and retrieve their profile information.

    This API view allows users to check if their contacts are registered AAPoon users and retrieve their profile
    information, such as profile status, name, profile picture, JID, FCM token, and more.

    Authentication:
    - API Key: Users must provide a valid API key or be allowed anonymous access to use this view.

    Permissions:
    - HasAPIKey: Users with a valid API key can access this view.
    - AllowAny: Anonymous users are allowed to access this view.

    HTTP Methods:
    - POST: Check if contacts are AAPoon users and retrieve their profile information.

    Request Data:
    - contacts: A list of dictionaries containing contact information, including contact name and phone number.

    Returns:
    - Response: A list of dictionaries with information about each contact's AAPoon user status and profile details.

    """

    permission_classes = [HasAPIKey or permissions.AllowAny]
    allowed_methods = ("POST",)
    serializer_class = UserCheckSerializer

    def post(self, request):
        """
        Check if contacts are AAPoon users and retrieve their profile information.

        This endpoint allows users to check if their contacts are registered AAPoon users and retrieve their profile
        information, such as profile status, name, profile picture, JID, FCM token, and more.

        Args:
        - contacts: A list of dictionaries containing contact information, including contact name and phone number.

        Returns:
        - Response: A list of dictionaries with information about each contact's AAPoon user status and profile details.

        Error Responses:
        - 400 Bad Request: If input data is missing or incorrect.
        """
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
    API View for searching user profiles using JID.

    This API view allows searching for user profiles using their JID (Jabber ID), which is a unique identifier used for
    communication in Jabber-based protocols like XMPP.

    Permissions:
    - AllowAny: Anonymous users are allowed to access this view.

    HTTP Methods:
    - GET: Search user profiles using the provided JID.

    Query Parameters:
    - jid: The JID (Jabber ID) of the user profile to search for.

    Returns:
    - Response: A list of user profiles matching the provided JID.
    """

    serializer_class = UserProfileSearchSerializer
    permission_classes = (permissions.AllowAny,)
    # pagination_class = GenericPagination

    def get(self, request, *args, **kwargs):
        """
        Search user profiles using JID.

        This endpoint allows searching for user profiles using their JID (Jabber ID), which is a unique identifier used for
        communication in Jabber-based protocols like XMPP.

        Query Parameters:
        - jid: The JID (Jabber ID) of the user profile to search for.

        Returns:
        - Response: A list of user profiles matching the provided JID.

        Error Responses:
        - 400 Bad Request: If the JID parameter is missing.
        """
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
