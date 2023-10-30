import csv
import logging

from django.contrib.auth import login
from django.contrib.auth.hashers import check_password
from django.http import HttpResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from user import models as user_models
from user.api import serializers as user_serializers
from user.api.admin import serializers as admin_serializers
from user.api.admin.filters import UserFilter
from user.user_delete import UserDelete
from user.utils import GenericPagination, make_request
from user_service import settings

logging = logging.getLogger(__name__)


class UserListDetailsAPI(APIView, GenericPagination):
    """
    Users List & Detail view.

    This view provides functionality to retrieve a list of users and their details. Users can be filtered by their ID.

    Query Parameters:
    - id (int, optional): Filter users by ID.

    Returns:
    - Response: A paginated response containing a list of users with details.
    """

    page_size = 100
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = admin_serializers.UserListSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="id",
                description="Retrieve User details with id",
                required=False,
                type=int,
            )
        ]
    )
    def get(self, request):
        """
        Get a list of users.

        This method retrieves a paginated list of all users or filters users based on their ID.

        Returns:
        - Response: A paginated response containing a list of users with details.
        """
        pk = request.query_params.get("id", None)
        if pk:
            queryset = user_models.User.objects.get(id=pk)
            serializer = admin_serializers.UserDetailSerializer(queryset)
            return Response(serializer.data, status=status.HTTP_200_OK)
        queryset = user_models.User.objects.all().order_by("-id")
        paginated_qs = self.paginate_queryset(queryset, request)
        serializer = self.serializer_class(paginated_qs, many=True)

        return self.get_paginated_response(serializer.data)


