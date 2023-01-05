from rest_framework import status, viewsets, permissions
from rest_framework.generics import get_object_or_404
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
)
from user.models import UserLog, UserFeedback, UserInvite, UserDevice, UserProfile, User


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
        return get_object_or_404(UserProfile.objects.all(), user=self.request.user)

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
