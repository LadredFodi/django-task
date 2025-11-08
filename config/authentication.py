import logging

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.signing import BadSignature, SignatureExpired
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from rest_framework_simplejwt.tokens import RefreshToken

from config.emails import AccountEmailService
from customers.services import CustomerService


logger = logging.getLogger(__name__)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        password_confirm = request.data.get('password_confirm')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        
        if not username or not email or not password:
            return Response(
                {'error': 'Missing username, email or password'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if password != password_confirm:
            return Response(
                {'error': 'Passwords do not match'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if User.objects.filter(username=username).exists():
            return Response(
                {'error': 'User with this username already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if User.objects.filter(email=email).exists():
            return Response(
                {'error': 'User with this email already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        customer = CustomerService.register_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=request.data.get('phone', ''),
            country=request.data.get('country', ''),
            city=request.data.get('city', ''),
            address=request.data.get('address', '')
        )
        
        try:
            AccountEmailService.send_email_verification(customer.user)
        except Exception as exc:
            logger.warning("Failed to send verification email for user %s: %s", customer.user.pk, exc)
        
        return Response({
            'message': 'Registration successful. Check your email for confirmation.',
            'user': {
                'id': customer.user.id,
                'username': customer.user.username,
                'email': customer.user.email,
            }
        }, status=status.HTTP_201_CREATED)


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {'error': 'Invalid confirmation link'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not default_token_generator.check_token(user, token):
            return Response(
                {'error': 'Invalid or expired token'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        customer = CustomerService.get_by_user(user)
        if not customer:
            return Response(
                {'error': 'Customer profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        CustomerService.verify_email(customer)
        
        return Response({
            'message': 'Email successfully confirmed',
        }, status=status.HTTP_200_OK)


class RequestPasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        
        if not email:
            return Response(
                {'error': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=email)
            try:
                AccountEmailService.send_password_reset_email(user)
            except Exception as exc:
                logger.warning("Failed to send password reset email for user %s: %s", user.pk, exc)
        except User.DoesNotExist:
            pass
        
        return Response({
            'message': 'If the specified email exists, a letter with a link for password reset has been sent to it.',
        }, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, uidb64, token):
        new_password = request.data.get('new_password')
        password_confirm = request.data.get('password_confirm')
        
        if not new_password or not password_confirm:
            return Response(
                {'error': 'New password and confirmation are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if new_password != password_confirm:
            return Response(
                {'error': 'Passwords do not match'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {'error': 'Invalid password reset link'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not default_token_generator.check_token(user, token):
            return Response(
                {'error': 'Invalid or expired token'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(new_password)
        user.save()
        
        return Response({
            'message': 'Password successfully changed',
        }, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        password_confirm = request.data.get('password_confirm')
        
        if not old_password or not new_password or not password_confirm:
            return Response(
                {'error': 'Old password, new password and confirmation are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if new_password != password_confirm:
            return Response(
                {'error': 'New passwords do not match'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = request.user
        
        if not user.check_password(old_password):
            return Response(
                {'error': 'Invalid old password'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(new_password)
        user.save()
        
        return Response({
            'message': 'Password successfully changed',
        }, status=status.HTTP_200_OK)


class ChangeEmailView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        new_email = request.data.get('new_email')
        password = request.data.get('password')
        
        if not new_email or not password:
            return Response(
                {'error': 'New email and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = request.user
        
        if not user.check_password(password):
            return Response(
                {'error': 'Invalid password'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if User.objects.filter(email=new_email).exclude(pk=user.pk).exists():
            return Response(
                {'error': 'User with this email already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        customer = CustomerService.get_by_user(user)
        if customer:
            customer.email_verified = False
            customer.save(update_fields=['email_verified', 'updated_at'])
        
        try:
            AccountEmailService.send_email_change_confirmation(user, new_email)
        except Exception as exc:
            logger.warning("Failed to send email change confirmation for user %s: %s", user.pk, exc)
        
        return Response({
            'message': 'Email change request sent. Check your new email for confirmation.',
        }, status=status.HTTP_200_OK)


class ResendVerificationEmailView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        
        customer = CustomerService.get_by_user(user)
        if not customer:
            return Response(
                {'error': 'Customer profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if customer.email_verified:
            return Response(
                {'message': 'Email already confirmed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            AccountEmailService.send_email_verification(user)
        except Exception as exc:
            logger.warning("Failed to resend verification email for user %s: %s", user.pk, exc)
        
        return Response({
            'message': 'Email confirmation letter has been sent',
        }, status=status.HTTP_200_OK)


class ChangeUsernameView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        new_username = request.data.get('new_username')
        password = request.data.get('password')

        if not new_username or not password:
            return Response(
                {'error': 'New username and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user

        if not user.check_password(password):
            return Response(
                {'error': 'Invalid password'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(username=new_username).exclude(pk=user.pk).exists():
            return Response(
                {'error': 'User with this username already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            AccountEmailService.send_username_change_confirmation(user, new_username)
        except Exception as exc:
            logger.warning("Failed to send username change confirmation for user %s: %s", user.pk, exc)

        return Response({
            'message': 'Username change confirmation sent to your email.',
        }, status=status.HTTP_200_OK)


class ConfirmEmailChangeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            payload = AccountEmailService.parse_email_change_token(token)
        except SignatureExpired:
            return Response(
                {'error': 'Confirmation link has expired'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except BadSignature:
            return Response(
                {'error': 'Invalid confirmation link'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user_id = payload.get('user_id')
        new_email = payload.get('new_email')

        if not user_id or not new_email:
            return Response(
                {'error': 'Invalid confirmation data'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if User.objects.filter(email=new_email).exclude(pk=user.pk).exists():
            return Response(
                {'error': 'User with this email already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.email = new_email
        user.save(update_fields=['email'])

        customer = CustomerService.get_by_user(user)
        if customer:
            CustomerService.verify_email(customer)

        return Response({
            'message': 'Email successfully updated and confirmed',
        }, status=status.HTTP_200_OK)


class ConfirmUsernameChangeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            payload = AccountEmailService.parse_username_change_token(token)
        except SignatureExpired:
            return Response(
                {'error': 'Confirmation link has expired'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except BadSignature:
            return Response(
                {'error': 'Invalid confirmation link'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user_id = payload.get('user_id')
        new_username = payload.get('new_username')

        if not user_id or not new_username:
            return Response(
                {'error': 'Invalid confirmation data'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if User.objects.filter(username=new_username).exclude(pk=user.pk).exists():
            return Response(
                {'error': 'User with this username already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.username = new_username
        user.save(update_fields=['username'])

        return Response({
            'message': 'Username successfully updated',
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({
                'message': 'Successful logout',
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
