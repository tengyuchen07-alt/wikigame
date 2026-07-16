"""Flask application for Wikipedia Race."""

from __future__ import annotations

import logging
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from requests import RequestException

import crawler

ROOT = Path(__file__).resolve().parent.parent
CLIENT_DIR = ROOT / "client"

app = Flask(__name__, static_folder=str(CLIENT_DIR), static_url_path="")


@app.get("/")
def home():
    return send_from_directory(CLIENT_DIR, "index.html")


@app.get("/find_path")
def find_path():
    try:
        puzzle = crawler.generate_puzzle(steps=3)
        return jsonify(
            {
                "start_title": puzzle.start_title,
                "target_title": puzzle.target_title,
                "path": [crawler.make_url(title) for title in puzzle.path],
            }
        )
    except (RequestException, crawler.WikipediaError) as exc:
        app.logger.warning("Puzzle generation failed: %s", exc)
        return jsonify({"error": "Wikipedia is temporarily unavailable."}), 503


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

    if next_title:
        message = f"From {current}, look for a link related to “{next_title}”."
    else:
        message = f"You are off the generated route. Look for a broad topic connected to “{target}”."

    return jsonify({"success": True, "hint": message})


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(host="127.0.0.1", port=5002, debug=False, threaded=True)
