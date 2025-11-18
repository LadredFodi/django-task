from __future__ import annotations

import logging
from typing import Optional, Tuple

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.signing import BadSignature, SignatureExpired
from django.db import transaction
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework_simplejwt.tokens import RefreshToken

from config.emails import AccountEmailService
from customers.models import Customer
from customers.services import CustomerService

logger = logging.getLogger(__name__)


class AuthService:

    @staticmethod
    def validate_registration_data(username: str, email: str, password: str, password_confirm: str) -> Optional[str]:

        if not username or not email or not password:
            return "Missing username, email or password"

        if password != password_confirm:
            return "Passwords do not match"

        if User.objects.filter(username=username).exists():
            return "User with this username already exists"

        if User.objects.filter(email=email).exists():
            return "User with this email already exists"

        return None

    @staticmethod
    @transaction.atomic
    def register_user(
        username: str, email: str, password: str, first_name: str = "", last_name: str = "", **customer_data
    ) -> Customer:

        customer = CustomerService.register_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            **customer_data,
        )

        try:
            AccountEmailService.send_email_verification(customer.user)
        except Exception as exc:
            logger.warning("Failed to send verification email for user %s: %s", customer.user.pk, exc)

        return customer

    @staticmethod
    def verify_email_by_token(uidb64: str, token: str) -> Tuple[bool, Optional[str], Optional[Customer]]:

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return False, "Invalid confirmation link", None

        if not default_token_generator.check_token(user, token):
            return False, "Invalid or expired token", None

        customer = CustomerService.get_by_user(user)
        if not customer:
            return False, "Customer profile not found", None

        CustomerService.verify_email(customer)
        return True, None, customer

    @staticmethod
    def request_password_reset(email: str) -> None:

        try:
            user = User.objects.get(email=email)
            try:
                AccountEmailService.send_password_reset_email(user)
            except Exception as exc:
                logger.warning("Failed to send password reset email for user %s: %s", user.pk, exc)
        except User.DoesNotExist:
            pass

    @staticmethod
    def reset_password(uidb64: str, token: str, new_password: str, password_confirm: str) -> Tuple[bool, Optional[str]]:

        if not new_password or not password_confirm:
            return False, "New password and confirmation are required"

        if new_password != password_confirm:
            return False, "Passwords do not match"

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return False, "Invalid password reset link"

        if not default_token_generator.check_token(user, token):
            return False, "Invalid or expired token"

        user.set_password(new_password)
        user.save()

        return True, None

    @staticmethod
    def change_password(
        user: User, old_password: str, new_password: str, password_confirm: str
    ) -> Tuple[bool, Optional[str]]:

        if not old_password or not new_password or not password_confirm:
            return False, "Old password, new password and confirmation are required"

        if new_password != password_confirm:
            return False, "New passwords do not match"

        if not user.check_password(old_password):
            return False, "Invalid old password"

        user.set_password(new_password)
        user.save()

        return True, None

    @staticmethod
    def request_email_change(user: User, new_email: str, password: str) -> Tuple[bool, Optional[str]]:

        if not new_email or not password:
            return False, "New email and password are required"

        if not user.check_password(password):
            return False, "Invalid password"

        if User.objects.filter(email=new_email).exclude(pk=user.pk).exists():
            return False, "User with this email already exists"

        customer = CustomerService.get_by_user(user)
        if customer:
            customer.email_verified = False
            customer.save(update_fields=["email_verified", "updated_at"])

        try:
            AccountEmailService.send_email_change_confirmation(user, new_email)
        except Exception as exc:
            logger.warning("Failed to send email change confirmation for user %s: %s", user.pk, exc)

        return True, None

    @staticmethod
    def confirm_email_change(token: str) -> Tuple[bool, Optional[str]]:

        try:
            payload = AccountEmailService.parse_email_change_token(token)
        except SignatureExpired:
            return False, "Confirmation link has expired"
        except BadSignature:
            return False, "Invalid confirmation link"

        user_id = payload.get("user_id")
        new_email = payload.get("new_email")

        if not user_id or not new_email:
            return False, "Invalid confirmation data"

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return False, "User not found"

        if User.objects.filter(email=new_email).exclude(pk=user.pk).exists():
            return False, "User with this email already exists"

        user.email = new_email
        user.save(update_fields=["email"])

        customer = CustomerService.get_by_user(user)
        if customer:
            CustomerService.verify_email(customer)

        return True, None

    @staticmethod
    def resend_verification_email(user: User) -> Tuple[bool, Optional[str]]:

        customer = CustomerService.get_by_user(user)
        if not customer:
            return False, "Customer profile not found"

        if customer.email_verified:
            return False, "Email already confirmed"

        try:
            AccountEmailService.send_email_verification(user)
        except Exception as exc:
            logger.warning("Failed to resend verification email for user %s: %s", user.pk, exc)

        return True, None

    @staticmethod
    def request_username_change(user: User, new_username: str, password: str) -> Tuple[bool, Optional[str]]:

        if not new_username or not password:
            return False, "New username and password are required"

        if not user.check_password(password):
            return False, "Invalid password"

        if User.objects.filter(username=new_username).exclude(pk=user.pk).exists():
            return False, "User with this username already exists"

        try:
            AccountEmailService.send_username_change_confirmation(user, new_username)
        except Exception as exc:
            logger.warning("Failed to send username change confirmation for user %s: %s", user.pk, exc)

        return True, None

    @staticmethod
    def confirm_username_change(token: str) -> Tuple[bool, Optional[str]]:

        try:
            payload = AccountEmailService.parse_username_change_token(token)
        except SignatureExpired:
            return False, "Confirmation link has expired"
        except BadSignature:
            return False, "Invalid confirmation link"

        user_id = payload.get("user_id")
        new_username = payload.get("new_username")

        if not user_id or not new_username:
            return False, "Invalid confirmation data"

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return False, "User not found"

        if User.objects.filter(username=new_username).exclude(pk=user.pk).exists():
            return False, "User with this username already exists"

        user.username = new_username
        user.save(update_fields=["username"])

        return True, None

    @staticmethod
    def logout_user(refresh_token: str) -> Tuple[bool, Optional[str]]:

        try:
            if refresh_token:
                token = RefreshToken(refresh_token)  # type: ignore[arg-type]
                token.blacklist()
            return True, None
        except Exception as e:
            return False, str(e)
