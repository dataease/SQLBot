"""Regression tests for error messages in chat execution details."""

import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHAT_DIR = PROJECT_ROOT / "frontend" / "src" / "views" / "chat"
COMPONENT_DIR = CHAT_DIR / "execution-component"

LOG_COMPONENTS = (
    "LogChooseTable",
    "LogCustomPrompt",
    "LogDataQuery",
    "LogGeneratePicture",
    "LogSQLSample",
    "LogTerm",
    "LogWithAi",
)


def read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class ExecutionErrorDetailsTestCase(unittest.TestCase):
    """Ensure the record error reaches every failed execution step."""

    def test_chat_view_passes_record_error_to_token_time(self) -> None:
        source = read_source(CHAT_DIR / "index.vue")
        token_time_tags = re.findall(r"<ChatTokenTime\b.*?/>", source, re.DOTALL)

        self.assertGreater(len(token_time_tags), 0)
        for tag in token_time_tags:
            with self.subTest(tag=tag):
                self.assertIn(':error="message.record?.error"', tag)

    def test_token_time_forwards_error_to_execution_details(self) -> None:
        source = read_source(CHAT_DIR / "ChatTokenTime.vue")

        self.assertRegex(
            source,
            re.compile(r"defineProps<\{.*?error\?: string.*?\}>\(\)", re.DOTALL),
        )
        execution_details_tag = re.search(
            r"<ExecutionDetails\b.*?</ExecutionDetails>", source, re.DOTALL
        )
        self.assertIsNotNone(execution_details_tag)
        self.assertIn(':error="error"', execution_details_tag.group(0))

    def test_execution_details_forwards_error_to_log_components(self) -> None:
        source = read_source(CHAT_DIR / "ExecutionDetails.vue")

        self.assertRegex(
            source,
            re.compile(r"defineProps<\{.*?error\?: string.*?\}>\(\)", re.DOTALL),
        )
        for component in LOG_COMPONENTS:
            with self.subTest(component=component):
                component_tag = re.search(rf"<{component}\b.*?/>", source, re.DOTALL)
                self.assertIsNotNone(component_tag)
                self.assertIn(':error="error"', component_tag.group(0))

    def test_log_components_render_the_forwarded_error(self) -> None:
        for component in LOG_COMPONENTS:
            with self.subTest(component=component):
                source = read_source(COMPONENT_DIR / f"{component}.vue")
                error_branch = re.search(
                    r'<template v-if="item\.error">\s*(.*?)\s*</template>',
                    source,
                    re.DOTALL,
                )

                self.assertIsNotNone(error_branch)
                self.assertIn("{{ error }}", error_branch.group(1))

    def test_ai_log_renders_error_branch_and_normal_list(self) -> None:
        """Error renders via its own v-if branch; the normal list is not gated by v-else."""
        source = read_source(COMPONENT_DIR / "LogWithAi.vue")

        self.assertRegex(
            source,
            re.compile(
                r'<template v-if="item\.error">\s*\{\{ error \}\}\s*</template>'
            ),
        )
        self.assertIn('<div class="item-list flex-gap-fallback flex-col">', source)


if __name__ == "__main__":
    unittest.main()
