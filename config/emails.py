from __future__ import annotations

from typing import Any, Dict
from urllib.parse import urljoin

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from config import settings


class AccountEmailService:

    EMAIL_CHANGE_SALT = "account/email-change"
    USERNAME_CHANGE_SALT = "account/username-change"

    @staticmethod
    def _build_absolute_url(path: str) -> str:
        base = settings.SITE_URL.rstrip("/")
        return urljoin(f"{base}/", path.lstrip("/"))

    @staticmethod
    def _send_mail(subject: str, message: str, recipient: str) -> None:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            fail_silently=False,
        )

    @classmethod
    def send_email_verification(cls, user: User) -> str:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        verification_link = cls._build_absolute_url(reverse("verify_email", kwargs={"uidb64": uid, "token": token}))

        subject = "Email verification"
        message = (
            f"Hello, {user.first_name or user.username}!\n\n"
            f"To complete registration, please confirm your email address by clicking the link:\n"
            f"{verification_link}\n\n"
            "If you did not register on our service, please ignore this email."
        )

        cls._send_mail(subject, message, user.email)
        return verification_link

    @classmethod
    def send_password_reset_email(cls, user: User) -> str:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_link = cls._build_absolute_url(reverse("reset_password", kwargs={"uidb64": uid, "token": token}))

        subject = "Password reset"
        message = (
            f"Hello, {user.first_name or user.username}!\n\n"
            "You requested a password reset. To set a new password, please click the link:\n"
            f"{reset_link}\n\n"
            "If you did not request a password reset, please ignore this email."
        )

        cls._send_mail(subject, message, user.email)
        return reset_link

    @classmethod
    def send_email_change_confirmation(cls, user: User, new_email: str) -> str:
        payload: Dict[str, Any] = {"user_id": user.pk, "new_email": new_email}
        token = signing.dumps(payload, salt=cls.EMAIL_CHANGE_SALT)
        confirmation_link = cls._build_absolute_url(reverse("confirm_email_change", kwargs={"token": token}))

        subject = "Email change confirmation"
        message = (
            f"Hello, {user.first_name or user.username}!\n\n"
            "You requested an email change. To confirm the change, please click the link:\n"
            f"{confirmation_link}\n\n"
            "If you did not request an email change, please ignore this email."
        )

        cls._send_mail(subject, message, new_email)
        return token

    @classmethod
    def parse_email_change_token(cls, token: str) -> Dict[str, Any]:
        return signing.loads(
            token,
            salt=cls.EMAIL_CHANGE_SALT,
            max_age=settings.ACCOUNT_ACTION_MAX_AGE,
        )

    @classmethod
    def send_username_change_confirmation(cls, user: User, new_username: str) -> str:
        payload: Dict[str, Any] = {"user_id": user.pk, "new_username": new_username}
        token = signing.dumps(payload, salt=cls.USERNAME_CHANGE_SALT)
        confirmation_link = cls._build_absolute_url(reverse("confirm_username_change", kwargs={"token": token}))

        subject = "Username change confirmation"
        message = (
            f"Hello, {user.first_name or user.username}!\n\n"
            f"You requested a username change to «{new_username}». "
            "To confirm the change, please click the link:\n"
            f"{confirmation_link}\n\n"
            "If you did not request a username change, please ignore this email."
        )

        cls._send_mail(subject, message, user.email)
        return token

    @classmethod
    def parse_username_change_token(cls, token: str) -> Dict[str, Any]:
        return signing.loads(
            token,
            salt=cls.USERNAME_CHANGE_SALT,
            max_age=settings.ACCOUNT_ACTION_MAX_AGE,
        )
