"""Rutas base del proyecto (independientes del directorio desde donde se ejecuta)."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"


def asset_path(*parts):
    return ASSETS_DIR.joinpath(*parts)
