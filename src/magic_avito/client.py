from __future__ import annotations

import time
from pathlib import Path
from typing import Self
from urllib.parse import urlsplit

import httpx

from .models import Product


class MagicShopClient:
    def __init__(self, source: dict):
        self.source = source
        self.client = httpx.Client(
            timeout=float(source["timeout_seconds"]),
            follow_redirects=True,
            headers={
                "User-Agent": "MagicAvitoCatalogBot/0.1 (+catalog synchronization; polite rate limit)",
                "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
            },
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args) -> None:
        self.close()

    def _get(self, url: str, **kwargs) -> httpx.Response:
        attempts = max(1, int(self.source.get("request_retry_attempts", 3)))
        last_error: httpx.HTTPError | None = None
        for attempt in range(attempts):
            try:
                response = self.client.get(url, **kwargs)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code not in {408, 425, 429, 500, 502, 503, 504}:
                    raise
            except httpx.HTTPError as exc:
                last_error = exc
            if attempt + 1 < attempts:
                time.sleep(0.75 * (2**attempt))
        if last_error is not None:
            raise last_error
        raise RuntimeError("Запрос каталога завершился без ответа")

    def fetch_products(self, limit: int | None = None) -> list[Product]:
        page_size = int(self.source["page_size"])
        products: list[Product] = []
        skip = 0
        total = None

        while total is None or skip < total:
            take = page_size if limit is None else min(page_size, max(limit - len(products), 0))
            if take <= 0:
                break
            response = self._get(
                self.source["api_url"],
                params={
                    "slug": self.source["category_slug"],
                    "gender": self.source["gender"],
                    "skip": skip,
                    "take": take,
                },
            )
            payload = response.json()
            batch = [Product.from_api(item) for item in payload.get("products", [])]
            total = int(payload.get("total", len(batch)))
            products.extend(batch)
            skip += len(batch)
            if not batch or (limit is not None and len(products) >= limit):
                break
            time.sleep(float(self.source.get("request_delay_seconds", 0)))

        return products[:limit] if limit is not None else products

    def download_images(self, product: Product, target_root: Path, max_images: int) -> list[Path]:
        paths: list[Path] = []
        target = target_root / product.sku
        target.mkdir(parents=True, exist_ok=True)
        urls = product.photo_urls(self.source["site_url"], max_images)
        for index, url in enumerate(urls, start=1):
            suffix = Path(urlsplit(url).path).suffix.lower() or ".jpg"
            path = target / f"{index:02d}{suffix}"
            with self.client.stream("GET", url) as response:
                response.raise_for_status()
                with path.open("wb") as stream:
                    for chunk in response.iter_bytes():
                        stream.write(chunk)
            paths.append(path)
            time.sleep(float(self.source.get("request_delay_seconds", 0)))
        return paths
