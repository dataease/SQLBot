"""
Unit tests for the MiniMax supplier configuration in SQLBot.

These tests validate that the MiniMax LLM provider is correctly configured
in the frontend supplier registry, i18n translation files, and backend
model factory.
"""

import json
import os
import re
import unittest

# Project root relative to this test file
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestMiniMaxSupplierConfig(unittest.TestCase):
    """Test the MiniMax supplier entry in supplier.ts."""

    def setUp(self):
        supplier_path = os.path.join(
            PROJECT_ROOT, "frontend", "src", "entity", "supplier.ts"
        )
        with open(supplier_path, "r", encoding="utf-8") as f:
            self.supplier_content = f.read()

    def test_minimax_icon_import_exists(self):
        """MiniMax icon import statement should be present."""
        self.assertIn(
            "import icon_minimax_colorful from '@/assets/model/icon_minimax_colorful.png'",
            self.supplier_content,
        )

    def test_minimax_supplier_entry_exists(self):
        """MiniMax supplier entry with id=13 should exist in supplierList."""
        self.assertIn("id: 13", self.supplier_content)
        self.assertIn("name: 'MiniMax'", self.supplier_content)

    def test_minimax_i18n_key(self):
        """MiniMax should have the correct i18n key."""
        self.assertIn("i18nKey: 'supplier.minimax'", self.supplier_content)

    def test_minimax_icon_reference(self):
        """MiniMax should reference the correct icon variable."""
        self.assertIn("icon: icon_minimax_colorful", self.supplier_content)

    def test_minimax_api_domain(self):
        """MiniMax API domain should be https://api.minimax.io/v1."""
        self.assertIn(
            "api_domain: 'https://api.minimax.io/v1'", self.supplier_content
        )

    def test_minimax_temperature_range(self):
        """MiniMax temperature should be in range [0, 1]."""
        # Find the MiniMax section and check temperature config
        minimax_section = self.supplier_content[
            self.supplier_content.index("id: 13") :
        ]
        # Limit to just MiniMax section (up to next id:)
        next_id = minimax_section.index("id: 11", 10) if "id: 11" in minimax_section[10:] else len(minimax_section)
        minimax_section = minimax_section[:next_id]
        self.assertIn("key: 'temperature'", minimax_section)
        self.assertIn("val: 0.7", minimax_section)
        self.assertIn("range: '[0, 1]'", minimax_section)

    def test_minimax_model_options(self):
        """MiniMax should have M2.7, M2.5, and M2.5-highspeed models."""
        self.assertIn("name: 'MiniMax-M2.7'", self.supplier_content)
        self.assertIn("name: 'MiniMax-M2.5'", self.supplier_content)
        self.assertIn("name: 'MiniMax-M2.5-highspeed'", self.supplier_content)

    def test_minimax_has_model_config_type_0(self):
        """MiniMax should have model_config with type 0 (LLM)."""
        minimax_section = self.supplier_content[
            self.supplier_content.index("id: 13") :
        ]
        next_section = minimax_section.find("/* {", 10)
        if next_section == -1:
            next_section = minimax_section.find("  {", 10)
        minimax_section = minimax_section[:next_section] if next_section > 0 else minimax_section[:500]
        self.assertIn("model_config:", minimax_section)
        self.assertIn("0:", minimax_section)

    def test_minimax_uses_openai_protocol(self):
        """MiniMax should not set type='vllm' or type='azure' (defaults to openai)."""
        minimax_section = self.supplier_content[
            self.supplier_content.index("id: 13") :
        ]
        # Get just the MiniMax entry (roughly 20 lines)
        lines = minimax_section.split("\n")[:20]
        minimax_text = "\n".join(lines)
        self.assertNotIn("type: 'vllm'", minimax_text)
        self.assertNotIn("type: 'azure'", minimax_text)

    def test_supplier_id_13_is_unique(self):
        """Supplier id 13 should appear exactly once."""
        count = self.supplier_content.count("id: 13")
        self.assertEqual(count, 1, "Supplier id 13 should be unique")


