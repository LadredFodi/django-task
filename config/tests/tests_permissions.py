import pytest
from unittest.mock import Mock

from config.permissions import (
    IsAdminUser,
    IsAdminOrReadOnly,
    IsCustomerUser,
    IsOwnerOrAdmin,
    IsEmailVerified,
    ReadOnlyPermission
)


@pytest.mark.django_db
class TestIsAdminUser:
    
    def test_admin_user_has_permission(self, admin_user):
        permission = IsAdminUser()
        request = Mock()
        request.user = admin_user
        
        assert permission.has_permission(request, None) is True
    
    def test_regular_user_no_permission(self, regular_user):
        permission = IsAdminUser()
        request = Mock()
        request.user = regular_user
        
        assert permission.has_permission(request, None) is False
    
    def test_unauthenticated_user_no_permission(self):
        permission = IsAdminUser()
        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = False
        
        assert permission.has_permission(request, None) is False


@pytest.mark.django_db
class TestIsAdminOrReadOnly:
    
    def test_admin_has_full_access(self, admin_user):
        permission = IsAdminOrReadOnly()
        request = Mock()
        request.user = admin_user
        request.method = 'POST'
        
        assert permission.has_permission(request, None) is True
    
    def test_regular_user_has_read_access(self, regular_user):
        permission = IsAdminOrReadOnly()
        request = Mock()
        request.user = regular_user
        request.method = 'GET'
        
        assert permission.has_permission(request, None) is True
    
    def test_regular_user_no_write_access(self, regular_user):
        permission = IsAdminOrReadOnly()
        request = Mock()
        request.user = regular_user
        request.method = 'POST'
        
        assert permission.has_permission(request, None) is False
    
    def test_unauthenticated_user_no_access(self):
        permission = IsAdminOrReadOnly()
        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = False
        request.method = 'GET'
        
        assert permission.has_permission(request, None) is False

@pytest.mark.django_db
class TestIsCustomerUser:
    
    def test_regular_user_has_permission(self, regular_user):
        permission = IsCustomerUser()
        request = Mock()
        request.user = regular_user
        
        assert permission.has_permission(request, None) is True
    
    def test_admin_user_no_permission(self, admin_user):
        permission = IsCustomerUser()
        request = Mock()
        request.user = admin_user
        
        assert permission.has_permission(request, None) is False
    
    def test_unauthenticated_user_no_permission(self):
        permission = IsCustomerUser()
        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = False
        
        assert permission.has_permission(request, None) is False


@pytest.mark.django_db
class TestIsOwnerOrAdmin:
    
    def test_admin_has_permission(self, admin_user):
        permission = IsOwnerOrAdmin()
        request = Mock()
        request.user = admin_user
        obj = Mock()
        
        assert permission.has_object_permission(request, None, obj) is True
    
    def test_owner_has_permission(self, regular_user):
        permission = IsOwnerOrAdmin()
        request = Mock()
        request.user = regular_user
        
        obj = Mock()
        obj.user = regular_user
        
        assert permission.has_object_permission(request, None, obj) is True
    
    def test_owner_through_customer_has_permission(self, regular_user, customer):
        permission = IsOwnerOrAdmin()
        request = Mock()
        request.user = regular_user
        
        obj = Mock()
        obj.customer = customer
        obj.customer.user = regular_user
        
        assert permission.has_object_permission(request, None, obj) is True
    
    def test_non_owner_no_permission(self, regular_user, user_factory):
        permission = IsOwnerOrAdmin()
        request = Mock()
        request.user = regular_user
        
        other_user = user_factory()
        obj = Mock()
        obj.user = other_user
        
        assert permission.has_object_permission(request, None, obj) is False
    
    def test_object_without_user_or_customer_no_permission(self, regular_user):
        permission = IsOwnerOrAdmin()
        request = Mock()
        request.user = regular_user
        
        obj = Mock(spec=[])
        delattr(obj, 'user')
        delattr(obj, 'customer')
        
        assert permission.has_object_permission(request, None, obj) is False

