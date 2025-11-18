from django.contrib.gis.db.models import PointField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django_countries.fields import CountryField

from config.models import BaseModel


class Dealership(BaseModel):

    name = models.CharField(max_length=256, verbose_name="Dealership Name", unique=True, db_index=True)

    country = CountryField(verbose_name="Country")
    city = models.CharField(max_length=128, verbose_name="City")
    address = models.CharField(max_length=256, verbose_name="Address")
    location = PointField(
        verbose_name="Coordinates",
        geography=True,
        null=True,
        blank=True,
        help_text="Geographic coordinates of the dealership (longitude, latitude)",
    )

    email = models.EmailField(verbose_name="Email", unique=True)
    phone = models.CharField(max_length=32, verbose_name="Phone")
    website = models.URLField(verbose_name="Website", blank=True, null=True)

    balance = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        verbose_name="Balance (USD)",
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Current dealership balance",
    )

    total_sales = models.PositiveIntegerField(verbose_name="Total Sales", default=0)
    total_revenue = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        verbose_name="Total Revenue (USD)",
        default=0,
        validators=[MinValueValidator(0)],
    )
    total_profit = models.DecimalField(max_digits=16, decimal_places=2, verbose_name="Total Profit (USD)", default=0)

    description = models.TextField(verbose_name="Description", blank=True, null=True)

    class Meta:
        verbose_name = "Dealership"
        verbose_name_plural = "Dealerships"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name", "is_active"]),
            models.Index(fields=["country", "city"]),
            models.Index(fields=["-total_sales", "-total_revenue"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.city}, {self.country})"


class DealershipPreference(BaseModel):

    dealership = models.ForeignKey(
        Dealership, on_delete=models.CASCADE, related_name="preferences", verbose_name="Dealership"
    )

    preferred_body_types = models.JSONField(
        verbose_name="Preferred Body Types",
        default=list,
        blank=True,
        help_text='List of body types, e.g.: ["sedan", "suv"]',
    )
    preferred_fuel_types = models.JSONField(
        verbose_name="Preferred Fuel Types",
        default=list,
        blank=True,
        help_text='List of fuel types, e.g.: ["gasoline", "hybrid"]',
    )
    preferred_brands = models.JSONField(
        verbose_name="Preferred Brands",
        default=list,
        blank=True,
        help_text='List of brands, e.g.: ["Toyota", "BMW"]',
    )

    min_price = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        verbose_name="Minimum Price (USD)",
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    max_price = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        verbose_name="Maximum Price (USD)",
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        verbose_name = "Dealership Preference"
        verbose_name_plural = "Dealership Preferences"
        ordering = ["dealership"]
        indexes = [
            models.Index(fields=["dealership"]),
        ]

    def __str__(self):
        return f"Preferences for {self.dealership.name}"


class DealershipInventory(BaseModel):

    dealership = models.ForeignKey(
        Dealership, on_delete=models.CASCADE, related_name="inventory", verbose_name="Dealership"
    )
    car_model = models.ForeignKey(
        "cars.CarModel", on_delete=models.CASCADE, related_name="dealership_inventory", verbose_name="Car Model"
    )

    quantity = models.PositiveIntegerField(verbose_name="Quantity in Stock", default=0)
    purchase_price = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        verbose_name="Purchase Price (USD)",
        validators=[MinValueValidator(0)],
        help_text="Average purchase price",
    )
    selling_price = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        verbose_name="Selling Price (USD)",
        validators=[MinValueValidator(0)],
        help_text="Price for selling to customers",
    )

    times_sold = models.PositiveIntegerField(verbose_name="Number of Sales", default=0)
    last_sale_date = models.DateTimeField(verbose_name="Last Sale Date", null=True, blank=True)

    class Meta:
        verbose_name = "Dealership Inventory"
        verbose_name_plural = "Dealership Inventories"
        unique_together = [["dealership", "car_model"]]
        ordering = ["dealership", "-quantity"]
        indexes = [
            models.Index(fields=["dealership", "is_active"]),
            models.Index(fields=["car_model", "quantity"]),
            models.Index(fields=["-times_sold"]),
        ]

    def __str__(self):
        return f"{self.dealership.name} - {self.car_model} (x{self.quantity})"


class Purchase(BaseModel):

    dealership = models.ForeignKey(
        Dealership, on_delete=models.CASCADE, related_name="purchases", verbose_name="Dealership"
    )
    supplier = models.ForeignKey(
        "suppliers.Supplier", on_delete=models.CASCADE, related_name="dealership_purchases", verbose_name="Supplier"
    )
    car_model = models.ForeignKey(
        "cars.CarModel", on_delete=models.CASCADE, related_name="purchases", verbose_name="Car Model"
    )

    quantity = models.PositiveIntegerField(verbose_name="Quantity", validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(
        max_digits=16, decimal_places=2, verbose_name="Unit Price (USD)", validators=[MinValueValidator(0)]
    )
    total_price = models.DecimalField(
        max_digits=16, decimal_places=2, verbose_name="Total Price (USD)", validators=[MinValueValidator(0)]
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
        related_name="purchases",
        verbose_name="Applied Promotion",
    )

    notes = models.TextField(verbose_name="Notes", blank=True, null=True)

    class Meta:
        verbose_name = "Purchase"
        verbose_name_plural = "Purchases"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["dealership", "-created_at"]),
            models.Index(fields=["supplier", "-created_at"]),
            models.Index(fields=["car_model", "-created_at"]),
            models.Index(fields=["-created_at", "is_active"]),
        ]

    def __str__(self):
        return f"{self.dealership.name} ← {self.supplier.name}: {self.car_model} x{self.quantity}"
