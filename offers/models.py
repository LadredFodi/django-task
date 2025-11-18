from django.core.validators import MinValueValidator
from django.db import models

from config.models import BaseModel


class Offer(BaseModel):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("expired", "Expired"),
    ]

    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.CASCADE, related_name="offers", verbose_name="Customer"
    )
    car_model = models.ForeignKey(
        "cars.CarModel", on_delete=models.CASCADE, related_name="offers", verbose_name="Car Model"
    )

    max_price = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        verbose_name="Maximum Price (USD)",
        validators=[MinValueValidator(0)],
        help_text="Maximum price the customer is willing to pay",
    )

    status = models.CharField(
        max_length=32, choices=STATUS_CHOICES, default="pending", verbose_name="Status", db_index=True
    )

    matched_dealership = models.ForeignKey(
        "dealerships.Dealership",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="matched_offers",
        verbose_name="Matched Dealership",
        help_text="Dealership that matches the conditions",
    )
    matched_price = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Price at Matched Dealership (USD)",
        validators=[MinValueValidator(0)],
    )

    processed_at = models.DateTimeField(verbose_name="Processed At", null=True, blank=True)
    completed_at = models.DateTimeField(verbose_name="Completed At", null=True, blank=True)
    expires_at = models.DateTimeField(
        verbose_name="Expires At", null=True, blank=True, help_text="When the offer becomes irrelevant"
    )

    notes = models.TextField(verbose_name="Notes", blank=True, null=True)
    search_results = models.JSONField(
        verbose_name="Search Results",
        default=dict,
        blank=True,
        help_text="All found options with prices and dealerships",
    )

    class Meta:
        verbose_name = "Offer"
        verbose_name_plural = "Offers"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "status", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["car_model", "status"]),
            models.Index(fields=["-created_at", "is_active"]),
        ]

    def __str__(self):
        return f"Offer #{self.id}: {self.customer.user.username} → {self.car_model} (max ${self.max_price})"
