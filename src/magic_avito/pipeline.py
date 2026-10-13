from __future__ import annotations

import json

from .client import MagicShopClient
from .config import Settings
from .descriptions import OpenAIDescriptionGenerator, TemplateDescriptionGenerator, make_title
from .exporters import export_products, export_xlsx, export_xml, write_validation_report
from .image_checks import audit_listing_images, image_url_fingerprint
from .mapping import apparel_fields
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
        apparel, apparel_type = apparel_fields(
            product.product_type, f"{product.name}\n{product.description}"
        )
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
                    apparel=apparel,
                    apparel_type=apparel_type,
                )
            )
    return listings


def run_pipeline(
    settings: Settings,
    limit: int | None = None,
    force_ai: bool | None = None,
    force_download_images: bool | None = None,
    force_verify_images: bool | None = None,
    template_path: str | None = None,
    cached_products_path: str | None = None,
    cached_image_audit_path: str | None = None,
) -> dict:
    export = settings.section("export")
    output_dir = (settings.root / export["output_dir"]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if cached_products_path:
        cache_path = (settings.root / cached_products_path).resolve()
        cached_payload = json.loads(cache_path.read_text(encoding="utf-8"))
        products = [Product(**item) for item in cached_payload]
        if limit is not None:
            products = products[:limit]
        source_mode = f"cache:{cache_path}"
    else:
        with MagicShopClient(settings.section("source")) as client:
            products = client.fetch_products(limit=limit)
            download_images = (
                export["download_images"]
                if force_download_images is None
                else force_download_images
            )
            if download_images:
                for product in products:
                    client.download_images(
                        product, output_dir / "images", int(export["max_images"])
                    )
        source_mode = "live_api"

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

    verify_images = export.get("verify_images", False)
    if force_verify_images is not None:
        verify_images = force_verify_images
    image_audit = None
    if verify_images:
        if cached_image_audit_path:
            audit_cache_path = (settings.root / cached_image_audit_path).resolve()
            image_audit = json.loads(audit_cache_path.read_text(encoding="utf-8"))
            url_count, url_fingerprint = image_url_fingerprint(listings)
            if (
                image_audit.get("total_urls") != url_count
                or image_audit.get("urls_sha256") != url_fingerprint
            ):
                raise ValueError("Сохранённый аудит фотографий относится к другому набору URL")
            image_audit["audit_mode"] = f"cache:{audit_cache_path}"
        else:
            image_audit = audit_listing_images(
                listings,
                output_dir / "image_audit.json",
                timeout_seconds=float(settings.section("source")["timeout_seconds"]),
                concurrency=int(export.get("image_concurrency", 8)),
                retry_attempts=int(export.get("image_retry_attempts", 3)),
            )
            image_audit["audit_mode"] = "live"
        failed_urls = {str(item["url"]) for item in image_audit["failures"]}
        retained_listings: list[Listing] = []
        excluded_listing_ids: list[str] = []
        removed_occurrences = 0
        for listing in listings:
            listing.unavailable_image_urls = [
                url for url in listing.image_urls if url in failed_urls
            ]
            removed_occurrences += len(listing.unavailable_image_urls)
            listing.image_urls = [url for url in listing.image_urls if url not in failed_urls]
            if listing.image_urls:
                retained_listings.append(listing)
            else:
                excluded_listing_ids.append(listing.listing_id)
        listings = retained_listings
        image_audit["removed_from_export"] = removed_occurrences
        image_audit["excluded_listing_ids"] = excluded_listing_ids
        (output_dir / "image_audit.json").write_text(
            json.dumps(image_audit, ensure_ascii=False, indent=2), encoding="utf-8"
        )

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
        listings,
        settings.section("seller"),
        output_dir / "validation_report.json",
        max_images=int(export["max_images"]),
        image_audit=image_audit,
    )
    return {
        "products": len(products),
        "listings": len(listings),
        "source_mode": source_mode,
        "changes": changes,
        "validation": validation,
        "image_audit": image_audit,
        "output_dir": str(output_dir),
    }
