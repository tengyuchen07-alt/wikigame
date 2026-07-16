from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from bs4 import BeautifulSoup

SERVER_DIR = Path(__file__).resolve().parents[1] / "server"
sys.path.insert(0, str(SERVER_DIR))

import crawler  # noqa: E402
import hints  # noqa: E402
import server  # noqa: E402


class ArticleCleaningTests(unittest.TestCase):
    @patch.object(crawler.session, "get")
    def test_absolute_wikipedia_article_links_are_normalized(self, get: Mock) -> None:
        response = Mock()
        response.content = b"""
            <div id="mw-content-text">
              <div class="mw-parser-output">
                <p>
                  <a href="https://en.wikipedia.org/wiki/Computer_science">Keep</a>
                  <a href="/wiki/Software_engineering#History">Keep too</a>
                  <a href="https://example.com/wiki/Other">Remove external</a>
                  <a href="/wiki/Category:Computing">Remove namespace</a>
                </p>
              </div>
            </div>
        """
        response.raise_for_status.return_value = None
        get.return_value = response

        soup = BeautifulSoup(crawler.fetch_article_html("Python"), "html.parser")
        self.assertEqual(
            [link["href"] for link in soup.select("a[href]")],
            ["/wiki/Computer_science", "/wiki/Software_engineering"],
        )


class HintTests(unittest.TestCase):
    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}, clear=True)
    @patch.object(hints.requests, "post")
    def test_ai_hint_uses_gemini_response(self, post: Mock) -> None:
        response = Mock()
        response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "往計算領域的基礎概念找。"}]}}]
        }
        response.raise_for_status.return_value = None
        post.return_value = response

        result = hints.generate_ai_hint(
            "Python",
            "Computer science",
            "Python is a programming language.",
            ["Programming language", "Computer science"],
        )

        self.assertEqual(result, "往計算領域的基礎概念找。")
        self.assertEqual(
            post.call_args.kwargs["headers"],
            {"x-goog-api-key": "test-key"},
        )

    @patch.object(crawler, "fetch_article_text", return_value="article text")
    @patch.object(crawler, "get_links", return_value=["Middle"])
    @patch.object(hints, "generate_ai_hint", side_effect=hints.HintError("no key"))
    def test_hint_route_falls_back_when_ai_is_unavailable(
        self,
        generate: Mock,
        get_links: Mock,
        fetch_text: Mock,
    ) -> None:
        response = server.app.test_client().get(
            "/api/hint?title=Start&target=Target&next=Middle"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["source"], "fallback")
        self.assertIn("Middle", response.json["hint"])


class FrontendTests(unittest.TestCase):
    def test_game_has_no_back_navigation_control(self) -> None:
        root = Path(__file__).resolve().parents[1]
        html = (root / "client" / "inGame.html").read_text(encoding="utf-8")
        script = (root / "client" / "inGame.js").read_text(encoding="utf-8")

        self.assertNotIn("back-button", html)
        self.assertNotIn("goBack", script)
        self.assertIn("glass-panel", html)


if __name__ == "__main__":
    unittest.main()
