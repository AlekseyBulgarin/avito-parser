from magic_avito.descriptions import clean_source_description, make_title, template_description
from magic_avito.models import Product


def product() -> Product:
    return Product(
        sku="02867",
        name="Рубашка Tommy Jeans Regular Fit",
        brand="Tommy Jeans",
        description="⚜ Эксклюзивно в Magic\nРазмеры L • XL\n• Материал Чистый хлопок",
        source_price=6900,
        gender="male",
        category="Одежда",
        product_type="Рубашка",
        sizes=["L", "XL"],
        photos=["1.jpg"],
    )


def test_supplier_marketing_is_removed():
    cleaned = clean_source_description(product().description)
    assert "Magic" not in cleaned
    assert "Материал Чистый хлопок" in cleaned


def test_title_and_description_limits():
    item = product()
    assert len(make_title(item, "L")) <= 100
    text = template_description(item, "несколько размеров", "Доставка по России.")
    assert "L, XL" in text
    assert "Артикул: 02867" in text
