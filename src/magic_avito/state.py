from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from .models import Product


def product_hash(product: Product) -> str:
    payload = {
        "name": product.name,
        "price": product.source_price,
        "sizes": product.sizes,
        "description": product.description,
        "photos": product.photos,
        "updated_at": product.updated_at,
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


class StateStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                sku TEXT PRIMARY KEY,
                source_hash TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                last_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.connection.commit()

    def upsert_all(self, products: list[Product], complete_snapshot: bool = True) -> dict[str, int]:
        existing = {
            row[0]: row[1]
            for row in self.connection.execute("SELECT sku, source_hash FROM products").fetchall()
        }
        added = changed = unchanged = 0
        for product in products:
            digest = product_hash(product)
            if product.sku not in existing:
                added += 1
            elif existing[product.sku] != digest:
                changed += 1
            else:
                unchanged += 1
            self.connection.execute(
                """
                INSERT INTO products (sku, source_hash, payload_json, last_seen)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(sku) DO UPDATE SET
                    source_hash=excluded.source_hash,
                    payload_json=excluded.payload_json,
                    last_seen=CURRENT_TIMESTAMP
                """,
                (product.sku, digest, json.dumps(asdict(product), ensure_ascii=False)),
            )
        self.connection.commit()
        removed = (
            len(set(existing) - {product.sku for product in products}) if complete_snapshot else 0
        )
        return {"added": added, "changed": changed, "unchanged": unchanged, "removed": removed}

    def close(self) -> None:
        self.connection.close()
