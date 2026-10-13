from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class Product:
    sku: str
    name: str
    brand: str
    description: str
    source_price: int
    gender: str
    category: str
    product_type: str
    sizes: list[str] = field(default_factory=list)
    photos: list[str] = field(default_factory=list)
    updated_at: str | None = None

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> Product:
        return cls(
            sku=str(raw["sku"]),
            name=str(raw["name"]).strip(),
            brand=str(raw.get("brand") or "").strip(),
            description=str(raw.get("description") or "").strip(),
            source_price=int(raw["price"]),
            gender=str(raw.get("gender") or ""),
            category=str((raw.get("category") or {}).get("name") or "Одежда"),
            product_type=str(raw.get("productType") or "Другое").strip(),
            sizes=[str(value).strip() for value in raw.get("sizes") or [] if str(value).strip()],
            photos=[str(value).strip() for value in raw.get("photos") or [] if str(value).strip()],
            updated_at=raw.get("updatedAt"),
        )

    def photo_urls(self, site_url: str, max_images: int = 10) -> list[str]:
        version = ""
        if self.updated_at:
            try:
                timestamp = int(datetime.fromisoformat(self.updated_at).timestamp() * 1000)
                version = f"?v={timestamp}"
            except ValueError:
                version = ""
        base = site_url.rstrip("/")
        return [
            f"{base}/uploads/products/{self.sku}/{photo}{version}"
            for photo in self.photos[:max_images]
        ]


@dataclass(slots=True)
class Listing:
    listing_id: str
    product: Product
    size: str
    title: str
    description: str
    selling_price: int
    image_urls: list[str]
    apparel: str
    apparel_type: str
    unavailable_image_urls: list[str] = field(default_factory=list)
