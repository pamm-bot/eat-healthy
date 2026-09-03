import pytest
from django.contrib.auth.models import User
from django.utils import timezone

from tracker.models import Entry, Food


@pytest.fixture
def user(db):
    return User.objects.create_user(username="tester", password="pw-123456789")


@pytest.fixture
def make_food(db):
    counter = {"n": 0}

    def _make(**kwargs):
        counter["n"] += 1
        defaults = {
            "off_code": f"code-{counter['n']}",
            "name": kwargs.pop("name", f"Food {counter['n']}"),
            "energy_kcal": 100.0,
            "protein_g": 5.0,
            "fiber_g": 3.0,
            "sugars_g": 2.0,
            "salt_g": 0.5,
        }
        defaults.update(kwargs)
        return Food.objects.create(**defaults)

    return _make


@pytest.fixture
def make_entry(db, user, make_food):
    def _make(food=None, *, grams=100, eaten_on=None, meal="lunch", **food_kwargs):
        food = food or make_food(**food_kwargs)
        return Entry.objects.create(
            user=user,
            food=food,
            grams=grams,
            meal=meal,
            eaten_on=eaten_on or timezone.localdate(),
        )

    return _make
