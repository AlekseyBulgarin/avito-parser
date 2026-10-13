from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULTS: dict[str, Any] = {
    "source": {
        "api_url": "https://magic-shopp.com/api/products",
        "site_url": "https://magic-shopp.com",
        "category_slug": "odezhda",
        "gender": "male",
        "page_size": 100,
        "timeout_seconds": 30,
        "request_delay_seconds": 0.35,
    },
    "pricing": {
        "bands": [
            {"max_price": 5000, "markup": 0.60},
            {"max_price": 10000, "markup": 0.45},
            {"max_price": 20000, "markup": 0.35},
            {"max_price": 40000, "markup": 0.30},
            {"max_price": None, "markup": 0.25},
        ],
        "rounding_ending": 990,
    },
    "seller": {
        "address": "",
        "contact_phone": "",
        "contact_method": "В сообщениях",
        "manager_name": "",
        "ad_type": "Товар приобретен на продажу",
        "condition": "Новое",
    },
    "description": {
        "ai_enabled": False,
        "model": "gpt-6-astra",
        "suffix": (
            "В наличии. Перед заказом уточните актуальный размер.\n"
            "Отправка по России. Дополнительные фото и замеры — по запросу."
        ),
    },
    "export": {
        "output_dir": "output",
        "template_path": None,
        "split_by_size": False,
        "download_images": False,
        "max_images": 10,
        "image_separator": "|",
    },
}


@dataclass(slots=True)
class Settings:
    data: dict[str, Any]
    root: Path

    def section(self, name: str) -> dict[str, Any]:
        return self.data[name]


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def load_settings(path: str | Path = "config.yaml") -> Settings:
    config_path = Path(path).resolve()
    override: dict[str, Any] = {}
    if config_path.exists():
        override = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return Settings(data=_merge(DEFAULTS, override), root=config_path.parent)
