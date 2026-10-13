from magic_avito.pricing import calculate_price, round_to_ending, select_markup

PRICING = {
    "bands": [
        {"max_price": 5000, "markup": 0.60},
        {"max_price": 10000, "markup": 0.45},
        {"max_price": 20000, "markup": 0.35},
        {"max_price": 40000, "markup": 0.30},
        {"max_price": None, "markup": 0.25},
    ],
    "rounding_ending": 990,
}


def test_markup_boundaries():
    assert select_markup(5000, PRICING["bands"]) == 0.60
    assert select_markup(5001, PRICING["bands"]) == 0.45
    assert select_markup(40001, PRICING["bands"]) == 0.25


def test_rounding_to_990():
    assert round_to_ending(18_630, 990) == 18_990
    assert round_to_ending(18_990, 990) == 18_990
    assert round_to_ending(19_000, 990) == 19_990


def test_price_examples():
    assert calculate_price(4_000, PRICING) == 6_990
    assert calculate_price(8_900, PRICING) == 12_990
    assert calculate_price(13_800, PRICING) == 18_990
