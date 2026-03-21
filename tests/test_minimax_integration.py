"""
Integration tests for MiniMax LLM provider in SQLBot.

These tests validate that the MiniMax API is reachable and functioning
correctly via the OpenAI-compatible protocol.

Requires MINIMAX_API_KEY environment variable to be set.
"""

import json
import os
import unittest

import requests

MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
MINIMAX_BASE_URL = "https://api.minimax.io/v1"


def skip_without_api_key(func):
    """Skip test if MINIMAX_API_KEY is not set."""
    return unittest.skipUnless(MINIMAX_API_KEY, "MINIMAX_API_KEY not set")(func)


class TestMiniMaxAPIConnectivity(unittest.TestCase):
    """Test MiniMax API endpoint reachability."""

    @skip_without_api_key
    def test_api_endpoint_reachable(self):
        """MiniMax API endpoint should be reachable (chat completions)."""
        resp = requests.post(
            f"{MINIMAX_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {MINIMAX_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "MiniMax-M2.5-highspeed",
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1,
            },
            timeout=15,
        )
        self.assertEqual(resp.status_code, 200)

    @skip_without_api_key
    def test_chat_completions_basic(self):
        """MiniMax chat completions should return a valid response."""
        resp = requests.post(
            f"{MINIMAX_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {MINIMAX_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "MiniMax-M2.5-highspeed",
                "messages": [{"role": "user", "content": "Say hello in one word."}],
                "temperature": 0.7,
                "max_tokens": 10,
            },
            timeout=30,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("choices", data)
        self.assertGreater(len(data["choices"]), 0)
        content = data["choices"][0]["message"]["content"]
        self.assertTrue(len(content) > 0, "Response content should not be empty")

    @skip_without_api_key
    def test_temperature_zero_accepted(self):
        """MiniMax API should accept temperature=0."""
        resp = requests.post(
            f"{MINIMAX_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {MINIMAX_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "MiniMax-M2.5-highspeed",
                "messages": [{"role": "user", "content": "Reply with OK."}],
                "temperature": 0,
                "max_tokens": 5,
            },
            timeout=30,
        )
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
