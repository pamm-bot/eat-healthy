"""Build a demo account with a couple of weeks of realistic entries, so the
dashboard has something to show. Safe to re-run: it rebuilds this one user.

Foods are hard-coded (not fetched from OpenFoodFacts) so the command works
offline and in CI.
"""

import random
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from tracker.models import Entry, Food

DEMO_USERNAME = "demo"
# This is a published demo login, not a secret.
DEMO_PASSWORD = "demo12345"  # nosec B105

# name, brand, nova, nutriscore, kcal, protein, fibre, sugars, salt, plant_key
FOODS = [
    ("Rolled oats", "", 1, "a", 370, 13, 10.0, 1.0, 0.0, "oat"),
    ("Whole milk", "", 1, "b", 63, 3.3, 0.0, 4.8, 0.1, ""),
    ("Banana", "", 1, "a", 89, 1.1, 2.6, 12.0, 0.0, "banana"),
    ("Blueberries", "", 1, "a", 57, 0.7, 2.4, 10.0, 0.0, "blueberry"),
    ("Wholemeal bread", "", 3, "a", 247, 9.0, 7.0, 3.0, 1.0, "whole wheat"),
    ("Cheddar cheese", "", 3, "d", 402, 25, 0.0, 0.5, 1.8, ""),
    ("Baby spinach", "", 1, "a", 23, 2.9, 2.2, 0.4, 0.08, "spinach"),
    ("Cherry tomatoes", "", 1, "a", 18, 0.9, 1.2, 2.6, 0.01, "tomato"),
    ("Chickpeas, canned", "", 1, "a", 119, 7.0, 6.0, 0.5, 0.6, "chickpea"),
    ("Brown rice, cooked", "", 1, "a", 123, 2.7, 1.8, 0.4, 0.005, "brown rice"),
    ("Chicken breast", "", 1, "b", 165, 31, 0.0, 0.0, 0.2, ""),
    ("Olive oil", "", 2, "c", 884, 0.0, 0.0, 0.0, 0.0, ""),
    ("Greek yoghurt", "", 1, "b", 97, 9.0, 0.0, 4.0, 0.1, ""),
    ("Almonds", "", 1, "a", 579, 21, 12.5, 4.4, 0.001, "almond"),
    ("Instant noodles", "NoodleCo", 4, "d", 450, 9.0, 2.0, 3.0, 3.2, ""),
    ("Chocolate biscuits", "SnackCo", 4, "e", 490, 6.0, 2.5, 33.0, 0.6, ""),
    ("Cola", "FizzCo", 4, "e", 42, 0.0, 0.0, 10.6, 0.0, ""),
    ("Frozen pizza", "PizzaCo", 4, "d", 266, 11, 2.5, 3.5, 1.3, ""),
    ("Carrot", "", 1, "a", 41, 0.9, 2.8, 4.7, 0.07, "carrot"),
    ("Lentils, cooked", "", 1, "a", 116, 9.0, 8.0, 1.8, 0.002, "lentil"),
]

# meal -> list of (food index, grams) options
PATTERN = {
    "breakfast": [(0, 60), (1, 200), (2, 120), (3, 80), (12, 150)],
    "lunch": [(4, 90), (6, 80), (7, 100), (8, 150), (9, 180), (10, 120), (11, 10)],
    "dinner": [(9, 200), (10, 150), (18, 100), (19, 180), (17, 300), (5, 40)],
    "snack": [(13, 30), (14, 90), (15, 40), (16, 330), (3, 60)],
}


class Command(BaseCommand):
    help = "Create the demo account with two weeks of sample entries."

    def handle(self, *args, **options):
        # Only used to shape demo data; not security-sensitive.
        rng = random.Random(42)  # nosec B311

        demo, _ = User.objects.get_or_create(username=DEMO_USERNAME)
        demo.set_password(DEMO_PASSWORD)
        demo.save()
        demo.entries.all().delete()

        foods = [
            Food.objects.update_or_create(
                off_code=f"demo-{i}",
                defaults={
                    "name": f[0],
                    "brand": f[1],
                    "nova_group": f[2],
                    "nutriscore_grade": f[3],
                    "energy_kcal": f[4],
                    "protein_g": f[5],
                    "fiber_g": f[6],
                    "sugars_g": f[7],
                    "salt_g": f[8],
                    "plant_key": f[9],
                },
            )[0]
            for i, f in enumerate(FOODS)
        ]

        today = timezone.localdate()
        created = 0
        for day_offset in range(14):
            eaten_on = today - timedelta(days=day_offset)
            for meal, choices in PATTERN.items():
                for food_index, grams in rng.sample(choices, k=rng.randint(1, 2)):
                    Entry.objects.create(
                        user=demo,
                        food=foods[food_index],
                        grams=grams + rng.randint(-15, 15),
                        meal=meal,
                        eaten_on=eaten_on,
                    )
                    created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo ready: {DEMO_USERNAME} / {DEMO_PASSWORD} — {created} entries over 14 days."
            )
        )
