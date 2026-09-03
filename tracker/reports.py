"""The weekly diet-quality report.

This is the one piece of real domain logic in the app: turning a pile of
logged portions into a readable picture of *how* someone ate over a week —
how processed, how varied, how much fibre / sugar / salt against public
health references. Kept as plain functions with no queries or writes so it
can be unit-tested on synthetic entries.

Reference values (per day):
  * Fibre  >= 25 g   — EFSA adequate intake / WHO recommendation
  * Sugars <  25 g   — WHO free-sugars guidance (we only have *total*
                       sugars from OpenFoodFacts, so this is approximate)
  * Salt   <   5 g   — WHO recommendation
"""

from dataclasses import dataclass, field
from datetime import date, timedelta

FIBER_REF = 25.0
SUGARS_REF = 25.0
SALT_REF = 5.0
DEFAULT_PLANT_TARGET = 30

NUTRISCORE_GRADES = ("a", "b", "c", "d", "e")


@dataclass(frozen=True)
class NutrientAverage:
    key: str
    label: str
    avg: float  # grams per logged day
    reference: float
    direction: str  # "min" -> want >= reference; "max" -> want <= reference

    @property
    def status(self):
        if self.direction == "min":
            return "ok" if self.avg >= self.reference else "low"
        return "ok" if self.avg <= self.reference else "high"

    @property
    def symbol(self):
        return "≥" if self.direction == "min" else "≤"

    @property
    def pct_of_reference(self):
        if not self.reference:
            return 0
        return round(self.avg / self.reference * 100)


@dataclass(frozen=True)
class WeeklyDietReport:
    start: date
    end: date
    entry_count: int
    days_logged: int
    total_kcal: float
    ultra_processed_pct: float | None
    nutriscore_counts: dict
    plants: list = field(default_factory=list)
    plant_target: int = DEFAULT_PLANT_TARGET
    nutrients: list = field(default_factory=list)

    @property
    def distinct_plants(self):
        return len(self.plants)

    @property
    def has_data(self):
        return self.entry_count > 0


def week_bounds(day):
    """The Monday..Sunday range containing `day`."""
    start = day - timedelta(days=day.weekday())
    return start, start + timedelta(days=6)


def build_weekly_report(entries, *, start, end, plant_target=DEFAULT_PLANT_TARGET):
    entries = list(entries)

    days_logged = len({e.eaten_on for e in entries})
    divisor = max(days_logged, 1)

    total_kcal = 0.0
    ultra_kcal = 0.0
    known_kcal = 0.0
    nutriscore_counts = {g: 0 for g in NUTRISCORE_GRADES}
    nutriscore_counts["unknown"] = 0
    totals = {"fiber_g": 0.0, "sugars_g": 0.0, "salt_g": 0.0}
    plants = set()

    for entry in entries:
        food = entry.food
        grams = entry.grams

        kcal = food.amount_of("energy_kcal", grams)
        if kcal is not None:
            total_kcal += kcal
            known_kcal += kcal
            if food.is_ultra_processed:
                ultra_kcal += kcal

        grade = (food.nutriscore_grade or "").lower()
        nutriscore_counts[grade if grade in NUTRISCORE_GRADES else "unknown"] += 1

        for attr in totals:
            amount = food.amount_of(attr, grams)
            if amount is not None:
                totals[attr] += amount

        if food.plant_key:
            plants.add(food.plant_key)

    ultra_pct = round(ultra_kcal / known_kcal * 100, 1) if known_kcal else None

    nutrients = [
        NutrientAverage("fiber", "Fibre", round(totals["fiber_g"] / divisor, 1), FIBER_REF, "min"),
        NutrientAverage(
            "sugars", "Sugars (total)", round(totals["sugars_g"] / divisor, 1), SUGARS_REF, "max"
        ),
        NutrientAverage("salt", "Salt", round(totals["salt_g"] / divisor, 1), SALT_REF, "max"),
    ]

    return WeeklyDietReport(
        start=start,
        end=end,
        entry_count=len(entries),
        days_logged=days_logged,
        total_kcal=round(total_kcal),
        ultra_processed_pct=ultra_pct,
        nutriscore_counts=nutriscore_counts,
        plants=sorted(plants),
        plant_target=plant_target,
        nutrients=nutrients,
    )
