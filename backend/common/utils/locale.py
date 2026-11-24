import json
import re
from collections.abc import Collection
from pathlib import Path
from typing import Any, NamedTuple

from fastapi import Request

_DEFAULT_LANGUAGE = "zh-cn"
_CHINESE_VARIANTS = {
    "zh-hans": "zh-cn",
    "zh-sg": "zh-cn",
    "zh-hant": "zh-tw",
    "zh-hk": "zh-tw",
    "zh-mo": "zh-tw",
}
_LANGUAGE_ENTRY = re.compile(
    r"(?P<tag>[a-z]{1,8}(?:-[a-z0-9]{1,8})*|\*)"
    r"(?:[ \t]*;[ \t]*q=(?P<quality>0(?:\.[0-9]{0,3})?|1(?:\.0{0,3})?))?",
    re.ASCII | re.IGNORECASE,
)


class _LanguagePreference(NamedTuple):
    specificity: int
    direct_match: bool
    quality: float
    order: int


def _negotiate_language(headers: list[str], supported: Collection[str]) -> str:
    # A general language or wildcard may match several translations. Prefer the
    # application default when the client gives them identical preferences.
    languages = sorted(supported, key=lambda lang: (lang != _DEFAULT_LANGUAGE, lang))
    primaries = {lang.partition("-")[0] for lang in languages}
    ranges = {primary: primary for primary in primaries}
    ranges.update(
        {alias: lang for alias, lang in _CHINESE_VARIANTS.items() if lang in supported}
    )
    ranges.update({lang: lang for lang in languages})
    prefixes = sorted(ranges, key=len, reverse=True)

    # Keep each translation's most specific preference, including exclusions.
    scores: dict[str, _LanguagePreference] = {}
    for position, entry in enumerate(",".join(headers).split(",")):
        match = _LANGUAGE_ENTRY.fullmatch(entry.strip(" \t"))
        if not match:
            continue
        tag = match["tag"].lower()
        quality = float(match["quality"] or "1")
        language_range = "*"
        if tag != "*":
            prefix = next(
                (
                    part
                    for part in prefixes
                    if tag == part or tag.startswith(part + "-")
                ),
                None,
            )
            if prefix is None:
                continue
            language_range = ranges[prefix]
        specificity = 0 if language_range == "*" else language_range.count("-") + 1
        score = _LanguagePreference(
            specificity, tag == language_range, quality, -position
        )
        for lang in languages:
            if (
                language_range == "*"
                or lang == language_range
                or lang.startswith(language_range + "-")
            ):
                if lang not in scores or score > scores[lang]:
                    scores[lang] = score

    acceptable = [
        lang for lang in languages if lang in scores and scores[lang].quality > 0
    ]
    if acceptable:
        return max(
            acceptable, key=lambda lang: (scores[lang].quality, scores[lang].order)
        )
    if _DEFAULT_LANGUAGE in scores:  # Explicitly excluded; try an unmentioned language.
        return next(
            (lang for lang in languages if lang not in scores), _DEFAULT_LANGUAGE
        )
    return _DEFAULT_LANGUAGE


class I18n:
    def __init__(self, locale_dir: str | Path = "locales"):
        self.locale_dir = Path(locale_dir)
        self.translations: dict[str, dict[str, Any]] = {}
        self.load_translations()

    def load_translations(self):
        if not self.locale_dir.exists():
            self.locale_dir.mkdir()
            return

        for lang_file in self.locale_dir.glob("*.json"):
            with open(lang_file, encoding="utf-8") as f:
                self.translations[lang_file.stem.lower()] = json.load(f)

    def get_language(self, request: Request = None, lang: str = None) -> str:
        if lang is not None:
            normalized = lang.lower()
            return normalized if normalized in self.translations else _DEFAULT_LANGUAGE
        if request is None:
            return _DEFAULT_LANGUAGE

        headers = request.headers.getlist("accept-language") or ["en"]
        return _negotiate_language(headers, self.translations)

    def __call__(self, request: Request = None, lang: str = None) -> "I18nHelper":
        return I18nHelper(self, request, lang)


class I18nHelper:
    def __init__(self, i18n: I18n, request: Request = None, lang: str = None):
        self.i18n = i18n
        self.request = request
        self.lang = i18n.get_language(request, lang)

    def _get_nested_translation(self, data: dict[str, Any], key_path: str) -> str:
        keys = key_path.split(".")
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
