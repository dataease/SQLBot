import json
from pathlib import Path
from typing import Dict, Any

from fastapi import Request


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
        primary_lang: str | None = None
        if lang is not None:
            primary_lang = lang.lower()
        elif request is not None:
            accept_language = request.headers.get('accept-language', 'en')
            primary_lang = accept_language.split(',')[0].lower()

        return primary_lang if primary_lang in self.translations else 'zh-cn'

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
