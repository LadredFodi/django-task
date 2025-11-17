"""Base models for the Dealership Management System."""

from django.db import models


class BaseModel(models.Model):
    """
    Abstract base model providing common fields and functionality.

    Provides soft delete functionality, timestamp tracking, and active status management
    for all models in the system.

    Attributes:
        is_active (bool): Indicates if the record is active (soft delete flag).
        created_at (datetime): Timestamp when the record was created.
        updated_at (datetime): Timestamp when the record was last updated.
    """

    is_active = models.BooleanField(default=True, verbose_name="Active", help_text="Instead of deleting the record")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def soft_delete(self):
        """
        Soft delete the record by setting is_active to False.

        Instead of permanently deleting the record from the database,
        this method marks it as inactive.
        """
        self.is_active = False
        self.save(update_fields=["is_active", "updated_at"])

    def restore(self):
        """
        Restore a soft-deleted record by setting is_active to True.

        Reactivates a previously soft-deleted record.
        """
        self.is_active = True
        self.save(update_fields=["is_active", "updated_at"])

