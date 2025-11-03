from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str

from rest_framework_simplejwt.tokens import RefreshToken

from customers.services import CustomerService


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
            # Place for verification email
            pass
        except Exception as e:
            print(f"Error sending email: {e}")
        
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
            # Place for password reset email
            pass
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
        
        user.email = new_email
        user.save()
        
        customer = CustomerService.get_by_user(user)
        if customer:
            customer.email_verified = False
            customer.save(update_fields=['email_verified', 'updated_at'])
            
            # Place for verification email
            pass
        
        return Response({
            'message': 'Email changed. Check your new email for confirmation.',
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
        
        # Place for verification email
        pass
        
        return Response({
            'message': 'Email confirmation letter has been sent',
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
