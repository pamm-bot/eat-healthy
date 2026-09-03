"""A thin client for the OpenFoodFacts API.

It returns plain normalised dicts (never model instances), so it can be
unit-tested against canned JSON and the callers decide what to persist.
Every network call has a timeout and swallows request errors, returning an
empty result rather than propagating an exception into a view.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://world.openfoodfacts.org"
TIMEOUT = 6  # seconds, connect + read
FIELDS = "code,product_name,brands,nutriments,nova_group,nutriscore_grade,categories_tags"

# Whole plant foods we recognise for the "how many different plants this week"
# metric. Keys are substrings looked for in a product's category tags; the
# value is the normalised plant. Deliberately small and imperfect.
PLANT_KEYWORDS = {
    "spinach": "spinach",
    "kale": "kale",
    "lettuce": "lettuce",
    "rocket": "rocket",
    "arugula": "rocket",
    "chard": "chard",
    "cabbage": "cabbage",
    "broccoli": "broccoli",
    "cauliflower": "cauliflower",
    "carrot": "carrot",
    "tomato": "tomato",
    "pepper": "pepper",
    "courgette": "courgette",
    "zucchini": "courgette",
    "aubergine": "aubergine",
    "eggplant": "aubergine",
    "onion": "onion",
    "garlic": "garlic",
    "leek": "leek",
    "cucumber": "cucumber",
    "mushroom": "mushroom",
    "potato": "potato",
    "sweet-potato": "sweet potato",
    "beetroot": "beetroot",
    "pumpkin": "pumpkin",
    "squash": "squash",
    "pea": "pea",
    "green-bean": "green bean",
    "chickpea": "chickpea",
    "chick-pea": "chickpea",
    "lentil": "lentil",
    "black-bean": "black bean",
    "kidney-bean": "kidney bean",
    "white-bean": "white bean",
    "bean": "bean",
    "soy": "soy",
    "tofu": "soy",
    "apple": "apple",
    "banana": "banana",
    "orange": "orange",
    "lemon": "lemon",
    "berry": "berry",
    "strawberr": "strawberry",
    "blueberr": "blueberry",
    "raspberr": "raspberry",
    "grape": "grape",
    "pear": "pear",
    "peach": "peach",
    "plum": "plum",
    "kiwi": "kiwi",
    "mango": "mango",
    "pineapple": "pineapple",
    "avocado": "avocado",
    "almond": "almond",
    "walnut": "walnut",
    "cashew": "cashew",
    "hazelnut": "hazelnut",
    "peanut": "peanut",
    "pistachio": "pistachio",
    "oat": "oat",
    "barley": "barley",
    "buckwheat": "buckwheat",
    "quinoa": "quinoa",
    "brown-rice": "brown rice",
    "whole-wheat": "whole wheat",
    "wholemeal": "whole wheat",
    "rye": "rye",
    "chia": "chia",
    "flaxseed": "flaxseed",
    "linseed": "flaxseed",
    "sunflower-seed": "sunflower seed",
    "pumpkin-seed": "pumpkin seed",
}


def _headers():
    return {"User-Agent": settings.OFF_USER_AGENT}


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def plant_key_from_tags(tags):
    """Best-effort normalised plant name from OpenFoodFacts category tags."""
    found = ""
    for tag in tags or []:
        slug = tag.split(":")[-1].replace("_", "-").lower()
        for keyword, key in PLANT_KEYWORDS.items():
            if keyword in slug:
                found = key  # keep the last (most specific) match
    return found


def normalise(product):
    """Turn a raw OpenFoodFacts product dict into the shape our Food model uses.

    Returns None for products with no code or no usable name — the API has a
    lot of those and they only clutter search results.
    """
    if not product or not product.get("code"):
        return None

    name = (product.get("product_name") or "").strip()
    if not name:
        return None

    nutriments = product.get("nutriments") or {}
    nova = product.get("nova_group")
    try:
        nova = int(nova) if nova is not None else None
    except (TypeError, ValueError):
        nova = None

    grade = (product.get("nutriscore_grade") or "").strip().lower()[:1]

    return {
        "off_code": str(product["code"]),
        "name": name,
        "brand": (product.get("brands") or "").split(",")[0].strip(),
        "nova_group": nova if nova in (1, 2, 3, 4) else None,
        "nutriscore_grade": grade if grade in ("a", "b", "c", "d", "e") else "",
        "energy_kcal": _num(nutriments.get("energy-kcal_100g")),
        "protein_g": _num(nutriments.get("proteins_100g")),
        "fiber_g": _num(nutriments.get("fiber_100g")),
        "sugars_g": _num(nutriments.get("sugars_100g")),
        "salt_g": _num(nutriments.get("salt_100g")),
        "plant_key": plant_key_from_tags(product.get("categories_tags")),
    }


def search(query, limit=20):
    """Search products by name. Returns a list of normalised dicts (possibly empty)."""
    query = (query or "").strip()
    if not query:
        return []

    try:
        response = requests.get(
            f"{BASE_URL}/cgi/search.pl",
            params={
                "search_terms": query,
                "json": 1,
                "page_size": limit,
                "fields": FIELDS,
            },
            headers=_headers(),
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        products = response.json().get("products", [])
    except (requests.RequestException, ValueError) as exc:
        logger.warning("OpenFoodFacts search failed for %r: %s", query, exc)
        return []

    return [item for item in (normalise(p) for p in products) if item]


def get_by_barcode(code):
    """Look up a single product by barcode. Returns a normalised dict or None."""
    code = (code or "").strip()
    if not code:
        return None

    try:
        response = requests.get(
            f"{BASE_URL}/api/v2/product/{code}.json",
            params={"fields": FIELDS},
            headers=_headers(),
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("OpenFoodFacts lookup failed for %r: %s", code, exc)
        return None

    if payload.get("status") != 1:
        return None
    return normalise(payload.get("product"))
