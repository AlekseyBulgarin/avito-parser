from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

import httpx

from .models import Listing


def image_url_fingerprint(listings: list[Listing]) -> tuple[int, str]:
    urls = sorted({url for listing in listings for url in listing.image_urls})
    digest = hashlib.sha256("\n".join(urls).encode("utf-8")).hexdigest()
    return len(urls), digest


async def _probe(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    url: str,
    retry_attempts: int,
) -> dict[str, object]:
    last_result: dict[str, object] | None = None
    for attempt in range(max(1, retry_attempts)):
        try:
            async with (
                semaphore,
                client.stream("GET", url, headers={"Range": "bytes=0-31"}) as response,
            ):
                content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                sample = b""
                async for chunk in response.aiter_bytes():
                    sample += chunk
                    if len(sample) >= 16:
                        break
                is_jpeg = sample.startswith(b"\xff\xd8\xff")
                is_png = sample.startswith(b"\x89PNG\r\n\x1a\n")
                valid = (
                    response.status_code in {200, 206}
                    and content_type in {"image/jpeg", "image/png"}
                    and (is_jpeg or is_png)
                )
                reason = ""
                if response.status_code not in {200, 206}:
                    reason = f"HTTP {response.status_code}"
                elif content_type not in {"image/jpeg", "image/png"}:
                    reason = f"Content-Type {content_type or 'не указан'}"
                elif not (is_jpeg or is_png):
                    reason = "содержимое не похоже на JPEG/PNG"
                content_range = response.headers.get("content-range", "")
                total_size = None
                if "/" in content_range:
                    total_value = content_range.rsplit("/", 1)[-1]
                    if total_value.isdigit():
                        total_size = int(total_value)
                last_result = {
                    "url": url,
                    "valid": valid,
                    "status": response.status_code,
                    "content_type": content_type,
                    "content_length": total_size,
                    "reason": reason,
                }
                if valid or response.status_code not in {408, 425, 429, 500, 502, 503, 504}:
                    return last_result
        except (httpx.HTTPError, ValueError) as exc:
            last_result = {
                "url": url,
                "valid": False,
                "status": None,
                "content_type": "",
                "content_length": None,
                "reason": f"{type(exc).__name__}: {exc}".rstrip(),
            }
        if attempt + 1 < max(1, retry_attempts):
            await asyncio.sleep(0.5 * (2**attempt))
    return last_result or {
        "url": url,
        "valid": False,
        "status": None,
        "content_type": "",
        "content_length": None,
        "reason": "неизвестная ошибка проверки",
    }


async def _run_audit(
    urls: list[str], timeout_seconds: float, concurrency: int, retry_attempts: int
) -> list[dict[str, object]]:
    semaphore = asyncio.Semaphore(max(1, concurrency))
    async with httpx.AsyncClient(
        timeout=timeout_seconds,
        follow_redirects=True,
        headers={"User-Agent": "MagicAvitoCatalogBot/0.2 (+image availability audit)"},
    ) as client:
        return await asyncio.gather(
            *(_probe(client, semaphore, url, retry_attempts) for url in urls)
        )


def audit_listing_images(
    listings: list[Listing],
    path: Path,
    timeout_seconds: float = 30,
    concurrency: int = 8,
    retry_attempts: int = 3,
) -> dict:
    urls = list(dict.fromkeys(url for listing in listings for url in listing.image_urls))
    checks = asyncio.run(_run_audit(urls, timeout_seconds, concurrency, retry_attempts))
    failures = [check for check in checks if not check["valid"]]
    report = {
        "total_urls": len(urls),
        "urls_sha256": image_url_fingerprint(listings)[1],
        "valid_urls": len(urls) - len(failures),
        "invalid_urls": len(failures),
        "failures": failures,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
