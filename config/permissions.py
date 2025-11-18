"""Custom permission classes for access control."""

from rest_framework import permissions


class IsAdminUser(permissions.BasePermission):
    """
    Permission class that allows access only to admin users (staff members).

    Checks if the user is authenticated and has staff status.
    """

    def has_permission(self, request, view):
        """
        Check if the user has admin permissions.

        Args:
            request: The HTTP request object.
            view: The view being accessed.

        Returns:
            bool: True if user is authenticated and is staff, False otherwise.
        """
        return request.user and request.user.is_authenticated and request.user.is_staff


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission class that allows read access to authenticated users and write access to admins.

    Safe methods (GET, HEAD, OPTIONS) are available to all authenticated users,
    while unsafe methods require admin privileges.
    """

    def has_permission(self, request, view):
        """
        Check if the user has permission based on request method.

        Args:
            request: The HTTP request object.
            view: The view being accessed.

        Returns:
            bool: True if user is authenticated (for read) or admin (for write), False otherwise.
        """
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_authenticated and request.user.is_staff


class IsCustomerUser(permissions.BasePermission):
    """
    Permission class that allows access only to regular customers (non-staff users).

    Checks if the user is authenticated and is not a staff member.
    """

    def has_permission(self, request, view):
        """
        Check if the user is a customer (non-staff).

        Args:
            request: The HTTP request object.
            view: The view being accessed.

        Returns:
            bool: True if user is authenticated and not staff, False otherwise.
        """
        return request.user and request.user.is_authenticated and not request.user.is_staff


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission class that allows access to object owners or admins.

    Checks if the user is either the owner of the object or an admin.
    Supports objects with 'user' or 'customer' attributes.
    """

    def has_object_permission(self, request, view, obj):
        """
        Check if the user is the owner of the object or an admin.

        Args:
            request: The HTTP request object.
            view: The view being accessed.
            obj: The object being accessed.

        Returns:
            bool: True if user is admin or owner of the object, False otherwise.
        """
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
    """
    Permission class that requires email verification for customers.

    Allows access only to users who have verified their email address.
    Admin users are exempt from this requirement.
    """

    message = "Email must be verified to perform this action."

    def has_permission(self, request, view):
        """
        Check if the user's email is verified.

        Args:
            request: The HTTP request object.
            view: The view being accessed.

        Returns:
            bool: True if user is admin or has verified email, False otherwise.
        """
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
    """
    Permission class that allows only read-only (safe) methods.

    Restricts access to GET, HEAD, and OPTIONS requests only.
    """

    def has_permission(self, request, view):
        """
        Check if the request method is safe (read-only).

        Args:
            request: The HTTP request object.
            view: The view being accessed.

        Returns:
            bool: True if request method is safe, False otherwise.
        """
        return request.method in permissions.SAFE_METHODS
