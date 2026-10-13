from __future__ import annotations

import math


def select_markup(source_price: int, bands: list[dict]) -> float:
    for band in bands:
        maximum = band.get("max_price")
        if maximum is None or source_price <= int(maximum):
            return float(band["markup"])
    raise ValueError("Pricing bands do not contain a catch-all rule")


def round_to_ending(value: float, ending: int = 990) -> int:
    if not 0 <= ending <= 999:
        raise ValueError("rounding_ending must be between 0 and 999")
    base = math.floor(value / 1000) * 1000 + ending
    if base + 1e-9 < value:
        base += 1000
    return int(base)


def calculate_price(source_price: int, pricing: dict) -> int:
    markup = select_markup(source_price, pricing["bands"])
    return round_to_ending(source_price * (1 + markup), int(pricing["rounding_ending"]))
