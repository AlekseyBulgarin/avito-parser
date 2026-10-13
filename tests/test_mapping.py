from magic_avito.mapping import apparel_fields


def test_outerwear_taxonomy():
    assert apparel_fields("Ветровка") == (
        "Верхняя одежда",
        "Лёгкие куртки и ветровки",
    )
    assert apparel_fields("Пуховик") == (
        "Верхняя одежда",
        "Зимние куртки и пуховики",
    )
    assert apparel_fields("Куртка", "Утеплённая puffer jacket") == (
        "Верхняя одежда",
        "Зимние куртки и пуховики",
    )
    assert apparel_fields("Куртка", "Джинсовая denim jacket") == (
        "Верхняя одежда",
        "Джинсовые куртки",
    )


def test_tops_taxonomy():
    assert apparel_fields("Худи") == ("Кофты и футболки", "Толстовки")
    assert apparel_fields("Футболка") == ("Кофты и футболки", "Футболки")
    assert apparel_fields("Джемпер") == ("Кофты и футболки", "Свитеры")


def test_unknown_taxonomy_is_explicit():
    assert apparel_fields("Неизвестно") == ("Другое", "Другое")
