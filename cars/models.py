"""Car models for the Dealership Management System."""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from config.models import BaseModel


class CarModel(BaseModel):
    """
    Model representing a car specification.

    Stores detailed information about car models including brand, specifications,
    engine details, and physical characteristics.
    """

    BODY_TYPE_CHOICES = [
        ("sedan", "Sedan"),
        ("suv", "SUV"),
        ("hatchback", "Hatchback"),
        ("coupe", "Coupe"),
        ("wagon", "Wagon"),
        ("minivan", "Minivan"),
        ("pickup", "Pickup"),
        ("convertible", "Convertible"),
    ]

    FUEL_TYPE_CHOICES = [
        ("gasoline", "Gasoline"),
        ("diesel", "Diesel"),
        ("electric", "Electric"),
        ("hybrid", "Hybrid"),
        ("plugin_hybrid", "Plugin Hybrid"),
    ]

    TRANSMISSION_CHOICES = [
        ("manual", "Manual"),
        ("automatic", "Automatic"),
        ("cvt", "CVT"),
        ("robot", "Robot"),
    ]

    DRIVE_TYPE_CHOICES = [
        ("fwd", "Front Wheel Drive"),
        ("rwd", "Rear Wheel Drive"),
        ("awd", "All Wheel Drive"),
    ]

    brand = models.CharField(max_length=128, verbose_name="Brand", db_index=True)
    model = models.CharField(max_length=128, verbose_name="Model", db_index=True)
    year = models.PositiveIntegerField(
        verbose_name="Year",
        validators=[MinValueValidator(1024), MaxValueValidator(2048)],
        db_index=True,
    )

    body_type = models.CharField(max_length=32, choices=BODY_TYPE_CHOICES, verbose_name="Body Type", db_index=True)
    color = models.CharField(max_length=64, verbose_name="Color", default="black")
    doors = models.PositiveSmallIntegerField(verbose_name="Number of Doors", default=4)
    seats = models.PositiveSmallIntegerField(verbose_name="Number of Seats", default=5)

    fuel_type = models.CharField(max_length=32, choices=FUEL_TYPE_CHOICES, verbose_name="Fuel Type", db_index=True)
    engine_volume = models.DecimalField(
        max_digits=4, decimal_places=1, verbose_name="Engine Volume (L)", validators=[MinValueValidator(0.1)]
    )
    horsepower = models.PositiveIntegerField(
        verbose_name="Horsepower (HP)", validators=[MinValueValidator(1)], null=True, blank=True
    )

    transmission = models.CharField(
        max_length=32, choices=TRANSMISSION_CHOICES, verbose_name="Transmission Type", db_index=True
    )
    drive_type = models.CharField(max_length=16, choices=DRIVE_TYPE_CHOICES, verbose_name="Drive Type", db_index=True)

    description = models.TextField(verbose_name="Description", blank=True, null=True)
    vin_template = models.CharField(
        max_length=32, verbose_name="VIN Template", blank=True, null=True, help_text="For generating VIN numbers"
    )

    class Meta:
        verbose_name = "Car Model"
        verbose_name_plural = "Car Models"
        ordering = ["-year", "brand", "model"]
        indexes = [
            models.Index(fields=["brand", "model", "year"]),
            models.Index(fields=["body_type", "fuel_type"]),
            models.Index(fields=["is_active", "-created_at"]),
        ]
        unique_together = [["brand", "model", "year", "body_type", "fuel_type", "color", "engine_volume"]]

    def __str__(self):
        return f"{self.brand} {self.model} {self.year} ({self.get_fuel_type_display()})"