@pytest.mark.django_db
class TestIsEmailVerified:
    
    def test_admin_always_has_permission(self, admin_user):
        permission = IsEmailVerified()
        request = Mock()
        request.user = admin_user
        
        assert permission.has_permission(request, None) is True
    
    def test_verified_customer_has_permission(self, regular_user, customer):
        customer.email_verified = True
        customer.save()
        
        permission = IsEmailVerified()
        request = Mock()
        request.user = regular_user
        
        assert permission.has_permission(request, None) is True
    
    def test_unverified_customer_no_permission(self, regular_user, customer):
        customer.email_verified = False
        customer.save()
        
        permission = IsEmailVerified()
        request = Mock()
        request.user = regular_user
        
        assert permission.has_permission(request, None) is False
    
    def test_unauthenticated_user_no_permission(self):
        permission = IsEmailVerified()
        request = Mock()
        request.user = None
        
        assert permission.has_permission(request, None) is False
    
    def test_user_without_customer_profile_no_permission(self, regular_user):
        if hasattr(regular_user, 'customer_profile'):
            regular_user.customer_profile.delete()
        
        permission = IsEmailVerified()
        request = Mock()
        request.user = regular_user
        
        assert permission.has_permission(request, None) is False
    
    def test_custom_error_message(self):
        permission = IsEmailVerified()
        
        assert permission.message == "Email must be verified to perform this action."


@pytest.mark.django_db
class TestReadOnlyPermission:
    
    def test_get_method_allowed(self):
        permission = ReadOnlyPermission()
        request = Mock()
        request.method = 'GET'
        
        assert permission.has_permission(request, None) is True
    
    def test_head_method_allowed(self):
        permission = ReadOnlyPermission()
        request = Mock()
        request.method = 'HEAD'
        
        assert permission.has_permission(request, None) is True
    
    def test_options_method_allowed(self):
        permission = ReadOnlyPermission()
        request = Mock()
        request.method = 'OPTIONS'
        
        assert permission.has_permission(request, None) is True
    
    def test_post_method_not_allowed(self):
        permission = ReadOnlyPermission()
        request = Mock()
        request.method = 'POST'
        
        assert permission.has_permission(request, None) is False
    
    def test_put_method_not_allowed(self):
        permission = ReadOnlyPermission()
        request = Mock()
        request.method = 'PUT'
        
        assert permission.has_permission(request, None) is False
    
    def test_patch_method_not_allowed(self):
        permission = ReadOnlyPermission()
        request = Mock()
        request.method = 'PATCH'
        
        assert permission.has_permission(request, None) is False
    
    def test_delete_method_not_allowed(self):
        permission = ReadOnlyPermission()
        request = Mock()
        request.method = 'DELETE'
        
        assert permission.has_permission(request, None) is False

@pytest.mark.django_db
class TestPermissionsIntegration:
    
    def test_multiple_permissions_admin(self, admin_user):
        permissions = [
            IsAdminUser(),
            IsAdminOrReadOnly(),
            IsOwnerOrAdmin(),
            IsEmailVerified()
        ]
        
        request = Mock()
        request.user = admin_user
        request.method = 'POST'
        
        for permission in permissions:
            assert permission.has_permission(request, None) is True
    
    def test_multiple_permissions_regular_user(self, regular_user, customer):
        customer.email_verified = True
        customer.save()
        
        request = Mock()
        request.user = regular_user
        request.method = 'GET'
        
        assert IsAdminOrReadOnly().has_permission(request, None) is True
        assert IsCustomerUser().has_permission(request, None) is True
        assert IsEmailVerified().has_permission(request, None) is True
        
        assert IsAdminUser().has_permission(request, None) is False
        
        request.method = 'POST'
        assert IsAdminOrReadOnly().has_permission(request, None) is False
    
    def test_permission_chain_verified_customer_read_only(self, regular_user, customer):
        customer.email_verified = True
        customer.save()
        
        request = Mock()
        request.user = regular_user
        request.method = 'GET'
        
        assert IsEmailVerified().has_permission(request, None) is True
        assert ReadOnlyPermission().has_permission(request, None) is True
        assert IsCustomerUser().has_permission(request, None) is True
    
    def test_permission_chain_unverified_customer(self, regular_user, customer):
        customer.email_verified = False
        customer.save()
        
        request = Mock()
        request.user = regular_user
        
        assert IsEmailVerified().has_permission(request, None) is False
        
        assert IsCustomerUser().has_permission(request, None) is True

