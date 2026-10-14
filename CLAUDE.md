# Cokidoplanner

Scheduling tool for Cokido: it assigns parents to babysitting ("oppas") days with an OR-Tools CP-SAT solver. It is being rebuilt from a Google Sheet + polling script into a Flask + SQLite web app hosted on PythonAnywhere (free plan).

## Rebuild workflow

- Spec: `docs/FUNCTIONAL_SPEC.md` (v1.0; decisions in §10)
- Plan: `docs/REBUILD_PLAN.md`. Work one step at a time on a branch `step-NN-name`, meet the step's "Done when" criteria, then tick it off (☐ → ☑).
- Original tool: `docs/ORIGINAL_CODE.md`

## Layout & rules

- `planner/`: domain + solver. Pure Python, **no Flask imports**, fully unit-tested.
- `app/`: Flask web app (from step 5).
- `tests/`: pytest. Fixtures go in `tests/fixtures/` and must use anonymised data only.
- `legacy/`: original script, reference only. Don't modify it, and don't lint it.
- UI text is in Dutch. Code, identifiers and comments are in English.
- Remember the PythonAnywhere free-plan limits: the solver runs synchronously inside the web request with a time limit, and there are no background workers.

## Commands

```
venv\Scripts\activate
pip install -r requirements-dev.txt
pytest
ruff check .
```

## Legacy script

`python legacy/main.py`, run from the repo root. It needs `pip install -r legacy/requirements.txt` and `gs_credentials.json` (a Google service-account key) in the repo root. The key is gitignored: never commit it or print its contents. Running it edits the live Google Sheet (it deletes and recreates the result tabs), so don't run it unless asked.
