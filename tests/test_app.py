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
import puzzle_store  # noqa: E402
import server  # noqa: E402
from scripts import build_puzzle_db  # noqa: E402


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


class PuzzleStoreTests(unittest.TestCase):
    def test_store_round_trip_and_balanced_rotation(self) -> None:
        root = Path(__file__).resolve().parents[1]
        db_path = root / "tests" / ".test-puzzles.db"
        db_path.unlink(missing_ok=True)
        try:
            first = ["A", "B", "C", "D", "E", "F"]
            second = ["G", "H", "I", "J", "K", "L"]
            self.assertTrue(
                puzzle_store.add_puzzle(first, source="test", db_path=db_path)
            )
            self.assertTrue(
                puzzle_store.add_puzzle(second, source="test", db_path=db_path)
            )
            self.assertFalse(
                puzzle_store.add_puzzle(first, source="test", db_path=db_path)
            )

            selected = {
                puzzle_store.get_random_puzzle(
                    shortest_steps=5,
                    db_path=db_path,
                ).start_title
                for _ in range(2)
            }

            self.assertEqual(selected, {"A", "G"})
            self.assertEqual(
                puzzle_store.count_puzzles(shortest_steps=5, db_path=db_path),
                2,
            )
        finally:
            db_path.unlink(missing_ok=True)

    @patch.object(puzzle_store, "get_random_puzzle")
    def test_find_path_reads_from_database(self, get_random_puzzle: Mock) -> None:
        get_random_puzzle.return_value = puzzle_store.StoredPuzzle(
            start_title="A",
            target_title="F",
            path=["A", "B", "C", "D", "E", "F"],
            shortest_steps=5,
        )

        response = server.app.test_client().get("/find_path")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["shortest_steps"], 5)
        self.assertEqual(response.json["start_title"], "A")
        get_random_puzzle.assert_called_once_with(shortest_steps=5)

    def test_longer_shortest_path_produces_five_step_subpaths(self) -> None:
        groups = build_puzzle_db.fixed_depth_candidates(
            [["A", "B", "C", "D", "E", "F", "G"]],
            depth=5,
        )

        self.assertEqual(
            groups,
            {
                ("A", "F"): [["A", "B", "C", "D", "E", "F"]],
                ("B", "G"): [["B", "C", "D", "E", "F", "G"]],
            },
        )

    @patch.object(puzzle_store, "count_puzzles", return_value=150)
    def test_health_reports_puzzle_bank_readiness(self, count_puzzles: Mock) -> None:
        response = server.app.test_client().get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["puzzle_bank_ready"])
        self.assertEqual(response.json["puzzle_count"], 150)


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