class UserVerificationSettingAPI(APIView, GenericPagination):
    """
    User KYC Settings List, Detail & Update View.

    This view allows users to manage and retrieve their KYC verification settings.

    Query Parameters:
    - id (int, optional): Filter user KYC settings by ID.

    Returns:
    - Response: A paginated response containing a list of user KYC settings or details.

    Request Data (for PUT method):
    - UserVerificationUpdateSerializer: Serializer for updating user KYC settings.
    """

    page_size = 100
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = admin_serializers.UserVerificationSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="id",
                description="User Verify Settings with id",
                required=False,
                type=int,
            )
        ]
    )
    def get(self, request):
        """
        Get a list of user KYC settings or retrieve details for a specific user.

        This method retrieves a paginated list of all user KYC settings or details for a specific user based on the ID.

        Returns:
        - Response: A paginated response containing a list of user KYC settings or details.
        """
        pk = request.query_params.get("id", None)
        if pk:
            queryset = user_models.UserVerificationSetting.objects.get(id=pk)
            serializer = admin_serializers.UserVerificationDetailsSerializer(queryset)
            return Response(serializer.data, status=status.HTTP_200_OK)
        queryset = user_models.UserVerificationSetting.objects.all().order_by("-id")
        pagination = self.paginate_queryset(queryset, request)
        serializer = self.serializer_class(pagination, many=True)
        return self.get_paginated_response(serializer.data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="id",
                description="User Verify Settings with user id",
                required=True,
                type=int,
            )
        ]
    )
    def put(self, request):
        """
        Update user KYC settings.

        This method updates the KYC verification settings for a specific user based on the user ID.

        Returns:
        - Response: Updated user KYC settings data or error details.
        """
        pk = request.query_params.get("id", None)
        if pk:
            try:
                user_settings = user_models.UserVerificationSetting.objects.get(user=pk)
            except user_models.UserVerificationSetting.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)

            serializer = admin_serializers.UserVerificationUpdateSerializer(
                user_settings, data=request.data
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminUserFilters(APIView, GenericPagination):
    """
    API to return a paginated list of users based on filters.

    This view allows administrators to retrieve a paginated list of users based on various filters.

    Query Parameters:
    - kyc_verified (bool, optional): Filter users by KYC verification status.

    Returns:
    - Response: A paginated response containing a list of filtered users with details.
    """

    serializer_class = admin_serializers.UserFilterSerializer
    permission_classes = (permissions.IsAuthenticated,)
    page_size = 100

    def get(self, request):
        """
        Get a paginated list of users based on filters.

        This method retrieves a paginated list of users based on various filters, including KYC verification status.

        Returns:
        - Response: A paginated response containing a list of filtered users with details.
        """
        kyc_verified = request.GET.get("kyc_verified", None)
        if kyc_verified:
            user_settings = user_models.UserVerificationSetting.objects.filter(
                kyc_done=kyc_verified
            ).order_by("-id")
            kyc_verified = user_settings.values_list("user", flat=True)
            queryset = user_models.User.objects.filter(id__in=kyc_verified).order_by(
                "-id"
            )
        else:
            queryset = user_models.User.objects.all().order_by("-id")
        filterset = UserFilter(request.GET, queryset=queryset)
        paginated_qs = self.paginate_queryset(filterset.qs, request)
        serializer = self.serializer_class(paginated_qs, many=True)
        return self.get_paginated_response(serializer.data)


class UserDeleteAdminAPI(APIView):
    """
    API to delete a user from the web and XMPP server.

    This view allows administrators to delete a user's account from both the web and XMPP server.

    Permissions:
    - IsAuthenticated: Only authenticated users (administrators) can access this API.

    Request Payload:
    - user_id (int): ID of the user to be deleted.

    Returns:
    - Response: A response indicating the status of the deletion process.
    """

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = admin_serializers.UserListSerializer

    def post(self, request, *args, **kwargs):
        """
        Delete a user from the web and XMPP server.

        This method handles the deletion of a user's account from both the web and XMPP server.

        Request Payload:
        - user_id (int): ID of the user to be deleted.

        Returns:
        - Response: A response indicating the status of the deletion process.
        """
        user_id = request.data.get("user_id", None)
        try:
            UserDelete().save_delete_record(user_id)
        except Exception as Exc:
            return Response(
                {"detail": "User doesn't exists"}, status=status.HTTP_400_BAD_REQUEST
            )
        user = user_models.User.objects.filter(id=user_id).first()
        self.xmpp_unregister(user)
        user.delete()
        return Response(
            {"detail": "User deleted successfully"}, status=status.HTTP_200_OK
        )

    def xmpp_unregister(self, user):
        """
        Unregister a user from the XMPP server.

        This method sends a request to the XMPP server to unregister a user.

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
            logging.info("User successfully unregistered at websocket server")
        except Exception as e:
            logging.exception("Error unregistering user at websocket server %s" % e)


class UsersExportAPI(APIView):
    """
    Export user information to a CSV file.

    This view allows administrators to export user information to a CSV file. The exported file
    will contain fields such as user ID, name, email, phone number, KYC verification status,
    phone verification status, user type, and date joined.

    Permissions:
    - IsAuthenticated: Only authenticated users (administrators) can access this API.

    Returns:
    - HttpResponse: A CSV file containing user information.
    """

    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        """
        Export user information to a CSV file.

        This method generates a CSV file containing user information, including fields such as
        user ID, name, email, phone number, KYC verification status, phone verification status,
        user type, and date joined.

        Returns:
        - HttpResponse: A CSV file containing user information.
        """
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="aapoon-users.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "ID",
                "Name",
                "Email",
                "Phone Number",
                "KYC Verified",
                "Phone Verified",
                "User Type",
                "Date Joined",
            ]
        )

        users = user_models.User.objects.all()
        # Write user data to CSV rows
        for user in users:
            kyc_verified = user.settings.get().kyc_done
            writer.writerow(
                [
                    user.id,
                    user.name,
                    user.email,
                    user.phone_number,
                    kyc_verified,
                    user.phone_number_verified,
                    user.user_type,
                    user.date_joined,
                ]
            )

        return response


class AppInfoViewSet(viewsets.ModelViewSet):
    """
    Viewsets to manage and maintain application versioning.
    """

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = user_serializers.AppInfoSerializer

    def get_queryset(self):
        return user_models.AppInfo.objects.all()


class AppPolicyViewSet(viewsets.ModelViewSet):
    """
    Viewsets to manage and maintain App Policies
    """

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = user_serializers.AppPolicySerializer

    def get_queryset(self):
        return user_models.Languages.objects.all()


class DeletedUserAPI(APIView, GenericPagination):
    """
    List and delete Deleted Users records.

    This API view provides endpoints to list and delete records of previously deleted users.
    Administrators can use these endpoints to retrieve a paginated list of deleted user records
    and to permanently delete a specific deleted user record.

    Permissions:
    - AllowAny: All users, including unauthenticated users, are allowed to access this view.

    Returns:
    - Response: JSON response containing deleted user records or deletion status.
    """

    serializer_class = admin_serializers.DeletedUserSerializer
    permission_classes = (AllowAny,)
    page_size = 100

    def get(self, request, *args, **kwargs):
        """
        Retrieve a paginated list of deleted user records.

        This method retrieves a paginated list of deleted user records and returns it as a JSON response.

        Returns:
        - Response: JSON response containing a paginated list of deleted user records.
        """
        queryset = user_models.DeletedUser.objects.all().order_by("-id")
        paginated_qs = self.paginate_queryset(queryset, request)
        serializer = self.serializer_class(paginated_qs, many=True)
        return self.get_paginated_response(serializer.data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="id",
                description="User delete with id specific",
                required=True,
                type=int,
            )
        ]
    )
    def delete(self, request, *args, **kwargs):
        """
        Delete a specific deleted user record.

        This method permanently deletes a specific deleted user record identified by its ID.

        Returns:
        - Response: JSON response indicating the success or failure of the deletion operation.
        """
        user_id = request.query_params.get("id", None)
        try:
            deleted_user = user_models.DeletedUser.objects.filter(user=user_id).first()
            deleted_user.delete()
        except Exception as exc:
            return Response(
                {"detail": "Error while deleting deleted Users"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"message": "User deleted successfully"}, status=status.HTTP_200_OK
        )


class AdminPanelRegisterAPI(APIView):
    """
    API for registering a new superuser through the admin panel.

    This API view allows administrators to register a new superuser through the admin panel.
    The superuser can be created with the provided phone number, country code, username,
    email, and password.

    Authentication:
    - JWTAuthentication: Administrators must be authenticated using JWT to access this view.

    Permissions:
    - AllowAny: All users, including unauthenticated users, are allowed to access this view.

    Returns:
    - Response: JSON response indicating the success or failure of the superuser creation.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = (AllowAny,)
    serializer_class = admin_serializers.CreateSuperUserSerializer

    def post(self, request):
        """
        Register a new superuser through the admin panel.

        This method registers a new superuser with the provided details and returns a JSON response
        indicating the success of the superuser creation.

        Returns:
        - Response: JSON response indicating the success or failure of the superuser creation.
        """
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone_number"]

        user = user_models.User.objects.create_superuser(
            phone_number=serializer.validated_data["phone_number"],
            country_code=serializer.validated_data["country_code"],
            username=serializer.validated_data["username"],
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )

        return Response(
            {"message": "Superuser created successfully."},
            status=status.HTTP_201_CREATED,
        )


class AdminPanelLoginAPI(APIView):
    """
    API for logging in as a superuser through the admin panel.

    This API view allows administrators to log in as a superuser through the admin panel.
    Administrators must provide their username and password to obtain access and refresh tokens.

    Authentication:
    - JWTAuthentication: Administrators must be authenticated using JWT to access this view.

    Permissions:
    - AllowAny: All users, including unauthenticated users, are allowed to access this view.

    Returns:
    - Response: JSON response containing access and refresh tokens upon successful login.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = (AllowAny,)
    serializer_class = admin_serializers.SuperUserLoginSerializer

    def post(self, request):
        """
        Log in as a superuser through the admin panel.

        This method allows administrators to log in as a superuser by providing their username and password.
        Upon successful login, the method returns a JSON response containing access and refresh tokens.

        Returns:
        - Response: JSON response containing access and refresh tokens upon successful login.
        """
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]
        user = user_models.User.objects.filter(username=username).first()

        # Validate password and generate tokens
        if user is not None and check_password(password, user.password):
            refresh = RefreshToken.for_user(user)
            refresh_token = str(refresh)
            access_token = str(refresh.access_token)

            login(request, user, backend="django.contrib.auth.backends.ModelBackend")

            result = {
                "access": access_token,
                "refresh": refresh_token,
            }
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(
                {"detail": "Wrong credentials."}, status=status.HTTP_400_BAD_REQUEST
            )
