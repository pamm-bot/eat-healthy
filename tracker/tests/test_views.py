from datetime import date
from unittest.mock import patch

import pytest
from django.urls import reverse

from tracker.models import Entry, Food

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


def test_food_search_renders_results(client, user):
    client.force_login(user)
    with patch("tracker.views.openfoodfacts.search", return_value=[PRODUCT]) as mocked:
        response = client.get(reverse("food_search"), {"q": "oats"})
    mocked.assert_called_once_with("oats")
    assert b"Rolled Oats" in response.content


def test_add_entry_creates_the_food_once_and_logs_the_portion(client, user):
    client.force_login(user)
    payload = {**PRODUCT, "grams": 80, "meal": "breakfast", "eaten_on": "2026-06-01"}

    client.post(reverse("add_entry"), payload)
    client.post(reverse("add_entry"), payload)  # same food again

    assert Food.objects.filter(off_code="555").count() == 1
    entries = Entry.objects.filter(user=user)
    assert entries.count() == 2
    assert entries.first().grams == 80
    assert entries.first().eaten_on == date(2026, 6, 1)


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
