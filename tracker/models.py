from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Food(models.Model):
    """A food product cached from OpenFoodFacts, keyed by its barcode.

    The remote API is messy and rate-limited, so the first time a product is
    logged it is normalised and stored here; later logs reuse this row.
    """

    NOVA_CHOICES = [
        (1, "Unprocessed or minimally processed"),
        (2, "Processed culinary ingredient"),
        (3, "Processed food"),
        (4, "Ultra-processed food"),
    ]

    off_code = models.CharField("OpenFoodFacts barcode", max_length=64, unique=True)
    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=255, blank=True)

    nova_group = models.PositiveSmallIntegerField(choices=NOVA_CHOICES, null=True, blank=True)
    nutriscore_grade = models.CharField(max_length=1, blank=True)  # "a".."e", lowercase

    # Nutrients per 100 g.
    energy_kcal = models.FloatField(null=True, blank=True)
    protein_g = models.FloatField(null=True, blank=True)
    fiber_g = models.FloatField(null=True, blank=True)
    sugars_g = models.FloatField(null=True, blank=True)
    salt_g = models.FloatField(null=True, blank=True)

    # Normalised key for the "plant variety" metric, e.g. "spinach", "chickpea".
    # Blank when the product isn't a recognisable whole plant food.
    plant_key = models.CharField(max_length=64, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} — {self.brand}" if self.brand else self.name

    @property
    def is_ultra_processed(self):
        return self.nova_group == 4

    def amount_of(self, nutrient, grams):
        """The given nutrient (a field name) scaled to `grams`, or None if unknown."""
        per_100g = getattr(self, nutrient)
        if per_100g is None:
            return None
        return per_100g * grams / 100


class Entry(models.Model):
    """One logged portion of a food, on a date."""

    MEALS = [
        ("breakfast", "Breakfast"),
        ("lunch", "Lunch"),
        ("dinner", "Dinner"),
        ("snack", "Snack"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="entries")
    food = models.ForeignKey(Food, on_delete=models.PROTECT, related_name="entries")
    grams = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    meal = models.CharField(max_length=16, choices=MEALS, default="lunch")
    eaten_on = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-eaten_on", "-created_at"]
        verbose_name_plural = "entries"

    def __str__(self):
        return f"{self.grams} g {self.food} on {self.eaten_on}"

    def kcal(self):
        return self.food.amount_of("energy_kcal", self.grams)
