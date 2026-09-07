from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone

from tracker.models import Entry, Food
from tracker.reports import week_bounds

pytestmark = pytest.mark.django_db

PRODUCT = {
    "off_code": "555",
    "name": "Rolled Oats",
    "brand": "OatCo",
    "nova_group": 1,
    "nutriscore_grade": "a",
    "energy_kcal": 370.0,
    "protein_g": 13.0,
    "fiber_g": 10.0,
    "sugars_g": 1.0,
    "salt_g": 0.0,
    "plant_key": "oat",
}


def test_dashboard_requires_login(client):
    response = client.get(reverse("dashboard"))
    assert response.status_code == 302
    assert reverse("login") in response.url


def test_home_redirects_a_logged_in_user_to_the_dashboard(client, user):
    client.force_login(user)
    response = client.get(reverse("home"))
    assert response.status_code == 302
    assert response.url == reverse("dashboard")


def test_dashboard_falls_back_to_the_last_week_with_data(client, user, make_entry):
    this_monday = week_bounds(timezone.localdate())[0]
    last_monday = this_monday - timedelta(days=7)
    make_entry(eaten_on=this_monday)  # current week: a single thin day
    for offset in range(3):  # previous week: three distinct days
        make_entry(eaten_on=last_monday + timedelta(days=offset))

    client.force_login(user)
    response = client.get(reverse("dashboard"))

    assert response.context["report"].start == last_monday
    assert response.context["is_current_week"] is False
    assert response.context["next_week"] == this_monday


def test_dashboard_honours_an_explicit_week_even_when_thin(client, user, make_entry):
    this_monday = week_bounds(timezone.localdate())[0]
    make_entry(eaten_on=this_monday)
    for offset in range(3):
        make_entry(eaten_on=this_monday - timedelta(days=7) + timedelta(days=offset))

    client.force_login(user)
    response = client.get(reverse("dashboard"), {"week": this_monday.isoformat()})

    assert response.context["report"].start == this_monday


def test_dashboard_stays_on_the_current_week_for_a_user_with_no_data(client, user):
    this_monday = week_bounds(timezone.localdate())[0]

    client.force_login(user)
    response = client.get(reverse("dashboard"))

    assert response.status_code == 200
    assert response.context["report"].start == this_monday
    assert response.context["is_current_week"] is True


def test_food_search_renders_results(client, user):
    client.force_login(user)
    with patch("tracker.views.openfoodfacts.search", return_value=[PRODUCT]) as mocked:
        response = client.get(reverse("food_search"), {"q": "oats"})
    mocked.assert_called_once_with("oats")
    assert b"Rolled Oats" in response.content


def test_add_entry_creates_the_food_once_and_logs_the_portion(client, user):
    client.force_login(user)
    payload = {"off_code": "555", "grams": 80, "meal": "breakfast", "eaten_on": "2026-06-01"}

    with patch("tracker.views.openfoodfacts.resolve", return_value=PRODUCT) as resolve:
        client.post(reverse("add_entry"), payload)
        client.post(reverse("add_entry"), payload)  # same food again

    resolve.assert_called_once_with("555")  # second add reuses the cached Food row
    assert Food.objects.filter(off_code="555").count() == 1
    entries = Entry.objects.filter(user=user)
    assert entries.count() == 2
    assert entries.first().grams == 80
    assert entries.first().eaten_on == date(2026, 6, 1)


def test_add_entry_ignores_client_supplied_nutrition(client, user):
    client.force_login(user)
    tampered = {
        "off_code": "555",
        "name": "Free Doughnuts",
        "energy_kcal": 1,
        "nova_group": 1,
        "grams": 100,
        "meal": "snack",
        "eaten_on": "2026-06-01",
    }

    with patch("tracker.views.openfoodfacts.resolve", return_value=PRODUCT):
        client.post(reverse("add_entry"), tampered)

    food = Food.objects.get(off_code="555")
    assert food.name == "Rolled Oats"
    assert food.energy_kcal == 370.0
    assert food.nova_group == 1


def test_add_entry_reports_when_the_product_cannot_be_resolved(client, user):
    client.force_login(user)

    with patch("tracker.views.openfoodfacts.resolve", return_value=None):
        response = client.post(
            reverse("add_entry"),
            {"off_code": "999", "grams": 100, "meal": "lunch", "eaten_on": "2026-06-01"},
            HTTP_HX_REQUEST="true",
        )

    assert response.status_code == 200
    assert not Food.objects.filter(off_code="999").exists()
    assert Entry.objects.filter(user=user).count() == 0


def test_delete_entry_only_touches_your_own(client, user, make_entry):
    other = make_entry(grams=50)  # belongs to `user`
    client.force_login(user)

    client.post(reverse("delete_entry", args=[other.pk]))
    assert not Entry.objects.filter(pk=other.pk).exists()


def test_delete_entry_404s_for_someone_elses(client, django_user_model, make_entry):
    victim_entry = make_entry()
    intruder = django_user_model.objects.create_user(username="intruder", password="pw-123456789")
    client.force_login(intruder)

    response = client.post(reverse("delete_entry", args=[victim_entry.pk]))
    assert response.status_code == 404
    assert Entry.objects.filter(pk=victim_entry.pk).exists()
