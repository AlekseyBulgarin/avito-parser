from __future__ import annotations

import os
import re
from typing import Protocol

from .models import Product

NOISE_PATTERNS = (
    r"^.*Эксклюзивно в Magic.*$",
    r"^.*Абсолютный эксклюзив.*$",
    r"^.*Абсолютный тренд.*$",
    r"^.*Качество в абсолюте.*$",
)


def clean_source_description(text: str) -> str:
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if any(re.search(pattern, line, flags=re.IGNORECASE) for pattern in NOISE_PATTERNS):
            continue
        line = re.sub(r"^[\s•▫️⚜🆕ℹ️]+", "", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def make_title(product: Product, size: str) -> str:
    title = product.name.strip()
    if size and size not in title and size != "несколько размеров":
        title = f"{title}, размер {size}"
    return title[:100].rstrip(" ,")


def template_description(product: Product, size: str, suffix: str) -> str:
    sizes = size if size != "несколько размеров" else ", ".join(product.sizes)
    details = clean_source_description(product.description)
    blocks = [
        product.name,
        f"Бренд: {product.brand}." if product.brand else "",
        f"Размеры в наличии: {sizes}." if sizes else "",
        "Состояние: новое.",
        details,
        suffix.strip(),
        f"Артикул: {product.sku}.",
    ]
    return "\n\n".join(block for block in blocks if block).strip()[:7500]


class DescriptionGenerator(Protocol):
    def generate(self, product: Product, size: str) -> str: ...


class TemplateDescriptionGenerator:
    def __init__(self, suffix: str):
        self.suffix = suffix

    def generate(self, product: Product, size: str) -> str:
        return template_description(product, size, self.suffix)


class OpenAIDescriptionGenerator:
    def __init__(self, model: str, suffix: str):
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install AI dependencies: uv sync --extra ai") from exc
        self.client = OpenAI()
        self.model = os.getenv("OPENAI_MODEL", model)
        self.suffix = suffix

    def generate(self, product: Product, size: str) -> str:
        prompt = f"""Напиши объявление для Avito на русском языке.
Используй только факты ниже. Не упоминай поставщика Magic Shop, закупочную цену или ИИ.
Не добавляй контакты. Текст до 1800 символов, без кликбейта, с короткими абзацами.

Название: {product.name}
Бренд: {product.brand}
Тип: {product.product_type}
Размеры: {size if size != "несколько размеров" else ", ".join(product.sizes)}
Характеристики:
{clean_source_description(product.description)}

В конце дословно добавь:
{self.suffix}
Артикул: {product.sku}.
"""
        response = self.client.responses.create(model=self.model, input=prompt)
        return response.output_text.strip()[:7500]
