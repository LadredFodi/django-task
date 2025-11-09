from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.services import AuthService


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        password_confirm = request.data.get('password_confirm')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        
        error = AuthService.validate_registration_data(username, email, password, password_confirm)
        if error:
            return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
        
        customer = AuthService.register_user(
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
        success, error, customer = AuthService.verify_email_by_token(uidb64, token)
        
        if not success:
            status_code = status.HTTP_404_NOT_FOUND if error == 'Customer profile not found' else status.HTTP_400_BAD_REQUEST
            return Response({'error': error}, status=status_code)
        
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
        
        AuthService.request_password_reset(email)
        
        return Response({
            'message': 'If the specified email exists, a letter with a link for password reset has been sent to it.',
        }, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, uidb64, token):
        new_password = request.data.get('new_password')
        password_confirm = request.data.get('password_confirm')
        
        success, error = AuthService.reset_password(uidb64, token, new_password, password_confirm)
        
        if not success:
            return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'message': 'Password successfully changed',
        }, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        password_confirm = request.data.get('password_confirm')
        
        success, error = AuthService.change_password(
            request.user, old_password, new_password, password_confirm
        )
        
        if not success:
            return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'message': 'Password successfully changed',
        }, status=status.HTTP_200_OK)


class ChangeEmailView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        new_email = request.data.get('new_email')
        password = request.data.get('password')
        
        success, error = AuthService.request_email_change(request.user, new_email, password)
        
        if not success:
            return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'message': 'Email change request sent. Check your new email for confirmation.',
        }, status=status.HTTP_200_OK)


class ResendVerificationEmailView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        success, error = AuthService.resend_verification_email(request.user)
        
        if not success:
            if error == 'Email already confirmed':
                return Response({'message': error}, status=status.HTTP_400_BAD_REQUEST)
            status_code = status.HTTP_404_NOT_FOUND if error == 'Customer profile not found' else status.HTTP_400_BAD_REQUEST
            return Response({'error': error}, status=status_code)
        
        return Response({
            'message': 'Email confirmation letter has been sent',
        }, status=status.HTTP_200_OK)


class ChangeUsernameView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        new_username = request.data.get('new_username')
        password = request.data.get('password')

        success, error = AuthService.request_username_change(request.user, new_username, password)
        
        if not success:
            return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'message': 'Username change confirmation sent to your email.',
        }, status=status.HTTP_200_OK)


class ConfirmEmailChangeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        success, error = AuthService.confirm_email_change(token)
        
        if not success:
            status_code = status.HTTP_404_NOT_FOUND if error == 'User not found' else status.HTTP_400_BAD_REQUEST
            return Response({'error': error}, status=status_code)

        return Response({
            'message': 'Email successfully updated and confirmed',
        }, status=status.HTTP_200_OK)


class ConfirmUsernameChangeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        success, error = AuthService.confirm_username_change(token)
        
        if not success:
            status_code = status.HTTP_404_NOT_FOUND if error == 'User not found' else status.HTTP_400_BAD_REQUEST
            return Response({'error': error}, status=status_code)

        return Response({
            'message': 'Username successfully updated',
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get('refresh_token')
        success, error = AuthService.logout_user(refresh_token)
        
        if not success:
            return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'message': 'Successful logout',
        }, status=status.HTTP_200_OK)
