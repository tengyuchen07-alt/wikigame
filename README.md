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

On Windows, create and activate the environment manually:

```powershell
cd server
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python server.py
```

## Project structure

- `client/` contains the static HTML, CSS, and JavaScript.
- `server/server.py` exposes the Flask routes.
- `server/crawler.py` contains the Wikipedia API and article-cleaning logic.

The repository does not include virtual environments, generated article dumps, or local environment files.
