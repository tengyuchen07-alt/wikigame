"""Flask application for Wikipedia Race."""

from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from requests import RequestException

import crawler
import hints
import puzzle_store

ROOT = Path(__file__).resolve().parent.parent
CLIENT_DIR = ROOT / "client"

load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "server" / ".env")

app = Flask(__name__, static_folder=str(CLIENT_DIR), static_url_path="")


@app.get("/")
def home():
    return send_from_directory(CLIENT_DIR, "index.html")


@app.get("/find_path")
def find_path():
    try:
        puzzle = puzzle_store.get_random_puzzle(
            shortest_steps=crawler.PUZZLE_DEPTH,
        )
        return jsonify(
            {
                "start_title": puzzle.start_title,
                "target_title": puzzle.target_title,
                "path": [crawler.make_url(title) for title in puzzle.path],
                "shortest_steps": puzzle.shortest_steps,
            }
        )
    except puzzle_store.PuzzleStoreError as exc:
        app.logger.error("Puzzle database unavailable: %s", exc)
        return jsonify({"error": "The puzzle bank is temporarily unavailable."}), 503


@app.get("/api/wiki/<path:title>")
def wiki_article(title: str):
    try:
        return jsonify({"success": True, "html": crawler.fetch_article_html(title)})
    except (RequestException, crawler.WikipediaError) as exc:
        app.logger.info("Article load failed for %s: %s", title, exc)
        return jsonify({"success": False, "error": "This article could not be loaded."}), 502


@app.get("/api/hint")
def hint():
    current = request.args.get("title", "").strip()
    target = request.args.get("target", "").strip()
    next_title = request.args.get("next", "").strip()

    if not current or not target:
        return jsonify({"success": False, "error": "Current and target titles are required."}), 400

    try:
        article_text = crawler.fetch_article_text(current)
        candidate_links = crawler.get_links(current, limit=80)
        message = hints.generate_ai_hint(
            current,
            target,
            article_text,
            candidate_links,
        )
        return jsonify({"success": True, "hint": message, "source": "ai"})
    except (RequestException, crawler.WikipediaError, hints.HintError) as exc:
        app.logger.info("AI hint unavailable, using fallback: %s", exc)
        message = hints.fallback_hint(current, target, next_title)
        return jsonify({"success": True, "hint": message, "source": "fallback"})


@app.get("/health")
def health():
    puzzle_count = puzzle_store.count_puzzles(shortest_steps=crawler.PUZZLE_DEPTH)
    return jsonify(
        {
            "status": "ok",
            "puzzle_count": puzzle_count,
            "puzzle_target": puzzle_store.TARGET_PUZZLE_COUNT,
            "puzzle_bank_ready": puzzle_count >= puzzle_store.TARGET_PUZZLE_COUNT,
        }
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(host="127.0.0.1", port=5002, debug=False, threaded=True)
