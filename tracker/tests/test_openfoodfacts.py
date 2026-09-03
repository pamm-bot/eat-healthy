from unittest.mock import patch

import requests

from tracker import openfoodfacts

SEARCH_PAYLOAD = {
    "products": [
        {
            "code": "111",
            "product_name": "Baby Spinach",
            "brands": "Green Farm, Other",
            "nova_group": 1,
            "nutriscore_grade": "A",
            "nutriments": {
                "energy-kcal_100g": 23,
                "proteins_100g": 2.9,
                "fiber_100g": 2.2,
                "sugars_100g": 0.4,
                "salt_100g": 0.08,
            },
            "categories_tags": ["en:vegetables", "en:leaf-vegetables", "en:spinaches"],
        },
        {"code": "", "product_name": "no code"},  # dropped by normalise
    ]
}

BARCODE_PAYLOAD = {
    "status": 1,
    "product": {
        "code": "737628064502",
        "product_name": "Instant Noodles",
        "brands": "NoodleCo",
        "nova_group": 4,
        "nutriscore_grade": "d",
        "nutriments": {"energy-kcal_100g": 450, "salt_100g": 3.1},
        "categories_tags": ["en:meals", "en:noodles"],
    },
}


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        pass


def test_search_normalises_products():
    with patch("tracker.openfoodfacts.requests.get", return_value=FakeResponse(SEARCH_PAYLOAD)):
        results = openfoodfacts.search("spinach")

    assert len(results) == 1
    item = results[0]
    assert item["off_code"] == "111"
    assert item["name"] == "Baby Spinach"
    assert item["brand"] == "Green Farm"  # first brand only
    assert item["nova_group"] == 1
    assert item["nutriscore_grade"] == "a"
    assert item["energy_kcal"] == 23.0
    assert item["plant_key"] == "spinach"


def test_search_returns_empty_on_a_network_error():
    with patch("tracker.openfoodfacts.requests.get", side_effect=requests.Timeout):
        assert openfoodfacts.search("spinach") == []


def test_search_ignores_a_blank_query():
    assert openfoodfacts.search("   ") == []


def test_get_by_barcode_normalises_a_single_product():
    with patch("tracker.openfoodfacts.requests.get", return_value=FakeResponse(BARCODE_PAYLOAD)):
        item = openfoodfacts.get_by_barcode("737628064502")

    assert item["name"] == "Instant Noodles"
    assert item["nova_group"] == 4
    assert item["salt_g"] == 3.1
    assert item["plant_key"] == ""  # not a whole plant food


def test_get_by_barcode_returns_none_when_product_is_missing():
    with patch("tracker.openfoodfacts.requests.get", return_value=FakeResponse({"status": 0})):
        assert openfoodfacts.get_by_barcode("000") is None


def test_plant_key_from_tags_picks_the_most_specific_match():
    tags = ["en:legumes", "en:pulses", "en:chickpeas"]
    assert openfoodfacts.plant_key_from_tags(tags) == "chickpea"
