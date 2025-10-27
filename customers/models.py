from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django_countries.fields import CountryField
from config.models import BaseModel


class Customer(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="customer_profile", verbose_name="User")

    phone = models.CharField(max_length=32, verbose_name="Phone", blank=True, null=True)
    date_of_birth = models.DateField(verbose_name="Date of Birth", null=True, blank=True)
    country = CountryField(verbose_name="Country", blank=True, null=True)
    city = models.CharField(max_length=128, verbose_name="City", blank=True, null=True)
    address = models.CharField(max_length=256, verbose_name="Address", blank=True, null=True)

    balance = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        verbose_name="Balance (USD)",
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Available balance for purchases",
    )

    email_verified = models.BooleanField(default=False, verbose_name="Email Verified")

    total_purchases = models.PositiveIntegerField(verbose_name="Total Purchases", default=0)
    total_spent = models.DecimalField(
        max_digits=16, decimal_places=2, verbose_name="Total Spent (USD)", default=0, validators=[MinValueValidator(0)]
    )

    customer_type = models.CharField(
        max_length=32,
        choices=[
            ("regular", "Regular"),
            ("vip", "VIP"),
            ("premium", "Premium"),
        ],
        default="regular",
        verbose_name="Customer Type",
    )
    loyalty_points = models.PositiveIntegerField(verbose_name="Loyalty Points", default=0)

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"
        ordering = ["-total_spent", "-total_purchases"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["email_verified"]),
            models.Index(fields=["-total_spent", "-total_purchases"]),
            models.Index(fields=["customer_type"]),
        ]

    def __str__(self):
        return f"{self.user.username} ({self.user.email})"

 
class Sale(BaseModel):
    dealership = models.ForeignKey(
        "dealerships.Dealership", on_delete=models.CASCADE, related_name="sales", verbose_name="Dealership"
    )
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="purchases", verbose_name="Customer")
    car_model = models.ForeignKey(
        "cars.CarModel", on_delete=models.CASCADE, related_name="sales", verbose_name="Car Model"
    )

    price = models.DecimalField(
        max_digits=16, decimal_places=2, verbose_name="Sale Price (USD)", validators=[MinValueValidator(0)]
    )
    original_price = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        verbose_name="Original Price (USD)",
        validators=[MinValueValidator(0)],
        help_text="Price before applying discounts",
    )

    discount_applied = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name="Applied Discount (%)",
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    promotion_applied = models.ForeignKey(
        "promotions.Promotion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales",
        verbose_name="Applied Promotion",
    )

    offer = models.OneToOneField(
        "offers.Offer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_sale",
        verbose_name="Offer",
    )

    vin_number = models.CharField(
        max_length=32, verbose_name="VIN Number", unique=True, blank=True, null=True, help_text="Vehicle Identification Number"
    )

    notes = models.TextField(verbose_name="Notes", blank=True, null=True)

    class Meta:
        verbose_name = "Sale"
        verbose_name_plural = "Sales"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["dealership", "-created_at"]),
            models.Index(fields=["customer", "-created_at"]),
            models.Index(fields=["car_model", "-created_at"]),
            models.Index(fields=["-created_at", "is_active"]),
            models.Index(fields=["vin_number"]),
        ]

    def __str__(self):
        return f"{self.dealership.name} → {self.customer.user.username}: {self.car_model}"