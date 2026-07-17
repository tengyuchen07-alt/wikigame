"""Build a reusable SQLite puzzle bank outside the request path.

The shortest-path service searches a Wikipedia dump quickly. Every accepted
path is then checked against the live Wikipedia API so stale links are rejected.
The script is resumable because each accepted puzzle is committed immediately.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import logging
import sys
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
SERVER_DIR = ROOT / "server"
sys.path.insert(0, str(SERVER_DIR))

import crawler  # noqa: E402
import puzzle_store  # noqa: E402

SHORTEST_PATH_API = "https://api.sixdegreesofwikipedia.com/paths"
SOURCE_NAME = "sixdegreesofwikipedia.com + live Wikipedia link verification"
RANDOM_BATCH_SIZE = 50
REQUEST_TIMEOUT = 60

logger = logging.getLogger("puzzle-builder")


def fetch_random_titles(limit: int = RANDOM_BATCH_SIZE) -> list[str]:
    data = crawler._api_get(  # noqa: SLF001 - shared MediaWiki client
        action="query",
        list="random",
        rnnamespace=0,
        rnlimit=limit,
    )
    return [
        item["title"]
        for item in data.get("query", {}).get("random", [])
        if item.get("title")
    ]


def fetch_shortest_paths(pair: tuple[str, str]) -> list[list[str]]:
    source, target = pair
    try:
        response = crawler.session.post(
            SHORTEST_PATH_API,
            json={"source": source, "target": target},
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == 400:
            return []
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        paths = data.get("paths", [])
        pages = data.get("pages", {})
        if not paths:
            return []
        return [
            [pages[str(page_id)]["title"] for page_id in path]
            for path in paths
        ]
    except (KeyError, TypeError, ValueError, requests.RequestException) as exc:
        logger.debug("Path lookup failed for %r -> %r: %s", source, target, exc)
        return []


def path_exists_on_live_wikipedia(path: list[str]) -> bool:
    """Verify all directed edges in one MediaWiki API request."""
    sources = path[:-1]
    targets = path[1:]
    data = crawler._api_get(  # noqa: SLF001 - shared MediaWiki client
        action="query",
        prop="links",
        titles="|".join(sources),
        pltitles="|".join(targets),
        plnamespace=0,
        pllimit="max",
        redirects=1,
    )
    pages = data.get("query", {}).get("pages", [])
    links_by_source = {
        page.get("title"): {
            item.get("title") for item in page.get("links", []) if item.get("title")
        }
        for page in pages
        if not page.get("missing")
    }
    return all(
        target in links_by_source.get(source, set())
        for source, target in zip(sources, targets)
    )


def candidate_pairs() -> list[tuple[str, str]]:
    titles = fetch_random_titles()
    return list(zip(titles[::2], titles[1::2]))


def fixed_depth_candidates(
    paths: list[list[str]],
    depth: int,
) -> dict[tuple[str, str], list[list[str]]]:
    """Group every depth-sized subpath from the returned shortest paths.

    Every contiguous subpath of a shortest path is itself a shortest path, so a
    six-step result provides two independently valid five-step puzzle choices.
    """
    grouped: dict[tuple[str, str], list[list[str]]] = {}
    width = depth + 1
    for path in paths:
        for offset in range(max(0, len(path) - depth)):
            candidate = path[offset : offset + width]
            if len(candidate) != width:
                continue
            grouped.setdefault((candidate[0], candidate[-1]), []).append(candidate)
    return grouped


def build(
    *,
    target_count: int,
    depth: int,
    workers: int,
    db_path: Path,
) -> None:
    puzzle_store.initialize(db_path)
    current = puzzle_store.count_puzzles(shortest_steps=depth, db_path=db_path)
    logger.info("Puzzle bank contains %d/%d depth-%d puzzles", current, target_count, depth)

    while current < target_count:
        pairs = candidate_pairs()
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(fetch_shortest_paths, pair) for pair in pairs]
            for future in concurrent.futures.as_completed(futures):
                paths = future.result()
                if current >= target_count:
                    break
                groups = fixed_depth_candidates(paths, depth)
                saved_from_result = False
                for alternatives in groups.values():
                    if current >= target_count or saved_from_result:
                        break
                    for path in alternatives:
                        try:
                            if path_exists_on_live_wikipedia(path):
                                break
                        except (
                            crawler.WikipediaError,
                            requests.RequestException,
                        ) as exc:
                            logger.warning("Live link verification failed: %s", exc)
                    else:
                        logger.info(
                            "Rejected stale path: %s",
                            " -> ".join(alternatives[-1]),
                        )
                        continue

                    if puzzle_store.add_puzzle(
                        path,
                        source=SOURCE_NAME,
                        db_path=db_path,
                    ):
                        current += 1
                        saved_from_result = True
                        logger.info(
                            "Saved %d/%d: %s",
                            current,
                            target_count,
                            " -> ".join(path),
                        )

    logger.info("Puzzle bank is ready: %d depth-%d puzzles", current, depth)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target-count",
        type=int,
        default=puzzle_store.TARGET_PUZZLE_COUNT,
    )
    parser.add_argument("--depth", type=int, default=5)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument(
        "--database",
        type=Path,
        default=puzzle_store.DEFAULT_DB_PATH,
    )
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    arguments = parse_args()
    build(
        target_count=arguments.target_count,
        depth=arguments.depth,
        workers=max(1, arguments.workers),
        db_path=arguments.database,
    )
