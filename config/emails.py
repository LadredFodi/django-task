from __future__ import annotations

from typing import Any, Dict
from urllib.parse import urljoin

from config import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


ACCOUNT_ACTION_MAX_AGE = getattr(settings, "ACCOUNT_ACTION_MAX_AGE", 60 * 60 * 24)  # 24 hours by default


class AccountEmailService:
    """
    Helper class responsible for sending transactional emails related to account management
    (registration confirmation, password recovery, profile updates, etc.).
    """

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
        verification_link = cls._build_absolute_url(
            reverse("verify_email", kwargs={"uidb64": uid, "token": token})
        )

        subject = "Подтверждение регистрации"
        message = (
            f"Здравствуйте, {user.first_name or user.username}!\n\n"
            f"Для завершения регистрации подтвердите адрес электронной почты, перейдя по ссылке:\n"
            f"{verification_link}\n\n"
            "Если вы не регистрировались на нашем сервисе, просто проигнорируйте это письмо."
        )

        cls._send_mail(subject, message, user.email)
        return verification_link

    @classmethod
    def send_password_reset_email(cls, user: User) -> str:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_link = cls._build_absolute_url(
            reverse("reset_password", kwargs={"uidb64": uid, "token": token})
        )

        subject = "Восстановление пароля"
        message = (
            f"Здравствуйте, {user.first_name or user.username}!\n\n"
            "Вы запросили сброс пароля. Для установки нового пароля перейдите по ссылке:\n"
            f"{reset_link}\n\n"
            "Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо."
        )

        cls._send_mail(subject, message, user.email)
        return reset_link

    @classmethod
    def send_email_change_confirmation(cls, user: User, new_email: str) -> str:
        payload: Dict[str, Any] = {"user_id": user.pk, "new_email": new_email}
        token = signing.dumps(payload, salt=cls.EMAIL_CHANGE_SALT)
        confirmation_link = cls._build_absolute_url(
            reverse("confirm_email_change", kwargs={"token": token})
        )

        subject = "Подтверждение смены адреса электронной почты"
        message = (
            f"Здравствуйте, {user.first_name or user.username}!\n\n"
            "Вы запросили смену адреса электронной почты. Для подтверждения перейдите по ссылке:\n"
            f"{confirmation_link}\n\n"
            "Если вы не запрашивали смену адреса, просто проигнорируйте это письмо."
        )

        cls._send_mail(subject, message, new_email)
        return token

    @classmethod
    def parse_email_change_token(cls, token: str) -> Dict[str, Any]:
        return signing.loads(
            token,
            salt=cls.EMAIL_CHANGE_SALT,
            max_age=ACCOUNT_ACTION_MAX_AGE,
        )

    @classmethod
    def send_username_change_confirmation(cls, user: User, new_username: str) -> str:
        payload: Dict[str, Any] = {"user_id": user.pk, "new_username": new_username}
        token = signing.dumps(payload, salt=cls.USERNAME_CHANGE_SALT)
        confirmation_link = cls._build_absolute_url(
            reverse("confirm_username_change", kwargs={"token": token})
        )

        subject = "Подтверждение смены логина"
        message = (
            f"Здравствуйте, {user.first_name or user.username}!\n\n"
            f"Вы запросили смену логина на «{new_username}». "
            "Для подтверждения перейдите по ссылке:\n"
            f"{confirmation_link}\n\n"
            "Если вы не отправляли этот запрос, просто проигнорируйте письмо."
        )

        cls._send_mail(subject, message, user.email)
        return token

    @classmethod
    def parse_username_change_token(cls, token: str) -> Dict[str, Any]:
        return signing.loads(
            token,
            salt=cls.USERNAME_CHANGE_SALT,
            max_age=ACCOUNT_ACTION_MAX_AGE,
        )

