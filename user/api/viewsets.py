from rest_framework import status, viewsets, permissions
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from user.api.serializers import (
    UserLoginSerializer,
    RegisterSerializer, UserLogsSerializer, UserFeedbackSerializer, UserInviteSerializer, UserDeviceSerializer,
)
from user.models import UserLogs, UserFeedback, UserInvite, UserDevice


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
    queryset = UserLogs.objects.all()
    serializer_class = UserLogsSerializer
    permission_classes = (permissions.IsAuthenticated,)


class UserFeedbackViewSet(viewsets.ModelViewSet):
    """
    Viewset to create, list, update and delete UserFeedback.
    """
    queryset = UserFeedback.objects.all()
    serializer_class = UserFeedbackSerializer
    permission_classes = (permissions.IsAuthenticated,)


class UserInviteViewSet(viewsets.ModelViewSet):
    """
    Viewset to create, list, update and delete UserInvite.
    """
    queryset = UserInvite.objects.all()
    serializer_class = UserInviteSerializer
    permission_classes = (permissions.IsAuthenticated,)


class UserDeviceViewSet(viewsets.ModelViewSet):
    """
    Viewset to create, list, update and delete UserDevice.
    """
    queryset = UserDevice.objects.all()
    serializer_class = UserDeviceSerializer
    permission_classes = (permissions.IsAuthenticated,)
