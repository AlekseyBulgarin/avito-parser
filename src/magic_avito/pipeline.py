from __future__ import annotations

from .client import MagicShopClient
from .config import Settings
from .descriptions import OpenAIDescriptionGenerator, TemplateDescriptionGenerator, make_title
from .exporters import export_products, export_xlsx, export_xml, write_validation_report
from .mapping import apparel_type
from .models import Listing, Product
from .pricing import calculate_price
from .state import StateStore


def build_listings(
    products: list[Product], settings: Settings, force_ai: bool | None = None
) -> list[Listing]:
    description_settings = settings.section("description")
    ai_enabled = description_settings["ai_enabled"] if force_ai is None else force_ai
    generator = (
        OpenAIDescriptionGenerator(description_settings["model"], description_settings["suffix"])
        if ai_enabled
        else TemplateDescriptionGenerator(description_settings["suffix"])
    )
    export = settings.section("export")
    split_by_size = bool(export["split_by_size"])
    listings: list[Listing] = []
    for product in products:
        variants = product.sizes if split_by_size else ["несколько размеров"]
        for size in variants:
            listing_id = f"magic-{product.sku}-{size}" if split_by_size else f"magic-{product.sku}"
            display_size = size if split_by_size else "|".join(product.sizes)
            listings.append(
                Listing(
                    listing_id=listing_id,
                    product=product,
                    size=display_size,
                    title=make_title(product, size),
                    description=generator.generate(product, size),
                    selling_price=calculate_price(
                        product.source_price, settings.section("pricing")
                    ),
                    image_urls=product.photo_urls(
                        settings.section("source")["site_url"], int(export["max_images"])
                    ),
                    apparel_type=apparel_type(product.product_type),
                )
            )
    return listings


def run_pipeline(
    settings: Settings,
    limit: int | None = None,
    force_ai: bool | None = None,
    force_download_images: bool | None = None,
    template_path: str | None = None,
) -> dict:
    export = settings.section("export")
    output_dir = (settings.root / export["output_dir"]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    with MagicShopClient(settings.section("source")) as client:
        products = client.fetch_products(limit=limit)
        download_images = (
            export["download_images"] if force_download_images is None else force_download_images
        )
        if download_images:
            for product in products:
                client.download_images(product, output_dir / "images", int(export["max_images"]))

    store = StateStore((settings.root / "data" / "products.db").resolve())
    try:
        changes = store.upsert_all(products, complete_snapshot=limit is None)
    finally:
        store.close()

    listings = build_listings(products, settings, force_ai=force_ai)
    template_value = template_path or export.get("template_path")
    template = (settings.root / template_value).resolve() if template_value else None
    if template and not template.exists():
        raise FileNotFoundError(f"Avito template not found: {template}")

    export_products(products, output_dir)
    export_xlsx(
        listings,
        output_dir / "avito_ready.xlsx",
        settings.section("seller"),
        export,
        template,
    )
    export_xml(listings, output_dir / "avito_feed.xml", settings.section("seller"))
    validation = write_validation_report(
        listings, settings.section("seller"), output_dir / "validation_report.json"
    )
    return {
        "products": len(products),
        "listings": len(listings),
        "changes": changes,
        "validation": validation,
        "output_dir": str(output_dir),
    }
