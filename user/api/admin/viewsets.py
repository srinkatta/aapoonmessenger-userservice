import csv
import logging

from django.http import HttpResponse
from django.contrib.auth import login
from django.contrib.auth.hashers import check_password

from rest_framework import status, viewsets, permissions
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import OpenApiParameter, extend_schema

from user import models as user_models
from user.utils import make_request
from user.user_delete import UserDelete
from user.api import serializers as user_serializers
from user.api.admin import serializers as admin_serializers
from user.api.admin.filters import UserFilter
from user_service import settings


class UserListDetailsAPI(APIView, PageNumberPagination):
    """
    Users List & Detail view
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
        pk = request.query_params.get("id", None)
        if pk:
            queryset = user_models.User.objects.get(id=pk)
            serializer = admin_serializers.UserDetailSerializer(queryset)
            return Response(serializer.data, status=status.HTTP_200_OK)
        queryset = user_models.User.objects.all().order_by("-id")
        paginated_qs = self.paginate_queryset(queryset, request)
        serializer = self.serializer_class(paginated_qs, many=True)

        return self.get_paginated_response(serializer.data)


class UserVerificationSettingAPI(APIView, PageNumberPagination):
    """
    User Kyc Settings List, Detail & Update View
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


class AdminUserFilters(APIView, PageNumberPagination):
    """
    API to return Users list based on filters
    """

    serializer_class = admin_serializers.UserFilterSerializer
    permission_classes = (permissions.IsAuthenticated,)
    page_size = 100

    def get(self, request):
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
    Delete User in Web & XMPP server
    """

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = admin_serializers.UserListSerializer

    def post(self, request, *args, **kwargs):
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
    """

    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):

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
    queryset = user_models.AppInfo.objects.all()


class AppPolicyViewSet(viewsets.ModelViewSet):
    """
    Viewsets to manage and maintain App Policies
    """

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = user_serializers.AppPolicySerializer
    queryset = user_models.Languages.objects.all()


class DeletedUserAPI(APIView, PageNumberPagination):
    """
    List & delete Deleted Users records
    """

    serializer_class = admin_serializers.DeletedUserSerializer
    permission_classes = (AllowAny,)
    page_size = 100

    def get(self, request, *args, **kwargs):
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
    authentication_classes = [JWTAuthentication]
    permission_classes = (AllowAny,)
    serializer_class = admin_serializers.CreateSuperUserSerializer

    def post(self, request):
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
    authentication_classes = [JWTAuthentication]
    permission_classes = (AllowAny,)
    serializer_class = admin_serializers.SuperUserLoginSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]
        user = user_models.User.objects.filter(username=username).first()
        refresh = RefreshToken.for_user(user)
        refresh_token = str(refresh)
        access_token = str(refresh.access_token)

        validate_password = check_password(password, user.password)
        if validate_password and user is not None:
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
