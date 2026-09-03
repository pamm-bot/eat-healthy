import pytest

from tracker.models import Food

pytestmark = pytest.mark.django_db


def test_amount_of_scales_a_nutrient_to_the_portion(make_food):
    food = make_food(fiber_g=4.0)  # 4 g per 100 g
    assert food.amount_of("fiber_g", 250) == 10.0


def test_amount_of_returns_none_when_the_nutrient_is_unknown(make_food):
    food = make_food(fiber_g=None)
    assert food.amount_of("fiber_g", 100) is None


def test_is_ultra_processed_tracks_the_nova_group(make_food):
    assert make_food(nova_group=4).is_ultra_processed is True
    assert make_food(nova_group=1).is_ultra_processed is False
    assert make_food(nova_group=None).is_ultra_processed is False


def test_entry_kcal_uses_the_food_and_the_portion(make_entry):
    entry = make_entry(grams=200, energy_kcal=120.0)
    assert entry.kcal() == 240.0


def test_off_code_is_unique(make_food):
    make_food(off_code="dup")
    with pytest.raises(Exception):
        Food.objects.create(off_code="dup", name="other")
