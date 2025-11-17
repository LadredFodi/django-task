from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from rest_framework import permissions
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from config.authentication import (
    ChangeEmailView,
    ChangePasswordView,
    ChangeUsernameView,
    ConfirmEmailChangeView,
    ConfirmUsernameChangeView,
    LogoutView,
    RegisterView,
    RequestPasswordResetView,
    ResendVerificationEmailView,
    ResetPasswordView,
    VerifyEmailView,
)
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


def health_check(request):
    return JsonResponse({"status": "ok"})

schema_view = get_schema_view(
    openapi.Info(
        title="Dealership Management API",
        default_version="v1",
        description="""
# Dealership Management System API

A comprehensive REST API for managing car dealerships, suppliers, inventory, sales, customers, and promotions.

## Features

- **Authentication**: JWT-based authentication with email verification
- **Car Models**: Complete car catalog with specifications
- **Customers**: Customer management with loyalty tracking
- **Dealerships**: Dealership operations with geolocation
- **Suppliers**: Supplier management and pricing
- **Offers**: Smart offer matching system
- **Promotions**: Flexible promotion and discount management
- **Sales**: Complete sales workflow with analytics

## Authentication

Most endpoints require authentication. To authenticate:

1. Register: `POST /api/v1/auth/register/`
2. Login: `POST /api/v1/auth/token/` - получите access и refresh tokens
3. Use Bearer token: Add `Authorization: Bearer <access_token>` header to requests
4. Refresh token: `POST /api/v1/auth/token/refresh/` when access token expires

## Permissions

- **Admin**: Full access to all resources (staff users)
- **Customer**: Access to own resources and read-only access to catalogs
- **Anonymous**: Limited access to registration and public endpoints

## Rate Limiting

API rate limits apply to prevent abuse. Contact support if you need higher limits.
        """,
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="support@dealership.com"),
        license=openapi.License(name="Proprietary License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


urlpatterns = [
    # Health check
    path("health/", health_check, name="health_check"),
    
    # Admin
    path("admin/", admin.site.urls),
    
    # API Documentation
    path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    path("swagger.json", schema_view.without_ui(cache_timeout=0), name="schema-json"),
    
    # JWT Authentication
    path("api/v1/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/v1/auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("api/v1/auth/logout/", LogoutView.as_view(), name="auth_logout"),
    
    # User Authentication
    path("api/v1/auth/register/", RegisterView.as_view(), name="auth_register"),
    path("api/v1/auth/verify-email/<str:uidb64>/<str:token>/", VerifyEmailView.as_view(), name="verify_email"),
    path("api/v1/auth/resend-verification/", ResendVerificationEmailView.as_view(), name="resend_verification"),
    path("api/v1/auth/request-password-reset/", RequestPasswordResetView.as_view(), name="request_password_reset"),
    path("api/v1/auth/reset-password/<str:uidb64>/<str:token>/", ResetPasswordView.as_view(), name="reset_password"),
    path("api/v1/auth/change-password/", ChangePasswordView.as_view(), name="change_password"),
    path("api/v1/auth/change-email/", ChangeEmailView.as_view(), name="change_email"),
    path("api/v1/auth/change-username/", ChangeUsernameView.as_view(), name="change_username"),
    path("api/v1/auth/confirm-email-change/<str:token>/", ConfirmEmailChangeView.as_view(), name="confirm_email_change"),
    path("api/v1/auth/confirm-username-change/<str:token>/", ConfirmUsernameChangeView.as_view(), name="confirm_username_change"),
    
    # API Endpoints
    path("api/v1/cars/", include("cars.urls")),
    path("api/v1/suppliers/", include("suppliers.urls")),
    path("api/v1/dealerships/", include("dealerships.urls")),
    path("api/v1/customers/", include("customers.urls")),
    path("api/v1/offers/", include("offers.urls")),
    path("api/v1/promotions/", include("promotions.urls")),
]


if settings.DEBUG:
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


admin.site.site_header = "Dealership Management System"
admin.site.site_title = "Dealership Admin"
admin.site.index_title = "Welcome to Dealership Management System"