class TestMiniMaxI18nTranslations(unittest.TestCase):
    """Test that MiniMax i18n translations are present in all locale files."""

    def _load_locale(self, locale_name):
        path = os.path.join(
            PROJECT_ROOT, "frontend", "src", "i18n", f"{locale_name}.json"
        )
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_en_translation(self):
        """English translation for MiniMax should exist."""
        data = self._load_locale("en")
        self.assertIn("minimax", data["supplier"])
        self.assertEqual(data["supplier"]["minimax"], "MiniMax")

    def test_zh_cn_translation(self):
        """Chinese (Simplified) translation for MiniMax should exist."""
        data = self._load_locale("zh-CN")
        self.assertIn("minimax", data["supplier"])
        self.assertEqual(data["supplier"]["minimax"], "MiniMax")

    def test_ko_kr_translation(self):
        """Korean translation for MiniMax should exist."""
        data = self._load_locale("ko-KR")
        self.assertIn("minimax", data["supplier"])
        self.assertEqual(data["supplier"]["minimax"], "MiniMax")

    def test_all_locales_have_same_supplier_keys(self):
        """All locale files should have the same set of supplier keys."""
        en = self._load_locale("en")
        zh = self._load_locale("zh-CN")
        ko = self._load_locale("ko-KR")
        en_keys = set(en["supplier"].keys())
        zh_keys = set(zh["supplier"].keys())
        ko_keys = set(ko["supplier"].keys())
        self.assertEqual(en_keys, zh_keys, "EN and ZH-CN should have same supplier keys")
        self.assertEqual(en_keys, ko_keys, "EN and KO-KR should have same supplier keys")


class TestMiniMaxIconFile(unittest.TestCase):
    """Test that the MiniMax icon file exists and is valid."""

    def test_icon_file_exists(self):
        """MiniMax icon PNG file should exist."""
        icon_path = os.path.join(
            PROJECT_ROOT,
            "frontend",
            "src",
            "assets",
            "model",
            "icon_minimax_colorful.png",
        )
        self.assertTrue(os.path.exists(icon_path), "MiniMax icon file should exist")

    def test_icon_is_png(self):
        """MiniMax icon should be a valid PNG file."""
        icon_path = os.path.join(
            PROJECT_ROOT,
            "frontend",
            "src",
            "assets",
            "model",
            "icon_minimax_colorful.png",
        )
        with open(icon_path, "rb") as f:
            header = f.read(8)
        # PNG magic number
        self.assertEqual(
            header[:4], b"\x89PNG", "File should have PNG magic number"
        )

    def test_icon_not_empty(self):
        """MiniMax icon file should not be empty."""
        icon_path = os.path.join(
            PROJECT_ROOT,
            "frontend",
            "src",
            "assets",
            "model",
            "icon_minimax_colorful.png",
        )
        size = os.path.getsize(icon_path)
        self.assertGreater(size, 100, "Icon file should be reasonably sized")


class TestModelFactoryConfig(unittest.TestCase):
    """Test that backend model_factory.py can support MiniMax via OpenAI protocol."""

    def setUp(self):
        factory_path = os.path.join(
            PROJECT_ROOT, "backend", "apps", "ai_model", "model_factory.py"
        )
        with open(factory_path, "r", encoding="utf-8") as f:
            self.factory_content = f.read()

    def test_openai_type_in_factory(self):
        """OpenAI type should be registered in LLMFactory._llm_types."""
        self.assertIn('"openai"', self.factory_content)

    def test_factory_supports_register(self):
        """LLMFactory should have register_llm method for extensibility."""
        self.assertIn("register_llm", self.factory_content)

    def test_factory_creates_openai_llm_for_openai_type(self):
        """The 'openai' type should map to OpenAILLM class."""
        self.assertIn('"openai": OpenAILLM', self.factory_content)

    def test_llm_config_has_api_base_url(self):
        """LLMConfig should support api_base_url for custom endpoints."""
        self.assertIn("api_base_url", self.factory_content)

    def test_openai_llm_passes_base_url(self):
        """OpenAILLM should pass base_url to BaseChatOpenAI."""
        self.assertIn("base_url=self.config.api_base_url", self.factory_content)


class TestReadmeContent(unittest.TestCase):
    """Test that README files mention MiniMax."""

    def test_readme_zh_mentions_minimax(self):
        """Chinese README should list MiniMax as a supported provider."""
        path = os.path.join(PROJECT_ROOT, "README.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("MiniMax", content)

    def test_readme_en_mentions_minimax(self):
        """English README should list MiniMax as a supported provider."""
        path = os.path.join(PROJECT_ROOT, "docs", "README.en.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("MiniMax", content)


if __name__ == "__main__":
    unittest.main()
