import json
from pathlib import Path
from typing import Dict, Any

from fastapi import Request


_LANGUAGE_DEFAULTS = {"zh": "zh-cn", "ko": "ko-kr", "th": "th-th"}


class I18n:
    def __init__(self, locale_dir: str = "locales"):
        self.locale_dir = Path(locale_dir)
        self.translations: Dict[str, Dict[str, Any]] = {}
        self.load_translations()

    def load_translations(self):
        if not self.locale_dir.exists():
            self.locale_dir.mkdir()
            return

        for lang_file in self.locale_dir.glob("*.json"):
            with open(lang_file, 'r', encoding='utf-8') as f:
                self.translations[lang_file.stem.lower()] = json.load(f)

    def get_language(self, request: Request = None, lang: str = None) -> str:
        if lang is not None:
            normalized = lang.lower()
            return normalized if normalized in self.translations else "zh-cn"
        if request is None:
            return "zh-cn"

        preferences: list[tuple[float, str]] = []
        for entry in request.headers.get("accept-language", "en").split(","):
            tag, separator, weight = entry.strip().lower().partition(";")
            quality = 1.0
            if separator:
                key, _, value = weight.strip().partition("=")
                if key.strip() != "q":
                    continue
                try:
                    quality = float(value)
                except ValueError:
                    continue
            if tag.strip() and 0 < quality <= 1:
                preferences.append((quality, tag.strip()))

        for _, tag in sorted(preferences, key=lambda preference: preference[0], reverse=True):
            if tag in self.translations:
                return tag
            primary = tag.split("-", 1)[0]
            fallback = _LANGUAGE_DEFAULTS.get(primary, primary)
            if fallback in self.translations:
                return fallback
        return "zh-cn"

    def __call__(self, request: Request = None, lang: str = None) -> 'I18nHelper':
        return I18nHelper(self, request, lang)


class I18nHelper:
    def __init__(self, i18n: I18n, request: Request = None, lang: str = None):
        self.i18n = i18n
        self.request = request
        self.lang = i18n.get_language(request, lang)

    def _get_nested_translation(self, data: Dict[str, Any], key_path: str) -> str:
        keys = key_path.split('.')
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return key_path  # 如果找不到，返回原键

        return current if isinstance(current, str) else key_path

    def __call__(self, arg_key: str, **kwargs) -> str:
        lang_data = self.i18n.translations.get(self.lang, {})
        text = self._get_nested_translation(lang_data, arg_key)

        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, ValueError):
                return text
        return text
