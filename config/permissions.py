from rest_framework import permissions


class IsAdminUser(permissions.BasePermission):

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff


class IsAdminOrReadOnly(permissions.BasePermission):

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_authenticated and request.user.is_staff


class IsCustomerUser(permissions.BasePermission):

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and not request.user.is_staff


class IsOwnerOrAdmin(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True

        if hasattr(obj, "user"):
            return obj.user == request.user

        if hasattr(obj, "customer"):
            return obj.customer.user == request.user

        if hasattr(obj, "customer"):
            return obj.customer.user == request.user

        return False


class IsEmailVerified(permissions.BasePermission):

    message = "Email must be verified to perform this action."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_staff:
            return True

        try:
            customer = request.user.customer_profile
            return customer.email_verified
        except AttributeError:
            return False


class ReadOnlyPermission(permissions.BasePermission):

    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS
