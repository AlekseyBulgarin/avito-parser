$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

if (-not (Test-Path -LiteralPath "config.yaml")) {
    Copy-Item -LiteralPath "config.example.yaml" -Destination "config.yaml"
    Write-Host "Создан config.yaml. Заполните раздел seller и запустите файл снова."
    exit 1
}

uv sync
uv run magic-avito --config config.yaml

