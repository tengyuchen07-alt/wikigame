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

## AI hints

Copy `.env.example` to `.env` and set `GEMINI_API_KEY` to enable Gemini hints.
The server sends Gemini the current article, target article, an article excerpt,
and the current page's candidate links. It asks for one short Traditional
Chinese clue without revealing the exact answer.

If the key is absent or Gemini is temporarily unavailable, the game returns a
deterministic fallback hint based on the generated solution path, so the game
remains playable.

## Project structure

- `client/` contains the static HTML, CSS, and JavaScript.
- `server/server.py` exposes the Flask routes.
- `server/crawler.py` contains the Wikipedia API and article-cleaning logic.
- `server/hints.py` contains Gemini hint generation and fallback behavior.

The repository does not include virtual environments, generated article dumps, or local environment files.
