from magic_avito.models import Product


def test_product_from_api_and_photo_urls():
    product = Product.from_api(
        {
            "sku": "00001",
            "name": "Куртка",
            "brand": "Brand",
            "description": "Описание",
            "price": 10000,
            "gender": "male",
            "productType": "Куртка",
            "sizes": ["M"],
            "photos": ["1.jpg", "2.jpg"],
            "updatedAt": "2026-10-13T10:00:00.000Z",
            "category": {"name": "Одежда"},
        }
    )
    urls = product.photo_urls("https://magic-shopp.com", 10)
    assert len(urls) == 2
    assert urls[0].startswith("https://magic-shopp.com/uploads/products/00001/1.jpg?v=")
