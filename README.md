# cokidoplanner

Planningstool voor Cokido: it builds the babysitting ("oppas") roster for parents with a constraint solver (Google OR-Tools).

The project is being rebuilt from a Google Sheet + Python script into a lightweight web app for PythonAnywhere.

- What the new app should do: [docs/FUNCTIONAL_SPEC.md](docs/FUNCTIONAL_SPEC.md)
- Step-by-step rebuild plan: [docs/REBUILD_PLAN.md](docs/REBUILD_PLAN.md)
- How the original tool works: [docs/ORIGINAL_CODE.md](docs/ORIGINAL_CODE.md)

## Repository layout

| Path | Contents |
|---|---|
| `planner/` | Domain model and solver (pure Python, no web code) |
| `app/` | Flask web app |
| `tests/` | pytest tests |
| `legacy/` | Original Google Sheet script, kept for reference until cut-over |
| `docs/` | Spec, plan and documentation |

## Local setup (Windows)

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements-dev.txt
pytest
ruff check .
```

## Running the legacy script

```
pip install -r legacy/requirements.txt
python legacy/main.py
```

Run it from the repo root, with the Google service-account key `gs_credentials.json` in the root. The key is gitignored and must never be committed.
