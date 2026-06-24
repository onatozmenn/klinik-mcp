"""Pure clinical calculation helpers — formula-based, no external data.

These functions implement well-established clinical formulas only. They never
invent drug-specific doses; callers supply the inputs.
"""
from __future__ import annotations

import math


def cockcroft_gault(
    age_years: float,
    weight_kg: float,
    serum_creatinine_mg_dl: float,
    is_female: bool,
) -> float:
    """Creatinine clearance (mL/min) via the Cockcroft–Gault equation."""
    if min(age_years, weight_kg, serum_creatinine_mg_dl) <= 0:
        raise ValueError("yaş, kilo ve kreatinin pozitif olmalı")
    crcl = ((140 - age_years) * weight_kg) / (72 * serum_creatinine_mg_dl)
    return crcl * 0.85 if is_female else crcl


def renal_function_category(crcl_ml_min: float) -> str:
    """Map a creatinine clearance value to a coarse renal-function band."""
    if crcl_ml_min >= 90:
        return "Normal (≥90 mL/dk)"
    if crcl_ml_min >= 60:
        return "Hafif azalma (60–89 mL/dk)"
    if crcl_ml_min >= 30:
        return "Orta azalma (30–59 mL/dk)"
    if crcl_ml_min >= 15:
        return "Ciddi azalma (15–29 mL/dk)"
    return "Böbrek yetmezliği (<15 mL/dk)"


def mosteller_bsa(height_cm: float, weight_kg: float) -> float:
    """Body surface area (m²) via the Mosteller formula."""
    if min(height_cm, weight_kg) <= 0:
        raise ValueError("boy ve kilo pozitif olmalı")
    return math.sqrt((height_cm * weight_kg) / 3600)
