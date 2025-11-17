"""Authentication and user management service layer."""

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
from customers.services import CustomerService
from customers.models import Customer


logger = logging.getLogger(__name__)


class AuthService:
    """
    Service class handling user authentication and account management.

    Provides methods for user registration, email verification, password management,
    and account updates including email and username changes.
    """

    @staticmethod
    def validate_registration_data(
        username: str, email: str, password: str, password_confirm: str
        ) -> Optional[str]:
        """
        Validate user registration data.

        Args:
            username: Desired username for the new account.
            email: Email address for the new account.
            password: Password for the new account.
            password_confirm: Password confirmation (must match password).

        Returns:
            Error message string if validation fails, None if validation passes.
        """
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
        username: str,
        email: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
        **customer_data
    ) -> Customer:
        """
        Register a new user and create associated customer profile.

        Creates a new user account and sends a verification email.
        The operation is atomic to ensure data consistency.

        Args:
            username: Username for the new account.
            email: Email address for the new account.
            password: Password for the new account.
            first_name: First name of the user (optional).
            last_name: Last name of the user (optional).
            **customer_data: Additional customer profile data (phone, country, city, address).

        Returns:
            Created Customer instance.

        Raises:
            Exception: If customer creation fails (transaction will be rolled back).
        """
        customer = CustomerService.register_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            **customer_data
        )
        
        try:
            AccountEmailService.send_email_verification(customer.user)
        except Exception as exc:
            logger.warning(
                "Failed to send verification email for user %s: %s",
                customer.user.pk,
                exc
            )
        
        return customer

    @staticmethod
    def verify_email_by_token(uidb64: str, token: str) -> Tuple[bool, Optional[str], Optional[Customer]]:
        """
        Verify user's email address using a token.

        Args:
            uidb64: Base64-encoded user ID.
            token: Verification token generated for the user.

        Returns:
            Tuple of (success: bool, error: Optional[str], customer: Optional[Customer]).
            If successful, returns (True, None, Customer instance).
            If failed, returns (False, error_message, None).
        """
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
        """
        Request a password reset for a user.

        Sends a password reset email if the user exists.
        Does not reveal whether the email exists in the system.

        Args:
            email: Email address of the user requesting password reset.
        """
        try:
            user = User.objects.get(email=email)
            try:
                AccountEmailService.send_password_reset_email(user)
            except Exception as exc:
                logger.warning(
                    "Failed to send password reset email for user %s: %s",
                    user.pk,
                    exc
                )
        except User.DoesNotExist:
            pass

    @staticmethod
    def reset_password(uidb64: str, token: str, new_password: str, password_confirm: str) -> Tuple[bool, Optional[str]]:
        """
        Reset user password using a reset token.

        Args:
            uidb64: Base64-encoded user ID.
            token: Password reset token.
            new_password: New password to set.
            password_confirm: Password confirmation (must match new_password).

        Returns:
            Tuple of (success: bool, error: Optional[str]).
            If successful, returns (True, None).
            If failed, returns (False, error_message).
        """
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
        """
        Change user password (requires current password).

        Args:
            user: User instance whose password is being changed.
            old_password: Current password for verification.
            new_password: New password to set.
            password_confirm: Password confirmation (must match new_password).

        Returns:
            Tuple of (success: bool, error: Optional[str]).
            If successful, returns (True, None).
            If failed, returns (False, error_message).
        """
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
        """
        Request email address change for a user.

        Validates the new email and sends a confirmation email.
        Sets email_verified to False until the change is confirmed.

        Args:
            user: User instance requesting email change.
            new_email: New email address to set.
            password: Current password for verification.

        Returns:
            Tuple of (success: bool, error: Optional[str]).
            If successful, returns (True, None).
            If failed, returns (False, error_message).
        """
        if not new_email or not password:
            return False, "New email and password are required"
        
        if not user.check_password(password):
            return False, "Invalid password"
        
        if User.objects.filter(email=new_email).exclude(pk=user.pk).exists():
            return False, "User with this email already exists"
        
        customer = CustomerService.get_by_user(user)
        if customer:
            customer.email_verified = False
            customer.save(update_fields=['email_verified', 'updated_at'])
        
        try:
            AccountEmailService.send_email_change_confirmation(user, new_email)
        except Exception as exc:
            logger.warning(
                "Failed to send email change confirmation for user %s: %s",
                user.pk,
                exc
            )
        
        return True, None

    @staticmethod
    def confirm_email_change(token: str) -> Tuple[bool, Optional[str]]:
        """
        Confirm email address change using a confirmation token.

        Updates the user's email and sets email_verified to True.

        Args:
            token: Email change confirmation token.

        Returns:
            Tuple of (success: bool, error: Optional[str]).
            If successful, returns (True, None).
            If failed, returns (False, error_message).
        """
        try:
            payload = AccountEmailService.parse_email_change_token(token)
        except SignatureExpired:
            return False, "Confirmation link has expired"
        except BadSignature:
            return False, "Invalid confirmation link"

        user_id = payload.get('user_id')
        new_email = payload.get('new_email')

        if not user_id or not new_email:
            return False, "Invalid confirmation data"

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return False, "User not found"

        if User.objects.filter(email=new_email).exclude(pk=user.pk).exists():
            return False, "User with this email already exists"

        user.email = new_email
        user.save(update_fields=['email'])

        customer = CustomerService.get_by_user(user)
        if customer:
            CustomerService.verify_email(customer)

        return True, None

    @staticmethod
    def resend_verification_email(user: User) -> Tuple[bool, Optional[str]]:
        """
        Resend email verification to a user.

        Args:
            user: User instance to resend verification email to.

        Returns:
            Tuple of (success: bool, error: Optional[str]).
            If successful, returns (True, None).
            If failed, returns (False, error_message).
        """
        customer = CustomerService.get_by_user(user)
        if not customer:
            return False, "Customer profile not found"
        
        if customer.email_verified:
            return False, "Email already confirmed"

        try:
            AccountEmailService.send_email_verification(user)
        except Exception as exc:
            logger.warning(
                "Failed to resend verification email for user %s: %s",
                user.pk,
                exc
            )
        
        return True, None

    @staticmethod
    def request_username_change(user: User, new_username: str, password: str) -> Tuple[bool, Optional[str]]:
        """
        Request username change for a user.

        Validates the new username and sends a confirmation email.

        Args:
            user: User instance requesting username change.
            new_username: New username to set.
            password: Current password for verification.

        Returns:
            Tuple of (success: bool, error: Optional[str]).
            If successful, returns (True, None).
            If failed, returns (False, error_message).
        """
        if not new_username or not password:
            return False, "New username and password are required"

        if not user.check_password(password):
            return False, "Invalid password"

        if User.objects.filter(username=new_username).exclude(pk=user.pk).exists():
            return False, "User with this username already exists"

        try:
            AccountEmailService.send_username_change_confirmation(user, new_username)
        except Exception as exc:
            logger.warning(
                "Failed to send username change confirmation for user %s: %s",
                user.pk,
                exc
            )

        return True, None

    @staticmethod
    def confirm_username_change(token: str) -> Tuple[bool, Optional[str]]:
        """
        Confirm username change using a confirmation token.

        Args:
            token: Username change confirmation token.

        Returns:
            Tuple of (success: bool, error: Optional[str]).
            If successful, returns (True, None).
            If failed, returns (False, error_message).
        """
        try:
            payload = AccountEmailService.parse_username_change_token(token)
        except SignatureExpired:
            return False, "Confirmation link has expired"
        except BadSignature:
            return False, "Invalid confirmation link"

        user_id = payload.get('user_id')
        new_username = payload.get('new_username')

        if not user_id or not new_username:
            return False, "Invalid confirmation data"

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return False, "User not found"

        if User.objects.filter(username=new_username).exclude(pk=user.pk).exists():
            return False, "User with this username already exists"

        user.username = new_username
        user.save(update_fields=['username'])

        return True, None

    @staticmethod
    def logout_user(refresh_token: str) -> Tuple[bool, Optional[str]]:
        """
        Logout a user by blacklisting their refresh token.

        Args:
            refresh_token: JWT refresh token to blacklist.

        Returns:
            Tuple of (success: bool, error: Optional[str]).
            If successful, returns (True, None).
            If failed, returns (False, error_message).
        """
        try:
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return True, None
        except Exception as e:
            return False, str(e)

