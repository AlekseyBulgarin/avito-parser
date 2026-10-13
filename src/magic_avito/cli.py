from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from .config import load_settings
from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="magic-avito",
        description="Собирает Magic Shop и формирует Excel/XML для автозагрузки Avito.",
    )
    parser.add_argument("--config", default="config.yaml", help="Путь к YAML-конфигурации")
    parser.add_argument(
        "--limit", type=int, default=None, help="Ограничить число товаров для теста"
    )
    parser.add_argument("--ai", action="store_true", help="Генерировать описания через OpenAI API")
    parser.add_argument("--download-images", action="store_true", help="Скачать фото локально")
    parser.add_argument(
        "--verify-images",
        action="store_true",
        help="Проверить доступность всех ссылок на фото",
    )
    parser.add_argument("--template", default=None, help="Путь к официальному XLSX-шаблону Avito")
    parser.add_argument(
        "--cached-products",
        default=None,
        help="Собрать выгрузку из ранее сохранённого output/products.json",
    )
    parser.add_argument(
        "--cached-image-audit",
        default=None,
        help="Повторно использовать завершённый image_audit.json при недоступности фотохоста",
    )
    parser.add_argument(
        "--init-config", action="store_true", help="Создать config.yaml из config.example.yaml"
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.init_config:
        source = Path("config.example.yaml")
        target = Path(args.config)
        if target.exists():
            raise SystemExit(f"Файл уже существует: {target}")
        shutil.copyfile(source, target)
        print(f"Создан {target}. Заполните seller.address и при необходимости телефон.")
        return 0

    result = run_pipeline(
        load_settings(args.config),
        limit=args.limit,
        force_ai=True if args.ai else None,
        force_download_images=True if args.download_images else None,
        force_verify_images=True if args.verify_images else None,
        template_path=args.template,
        cached_products_path=args.cached_products,
        cached_image_audit_path=args.cached_image_audit,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["validation"]["valid"]:
        print("Выгрузка создана, но проверка обнаружила ошибки; см. validation_report.json.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
