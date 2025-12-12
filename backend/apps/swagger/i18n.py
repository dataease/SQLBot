# Author: Junjun
# Date: 2025/12/11
# i18n.py
import json
from pathlib import Path
from typing import Dict

i18n_list = ["en", "zh"]

# placeholder prefix（trans key prefix）
PLACEHOLDER_PREFIX = "PLACEHOLDER_"

# default lang
DEFAULT_LANG = "en"

LOCALES_DIR = Path(__file__).parent / "locales"
_translations_cache: Dict[str, Dict[str, str]] = {}


def load_translation(lang: str) -> Dict[str, str]:
    """Load translations for the specified language from a JSON file"""
    if lang in _translations_cache:
        return _translations_cache[lang]

    file_path = LOCALES_DIR / f"{lang}.json"
    if not file_path.exists():
        if lang == DEFAULT_LANG:
            raise FileNotFoundError(f"Default language file not found: {file_path}")
        # If the non-default language is missing, fall back to the default language
        return load_translation(DEFAULT_LANG)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError(f"Translation file {file_path} must be a JSON object")
            _translations_cache[lang] = data
            return data
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {file_path}: {e}")


# group tags
tags_metadata = [
    {
        "name": "Datasource",
        "description": f"{PLACEHOLDER_PREFIX}ds_api"
    },
    {
        "name": "system_user",
        "description": f"{PLACEHOLDER_PREFIX}system_user_api"
    },
    {
        "name": "system_ws",
        "description": f"{PLACEHOLDER_PREFIX}system_ws_api"
    },
    {
        "name": "system_model",
        "description": f"{PLACEHOLDER_PREFIX}system_model_api"
    },
    {
        "name": "system_assistant",
        "description": f"{PLACEHOLDER_PREFIX}system_assistant_api"
    },
    {   "name": "Table Relation",
        "description": f"{PLACEHOLDER_PREFIX}tr_api"
    },
    {
        "name": "Data Permission",
        "description": f"{PLACEHOLDER_PREFIX}per_api"
    },

]


def get_translation(lang: str) -> Dict[str, str]:
    return load_translation(lang)
