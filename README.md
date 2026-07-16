# Wikipedia Race

A small web game where players navigate from one random English Wikipedia article to another using only links inside each article.

## Requirements

- Python 3.10 or newer
- Network access to Wikipedia

## Run locally

```sh
cd server
sh setup.sh
python server.py
```

Open <http://127.0.0.1:5002>.

On Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r server\requirements.txt
.\.venv\Scripts\python.exe server\server.py
```

VS Code/Pylance reads `pyrightconfig.json` and resolves imports from the
project-level `.venv`. After creating the environment, run **Developer: Reload
Window** if Pylance still shows stale import warnings.

## AI hints

Copy `.env.example` to `.env` and set `GEMINI_API_KEY` to enable Gemini hints.
The server sends Gemini the current article, target article, an article excerpt,
and the current page's candidate links. It asks for one short Traditional
Chinese clue without revealing the exact answer.

If the key is absent or Gemini is temporarily unavailable, the game returns a
deterministic fallback hint based on the generated solution path, so the game
remains playable.

## Pre-generated puzzle bank

Starting a game reads a verified five-step puzzle from
`server/data/puzzles.db`; it does not search Wikipedia in real time. The
runtime rotates through the least-played entries before repeating them.

Build or extend the bank to the target of 150 puzzles:

```powershell
.\.venv\Scripts\python.exe scripts\build_puzzle_db.py --target-count 150 --depth 5
```

The resumable builder uses the Six Degrees of Wikipedia graph to find shortest
paths, then checks every edge against the live Wikipedia API before saving it.
Interrupted runs continue from the number of rows already committed.
The generated database is deployment data and is ignored by Git by default.
After it reaches 150 entries, deploy it alongside the server or intentionally
add it with:

```powershell
git add -f server/data/puzzles.db
```

## Project structure

- `client/` contains the static HTML, CSS, and JavaScript.
- `server/server.py` exposes the Flask routes.
- `server/crawler.py` contains the Wikipedia API and article-cleaning logic.
- `server/hints.py` contains Gemini hint generation and fallback behavior.
- `server/puzzle_store.py` provides SQLite puzzle selection and persistence.
- `scripts/build_puzzle_db.py` builds the offline puzzle bank.

The repository does not include virtual environments, generated article dumps, or local environment files.
