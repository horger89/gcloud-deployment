from rest_framework.decorators import api_view, permission_classes
from .serializers import SignUpSerializer, UserSerializer
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from datetime import datetime, timedelta
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


# Create your views here.


@swagger_auto_schema(method='POST', request_body=SignUpSerializer)
@api_view(["POST"])
def register(request):
    """Register User"""
    data = request.data

    user = SignUpSerializer(data=data)

    if user.is_valid():

        if not User.objects.filter(username=data["email"]).exists():

            user = User.objects.create(
                first_name=data["first_name"],
                last_name=data["last_name"],
                email=data["email"],
                username=data["email"],
                password=make_password(data["password"]),
            )

            return Response({"details": "User Registered"},
                            status=status.HTTP_201_CREATED
                            )

        else:
            return Response({"error": "User already exists"},
                            status=status.HTTP_400_BAD_REQUEST
                            )

    else:
        return Response(user.errors)


@swagger_auto_schema(method='GET')
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_user(request):
    """Get Current User"""
    user = UserSerializer(request.user, many=False)

    return Response(user.data)


@swagger_auto_schema(
    method='PUT',
    request_body=openapi.Schema(
        type='object',
        properties={
            "first_name": openapi.Schema(type='string'),
            "last_name": openapi.Schema(type='string'),
            "email": openapi.Schema(type='string'),
            "username": openapi.Schema(type='string'),
            "password": openapi.Schema(type='string'),

        },
        required=["first_name", "last_name", "email", "username"]
    )
)
@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_user(request):
    """Update User Details"""
    user = request.user
    data = request.data

    user.first_name = data["first_name"]
    user.last_name = data["last_name"]
    user.username = data["username"]
    user.email = data["email"]

    if data["password"] != "":
        user.password = make_password(data["password"])

    user.save()

    serializer = UserSerializer(user, many=False)

    return Response(serializer.data)


@swagger_auto_schema(
    method='POST',
    request_body=openapi.Schema(
        type='object',
        properties={
            'email': openapi.Schema(type='string'),
        },
        required=['email']
    )
)
@api_view(["POST"])
def forgot_password(request):
    """Forgot Password EndPoint"""
    data = request.data

    user = get_object_or_404(User, email=data["email"])

    token = get_random_string(length=40)
    expire_date = timezone.now() + timedelta(minutes=30)

    user.profile.reset_password_token = token
    user.profile.reset_password_expire = expire_date

    user.profile.save()

    body = "Your password reset token is: {token}".format(token=token)

    send_mail(
        "Requested Password Reset Link",
        body,
        "noreply@ecommerceapi.com",
        [data["email"]]
    )

    return Response(
        {"details": "Password reset email sent to: {email}".format(
            email=data["email"]
            )}
        )


@swagger_auto_schema(
    method="POST",
    request_body=openapi.Schema(
        type='object',
        properties={
            "password": openapi.Schema(type='string'),
            "confirmPassword": openapi.Schema(type='string')
        },
        required=["password", "confirmPassword"]
    )
)
@api_view(["POST"])
def reset_password(request, token):
    """Reset User Password"""
    data = request.data

    user = get_object_or_404(User, profile__reset_password_token=token)

    if (
        user.profile.reset_password_expire.replace(tzinfo=None) <
        datetime.now()
         ):
        return Response({"error": "Token is expired"},
                        status=status.HTTP_400_BAD_REQUEST
                        )

    if data["password"] != data["confirmPassword"]:
        return Response({"error": "Passwords has to match"},
                        status=status.HTTP_400_BAD_REQUEST
                        )

    user.password = make_password(data["password"])
    user.profile.reset_password_token = ""
    user.profile.reset_password_expire = None

    user.profile.save()
    user.save()

    return Response({"details": "Password is now updated"})
