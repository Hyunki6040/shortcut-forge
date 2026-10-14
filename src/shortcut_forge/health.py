"""Apple Health quantity types usable with the "Log Health Sample" action.

The unit table holds the unit people usually write on supplement labels. Writing
"mcg" (or "µg") straight into the action is a trap: on iOS 26/27 the Health app
interprets that unit string as *grams*, so 77.4 mcg of B12 lands as
77,400,000 mcg. The builder therefore converts micro-gram values to milligrams
(value / 1000) before logging. Verified on iPhone, iOS 27, Oct 2026.
"""
from __future__ import annotations

# type identifier (as the Shortcuts action expects it) -> label unit
NUTRIENTS: dict[str, str] = {
    "Vitamin A": "mcg", "Thiamin": "mg", "Riboflavin": "mg", "Niacin": "mg", "Pantothenic Acid": "mg",
    "Vitamin B6": "mg", "Biotin": "mcg", "Folate": "mcg", "Vitamin B12": "mcg", "Vitamin C": "mg",
    "Vitamin D": "mcg", "Vitamin E": "mg", "Vitamin K": "mcg",
    "Calcium": "mg", "Chloride": "mg", "Chromium": "mcg", "Copper": "mg", "Iodine": "mcg", "Iron": "mg",
    "Magnesium": "mg", "Manganese": "mg", "Molybdenum": "mcg", "Phosphorus": "mg", "Potassium": "mg",
    "Selenium": "mcg", "Sodium": "mg", "Zinc": "mg",
    "Caffeine": "mg", "Carbohydrates": "g", "Dietary Cholesterol": "mg", "Dietary Energy": "kcal",
    "Fiber": "g", "Protein": "g", "Sugar": "g", "Total Fat": "g", "Monounsaturated Fat": "g",
    "Polyunsaturated Fat": "g", "Saturated Fat": "g", "Water": "mL",
}

OTHER: dict[str, str] = {
    "Weight": "kg", "Height": "cm", "Body Fat Percentage": "%", "Steps": "count",
    "Mindful Minutes": "min", "Blood Glucose": "mg/dL", "Heart Rate": "count/min",
    "Body Temperature": "degC", "Respiratory Rate": "count/min", "Waist Circumference": "cm",
}

ALL_TYPES: dict[str, str] = {**NUTRIENTS, **OTHER}

MICRO_UNITS = {"mcg", "µg", "μg", "ug"}


def default_unit(sample_type: str) -> str:
    try:
        return ALL_TYPES[sample_type]
    except KeyError as e:  # pragma: no cover - message matters more than coverage
        raise ValueError(
            f"Unknown Health type {sample_type!r}. Known types: {', '.join(sorted(ALL_TYPES))}"
        ) from e


def is_micro(unit: str) -> bool:
    return unit.strip() in MICRO_UNITS
