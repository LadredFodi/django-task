from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from config.models import BaseModel


class Promotion(BaseModel):

    PROMOTION_TYPE_CHOICES = [
        ("seasonal", "Seasonal"),
        ("clearance", "Clearance"),
        ("holiday", "Holiday"),
        ("loyalty", "Loyalty"),
        ("special", "Special"),
    ]

    name = models.CharField(max_length=256, verbose_name="Promotion Name", db_index=True)
    description = models.TextField(verbose_name="Promotion Description")
    promotion_type = models.CharField(
        max_length=32, choices=PROMOTION_TYPE_CHOICES, default="special", verbose_name="Promotion Type"
    )

    start_date = models.DateTimeField(verbose_name="Start Date", db_index=True)
    end_date = models.DateTimeField(verbose_name="End Date", db_index=True)

    default_discount_percent = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name="Default Discount Percent",
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Default discount percentage",
    )

    car_models = models.ManyToManyField(
        "cars.CarModel",
        related_name="promotions",
        verbose_name="Car Models",
        help_text="Models covered by the promotion",
        blank=True,
    )

    min_purchase_amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        verbose_name="Minimum Purchase Amount (USD)",
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Minimum amount to apply discount",
    )

    times_used = models.PositiveIntegerField(verbose_name="Times Used", default=0)

    class Meta:
        verbose_name = "Promotion"
        verbose_name_plural = "Promotions"
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["start_date", "end_date", "is_active"]),
            models.Index(fields=["-times_used"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.start_date.date()} - {self.end_date.date()})"


class PromotionDealership(BaseModel):

    promotion = models.ForeignKey(
        Promotion, on_delete=models.CASCADE, related_name="dealership_promotions", verbose_name="Promotion"
    )
    dealership = models.ForeignKey(
        "dealerships.Dealership", on_delete=models.CASCADE, related_name="promotions", verbose_name="Dealership"
    )

    discount_percent = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name="Dealership Discount Percent",
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Unique discount percentage for this dealership",
    )

    times_applied = models.PositiveIntegerField(verbose_name="Times Applied", default=0)
    total_discount_amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        verbose_name="Total Discount Amount (USD)",
        default=0,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        verbose_name = "Dealership Promotion"
        verbose_name_plural = "Dealership Promotions"
        unique_together = [["promotion", "dealership"]]
        ordering = ["promotion", "dealership"]
        indexes = [
            models.Index(fields=["promotion", "dealership", "is_active"]),
            models.Index(fields=["-times_applied"]),
        ]

    def __str__(self):
        return f"{self.promotion.name} → {self.dealership.name} ({self.discount_percent}%)"


class PromotionSupplier(BaseModel):

    promotion = models.ForeignKey(
        Promotion, on_delete=models.CASCADE, related_name="supplier_promotions", verbose_name="Promotion"
    )
    supplier = models.ForeignKey(
        "suppliers.Supplier", on_delete=models.CASCADE, related_name="promotions", verbose_name="Supplier"
    )

    discount_percent = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name="Supplier Discount Percent",
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Unique discount percentage for this supplier",
    )

    times_applied = models.PositiveIntegerField(verbose_name="Times Applied", default=0)
    total_discount_amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        verbose_name="Total Discount Amount (USD)",
        default=0,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        verbose_name = "Supplier Promotion"
        verbose_name_plural = "Supplier Promotions"
        unique_together = [["promotion", "supplier"]]
        ordering = ["promotion", "supplier"]
        indexes = [
            models.Index(fields=["promotion", "supplier", "is_active"]),
            models.Index(fields=["-times_applied"]),
        ]

    def __str__(self):
        return f"{self.promotion.name} → {self.supplier.name} ({self.discount_percent}%)"

