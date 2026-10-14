# Rebuild plan: step by step

This plan executes [FUNCTIONAL_SPEC.md](FUNCTIONAL_SPEC.md). Each step is small enough for one working session, ends in a working state and gets its own commit or PR. Do the steps in order and tick them off here.

Working agreements:
- One step per branch (`step-NN-short-name`). Merge to `main` when the acceptance criteria pass.
- The original script stays runnable until step 12. It is moved to `legacy/` in step 1, not deleted.
- New code lives in `app/` (web) and `planner/` (pure domain + solver, no Flask imports).
- Tests use `pytest`. Each step lists what has to be tested.

## Step 0: Decisions & environment check ☐
- Answer the open questions in spec §10 and update the spec. Remove ⚠️ where a default is confirmed. *(Done: spec v1.0, decisions D-1 to D-8.)*
- Create a PythonAnywhere **free** account and confirm:
  - the Python version,
  - that `pip install ortools` works in a virtualenv, and its disk usage,
  - the web request timeout and the CPU quota.
- Export the current Google Sheet tabs to CSV as anonymised sample data in `tests/fixtures/` (fake names).
- **Done when:** the spec is v1.0 and the fixtures are committed.

## Step 1: Repo restructure ☑
- Move `main.py`, `Calculation.py`, `DataHandler.py`, `GsheetWrapper.py` and `SolutionPrint.py` into `legacy/` (keeping git history with `git mv`). Update the run instructions in `CLAUDE.md`.
- Add `pyproject.toml` (project metadata, ruff, pytest config) and split dependencies into `requirements.txt` (runtime) and `requirements-dev.txt`.
- Create empty packages `planner/` and `app/`, plus `tests/`.
- Add a README with a project description and local setup.
- **Done when:** `pytest` runs (0 tests) and `ruff check` is clean on the new folders.

## Step 2: Domain model & solver core (no web) ☐
- Write `planner/model.py`: plain dataclasses for the planning input (families, parents, days, attendance, availability, fixed assignments, quotas, settings).
- Write `planner/defaults.py`: required parents per day and family quota defaults (F-5, F-9).
- Write `planner/solver.py`: CP-SAT with the hard constraints from F-10, a real objective (F-11) and N distinct solutions via no-good cuts. Returns ranked rosters plus stats.
- **Tests:**
  - fixture input gives a feasible result that satisfies all constraints,
  - an infeasible case is detected,
  - defaults match the legacy formulas,
  - a family with more than 5 parents works.
- **Done when:** the tests pass and solving the fixture finishes in under 10 s locally.

## Step 3: Feasibility pre-check ☐
- Write `planner/precheck.py` with human-readable diagnostics (F-12). Messages in Dutch.
- **Tests:** one test per diagnostic.

## Step 4: Legacy parity check ☐
- Write a script `scripts/compare_legacy.py` that runs the legacy solver and the new solver on the fixture CSVs and compares constraint satisfaction and score.
- **Done when:** the new solver's score is at least the legacy score and there are no constraint violations. Document the findings in `docs/`.

## Step 5: Flask skeleton + persistence ☐
- Create the app factory, config from `.env`, SQLAlchemy models for spec §3, and database migrations with Flask-Migrate (or a simple `create_all` plus versioned SQL; pick Flask-Migrate unless it causes trouble on PythonAnywhere).
- SQLite setup per spec §7: the DB path comes from `.env` and lives outside the repo, WAL mode and a busy timeout are set on connect, and there is a test that the app creates a fresh database at the configured path.
- Add a base layout, Dutch UI strings and the dashboard placeholder.
- **Done when:** `flask run` serves the dashboard locally and the DB is created from scratch with one command.

## Step 6: Auth & users ☐
- Add password login (Flask-Login), CSRF (Flask-WTF), planner role and a CLI command to create the first user.
- **Tests:** protected routes redirect when logged out.

## Step 7: Master data screens + CSV import ☐
- Build the families, parents and children CRUD (F-1).
- Build the CSV import of the legacy sheet tabs (F-2) and CSV export (F-3).
- **Done when:** importing the fixture CSVs reproduces the same entities.

## Step 8: Periods, days, grids ☐
- Build period create and day toggles (F-4).
- Build the grids for attendance, availability, fixed assignments and quotas (F-5–F-9).
- **Done when:** the planner can prepare a full period in the browser.

## Step 9: Calculate flow ☐
- Wire up pre-check → solve → store the PlanRun and Rosters (F-10–F-14). The solver is called synchronously with the configured time limit.
- **Done when:** a calculation on fixture-sized data completes within the PythonAnywhere request limit (measured on PythonAnywhere in step 11, locally here).

## Step 10: Roster review, edit, publish, export ☐
- Build the roster views and comparison (F-15, F-16), manual edits with re-validation (F-17), publish (F-18), and CSV/XLSX/print export (F-19).

## Step 11: Deploy to PythonAnywhere ☐
- Write `docs/DEPLOY.md`: virtualenv, WSGI file, static files mapping, `.env`, DB location outside the checkout, and the daily backup scheduled task (SQLite online backup with rotation, see spec §7).
- Deploy, then measure solve time and CPU usage on the real host and adjust the solver time limit.
- **Done when:** the planner can log in and complete a full period end-to-end on PythonAnywhere.

## Step 12: Migration & cut-over ☐
- Import the real data (spec §8) and run both tools in parallel for one period.
- Retire the sheet script. Keep `legacy/` for reference or delete it once accepted.

## Phase 2 (later)
Parent self-service (F-20), e-mail notifications (F-21), iCal (F-22), swaps (F-23). Plan these once phase 1 is in use.
