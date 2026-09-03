from datetime import date

import pytest

from tracker.reports import build_weekly_report, week_bounds

pytestmark = pytest.mark.django_db

START = date(2026, 6, 1)  # a Monday
END = date(2026, 6, 7)


def report_for(entries):
    return build_weekly_report(entries, start=START, end=END)


def test_week_bounds_is_monday_to_sunday():
    start, end = week_bounds(date(2026, 6, 3))  # a Wednesday
    assert start == date(2026, 6, 1)
    assert end == date(2026, 6, 7)


def test_empty_week_has_no_data(make_food):
    report = report_for([])
    assert report.has_data is False
    assert report.total_kcal == 0
    assert report.ultra_processed_pct is None
    assert report.distinct_plants == 0


def test_ultra_processed_pct_is_share_of_known_calories(make_entry):
    entries = [
        make_entry(grams=100, energy_kcal=100, nova_group=4),  # 100 kcal ultra
        make_entry(grams=100, energy_kcal=300, nova_group=1),  # 300 kcal not
    ]
    report = report_for(entries)
    assert report.total_kcal == 400
    assert report.ultra_processed_pct == 25.0


def test_calorieless_foods_are_ignored_in_the_processed_share(make_entry):
    entries = [
        make_entry(grams=100, energy_kcal=200, nova_group=4),
        make_entry(grams=100, energy_kcal=None, nova_group=1),  # no kcal -> ignored
    ]
    report = report_for(entries)
    assert report.ultra_processed_pct == 100.0


def test_plant_variety_counts_distinct_plant_keys(make_entry):
    entries = [
        make_entry(plant_key="spinach"),
        make_entry(plant_key="spinach"),  # duplicate -> counted once
        make_entry(plant_key="chickpea"),
        make_entry(plant_key=""),  # not a plant
    ]
    report = report_for(entries)
    assert report.distinct_plants == 2
    assert report.plants == ["chickpea", "spinach"]


def test_nutriscore_counts_group_unknown_grades(make_entry):
    for grade in ["a", "a", "c", "", "z"]:
        make_entry(nutriscore_grade=grade)
    report = report_for(list_all_entries())
    assert report.nutriscore_counts["a"] == 2
    assert report.nutriscore_counts["c"] == 1
    assert report.nutriscore_counts["unknown"] == 2


def test_nutrient_averages_are_per_logged_day(make_entry):
    # 30 g fibre on day 1, 10 g on day 2 -> 20 g/day average over 2 logged days
    make_entry(grams=100, fiber_g=30.0, eaten_on=date(2026, 6, 1))
    make_entry(grams=100, fiber_g=10.0, eaten_on=date(2026, 6, 2))
    report = report_for(list_all_entries())

    fibre = next(n for n in report.nutrients if n.key == "fiber")
    assert report.days_logged == 2
    assert fibre.avg == 20.0
    assert fibre.status == "low"  # below the 25 g reference


def test_nutrient_status_flags_high_salt(make_entry):
    make_entry(grams=100, salt_g=8.0)  # 8 g in one day
    report = report_for(list_all_entries())
    salt = next(n for n in report.nutrients if n.key == "salt")
    assert salt.status == "high"
    assert salt.symbol == "≤"


def list_all_entries():
    from tracker.models import Entry

    return list(Entry.objects.select_related("food"))
