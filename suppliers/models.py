from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django_countries.fields import CountryField
from config.models import BaseModel


class Supplier(BaseModel):
    name = models.CharField(max_length=256, verbose_name="Company Name", unique=True, db_index=True)
    country = CountryField(verbose_name="Country")
    founded_year = models.PositiveIntegerField(
        verbose_name="Founded Year", validators=[MinValueValidator(1024), MaxValueValidator(2048)]
    )

    email = models.EmailField(verbose_name="Email", unique=True)
    phone = models.CharField(max_length=32, verbose_name="Phone", blank=True, null=True)
    website = models.URLField(verbose_name="Website", blank=True, null=True)

    description = models.TextField(verbose_name="Description", blank=True, null=True)
    rating = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        verbose_name="Rating",
        default=5.0,
        validators=[MinValueValidator(0), MaxValueValidator(8)],
        help_text="Rating from 0 to 8",
    )

    total_sales = models.PositiveIntegerField(verbose_name="Total Sales", default=0)
    total_revenue = models.DecimalField(
        max_digits=16, decimal_places=2, verbose_name="Total Revenue (USD)", default=0, validators=[MinValueValidator(0)]
    )

    class Meta:
        verbose_name = "Supplier"
        verbose_name_plural = "Suppliers"
        ordering = ["-rating", "name"]
        indexes = [
            models.Index(fields=["name", "is_active"]),
            models.Index(fields=["-rating", "-total_sales"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.country})"


class SupplierCar(BaseModel):

    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, related_name="supplier_cars", verbose_name="Supplier"
    )
    car_model = models.ForeignKey(
        "cars.CarModel", on_delete=models.CASCADE, related_name="supplier_cars", verbose_name="Car Model"
    )

    price = models.DecimalField(
        max_digits=16, decimal_places=2, verbose_name="Price (USD)", validators=[MinValueValidator(0)]
    )
    available_quantity = models.PositiveIntegerField(
        verbose_name="Available Quantity", default=0, help_text="Number of available cars for sale"
    )

    delivery_days = models.PositiveSmallIntegerField(
        verbose_name="Delivery Days", default=8, help_text="Average delivery time"
    )
    min_order_quantity = models.PositiveSmallIntegerField(
        verbose_name="Minimum Order Quantity", default=1
    )

    times_sold = models.PositiveIntegerField(verbose_name="Times Sold", default=0)
    last_purchase_date = models.DateTimeField(verbose_name="Last Purchase Date", null=True, blank=True)

    class Meta:
        verbose_name = "Supplier Car"
        verbose_name_plural = "Supplier Cars"
        ordering = ["supplier", "price"]
        unique_together = [["supplier", "car_model"]]
        indexes = [
            models.Index(fields=["supplier", "is_active"]),
            models.Index(fields=["car_model", "price"]),
            models.Index(fields=["-times_sold"]),
        ]

    def __str__(self):
        return f"{self.supplier.name} - {self.car_model} (${self.price})"

 
class SupplierDiscount(BaseModel):

    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, related_name="loyalty_discounts", verbose_name="Supplier"
    )
    dealership = models.ForeignKey(
        "dealerships.Dealership",
        on_delete=models.CASCADE,
        related_name="supplier_discounts",
        verbose_name="Dealership",
    )

    discount_percent = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name="Discount Percent",
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    min_purchases = models.PositiveIntegerField(
        verbose_name="Minimum Purchases",
        default=16,
        help_text="Required number of purchases to receive discount",
    )

    is_applied = models.BooleanField(
        default=False, verbose_name="Applied", help_text="Whether the conditions are met to apply discount"
    )

    class Meta:
        verbose_name = "Supplier Discount"
        verbose_name_plural = "Supplier Discounts"
        unique_together = [["supplier", "dealership"]]
        indexes = [
            models.Index(fields=["supplier", "dealership", "is_active"]),
            models.Index(fields=["is_applied"]),
        ]

    def __str__(self):
        return f"{self.supplier.name} → {self.dealership.name}: {self.discount_percent}%"