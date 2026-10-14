# Cokidoplanner web app: functional specification

Status: **v1.0**: all phase-1 decisions taken, see [Decisions](#10-decisions).
Background on the old tool: [ORIGINAL_CODE.md](ORIGINAL_CODE.md).

## 1. Goal

Replace the current setup, a Google Sheet plus a Python script polling it from someone's PC, with a lightweight web app hosted on **PythonAnywhere**. In the new app the Cokido planner can:

1. maintain families, parents, children and the planning period,
2. collect attendance (children) and availability (parents),
3. generate a fair babysitting ("oppas") roster with one click,
4. compare a few alternative rosters, adjust one by hand, publish it and export it.

Nothing has to run on a personal computer any more.

## 2. Users and roles

| Role | Who | Can do |
|---|---|---|
| **Planner** (admin) | 1–3 board members | Everything: master data, periods, calculations, publishing, user management. |
| **Parent** (phase 2) | Every parent | Log in (or use a personal link), enter their own availability and preferences for an open period, and view the published roster. |
| **Anonymous** | none | Only sees the login page. |

**Decided:** phase 1 delivers the Planner role only. The planner enters availability on behalf of parents, which is how it works in the sheet today. User management for parents (accounts, roles, self-service) comes in phase 2. Phase 1 should not block it: planner accounts already live in a `User` table with a role field.

## 3. Domain model

| Entity | Fields (key ones) | Notes |
|---|---|---|
| **Family** | id, name, active | Groups parents and children. |
| **Parent** | id, family, name, email (optional), min_days (optional), max_days (optional), active | A family can have 1–N parents. The old limit of 5 is dropped. |
| **Child** | id, family, name, active | |
| **Period** | id, name, start_date, end_date, status (`draft` → `open` → `planned` → `published` → `archived`) | Planning horizon. Replaces the "day columns" of the sheet. |
| **Day** | period, date, is_open (bool), required_parents (optional override) | Generated from the period, excluding weekends and holidays (the planner can toggle days). |
| **Attendance** | child, day, present (bool) | Replaces the `presence` tab. |
| **Availability** | parent, day, preference (integer ≥ 0; 0 = not available) | Replaces `availability`. Any positive number means available. A higher number means a stronger preference relative to the same family's other days. See F-7. |
| **FixedAssignment** | parent, day, value (must / must not) | Replaces `availability-fix`. |
| **FamilyQuota** | family, period, quota_days (optional override) | Replaces `oppasdagen`. |
| **Settings** | children_per_parent (default 6), child_days_per_oppas_day (default 5), solver_time_limit_s, solutions_to_keep | Replaces the hardcoded factors. |
| **PlanRun** | id, period, started_at, status, solver stats, message | One click on "Calculate". |
| **Roster** | id, plan_run, rank, score, is_selected, is_published | One candidate solution. |
| **Assignment** | roster, parent, day | One scheduled parent on one day. |

## 4. Functional requirements

### 4.1 Master data
- **F-1**: CRUD for families, parents and children. Parents and children are always linked to a family. Deletes are soft (set `active = false`) so history stays intact.
- **F-2**: Import from the existing Google Sheet tabs `children`, `parents`, `presence`, `availability`, `availability-fix`, `oppasdagen` and `oppassers_per_dag`. This is a one-off migration, via CSV export of each tab (no Google API credentials needed in production).
- **F-3**: CSV import and export of the master data.

### 4.2 Periods and days
- **F-4**: The planner creates a period with a start and end date. The app generates the days and the planner can switch individual days off.
- **F-5**: Per day, the required number of parents defaults to `ceil(children present / children_per_parent)` and can be overridden.

### 4.3 Attendance and availability
- **F-6**: A grid of children × days to tick attendance, with an option to copy the attendance pattern from the previous period or from a weekday pattern.
- **F-7**: A grid of parents × days to enter preferences. 0 or empty means not available. Any positive integer means available, and the size of the number expresses how much the parent prefers that day. Example: Friday 5, Monday 1 means available on both, with Friday strongly preferred. There is no fixed upper limit. For the objective, each family's values are normalised so they sum to 100 (see F-11). A family that enters big numbers therefore gets no more weight than one that enters 1s. Only the relative spread within a family matters.
- **F-8**: A grid for fixed assignments ("must" / "must not" / empty).
- **F-9**: Per-family quota. It defaults to `round(total child-days of the family / child_days_per_oppas_day)` and can be overridden. Shown next to the calculated default.

### 4.4 Calculation
- **F-10**: A "Calculate" button runs the solver for a period. The hard constraints are the same as today:
  1. parents scheduled each day = required number,
  2. days per family ≤ family quota (the quota is a **maximum**, decided),
  3. a parent is only scheduled on available days,
  4. parent min_days ≤ scheduled days ≤ max_days,
  5. fixed assignments are respected.
- **F-11**: Objective: maximise the total of each family's normalised preferences (each family's preferences scaled to sum to 100, as today). Unlike the original, this is a real CP-SAT objective, and up to `solutions_to_keep` (default 5) **distinct** good rosters are produced. They are ranked by score.
- **F-12**: Before solving, the app runs a feasibility pre-check with clear messages, for example "Day 2026-11-03 needs 3 parents but only 2 are available" or "Sum of family quotas (40) < total required parent-days (44)". If the solver finds no solution, the user sees the likely cause and is never left with an empty result.
- **F-13**: The calculation runs synchronously inside the web request (free plan, so no background workers) and finishes within the configured time limit (default 30 s, to be tuned in step 11, see §7). While it runs, the user sees progress or a waiting state, and gets a result page afterwards.
- **F-14**: Every run is stored as a PlanRun with its stats, so earlier runs stay viewable.

### 4.5 Review, edit, publish
- **F-15**: A roster view with a parents × days matrix and a days → parents list. It shows per-parent and per-family totals compared with quotas, and highlights where preferences were not met.
- **F-16**: Side-by-side comparison of candidate rosters.
- **F-17**: The planner selects a roster and can then make manual swaps. After each edit the app re-validates the hard constraints and shows violations as warnings without blocking the edit.
- **F-18**: Publish. The roster becomes read-only and the period status becomes `published`.
- **F-19**: Export the published roster as CSV and XLSX, plus a print-friendly page.

### 4.6 Phase 2 (not in the first release)
- **F-19a**: User management: invite and manage parent accounts and roles.
- **F-20**: Parent self-service for availability, via a login or a magic link per parent.
- **F-21**: E-mail notification when availability opens and when a roster is published.
- **F-22**: iCal feed per parent.
- **F-23**: Swap requests between parents.

## 5. Screens (phase 1)

1. Login
2. Dashboard: current period, its status, next action
3. Families (list/detail with parents and children)
4. Periods (list, create, day toggles)
5. Attendance grid
6. Availability grid (+ fixed-assignment mode)
7. Quotas & daily requirements (calculated vs. override)
8. Calculate (pre-check results → run → result)
9. Rosters (compare, select, edit, publish)
10. Export / print
11. Settings & users

UI language: **Dutch**. Code and identifiers: English.

## 6. Non-functional requirements

| Area | Requirement |
|---|---|
| Hosting | PythonAnywhere, single web app, WSGI. |
| Size | About 20–40 families, about 60 parents, periods of up to about 6 months. |
| Tech stack | Python 3.12+, **Flask**, **SQLite** (via SQLAlchemy), server-rendered Jinja templates, minimal JavaScript (plain JS or htmx) and no build step. OR-Tools CP-SAT for solving. |
| Security | Password login with hashed passwords, CSRF protection on all forms, HTTPS (enforced by PythonAnywhere). Secrets in a `.env` outside git. Personal data is limited to names and optional e-mail addresses (GDPR: data minimisation, delete on request). |
| Reliability | Daily SQLite backup (PythonAnywhere scheduled task) plus manual download of the DB/CSV export. |
| Maintainability | Solver logic separated from the web layer and unit-tested on fixtures. One-command local start. |
| Performance | Pages < 1 s. Solve within the time limit. |

## 7. PythonAnywhere constraints to design around

**Decided: free plan.** The limits below are hard design constraints. Verify the exact numbers in step 0.

- **Request timeout and CPU quota.** Web requests have a hard time limit, and accounts have a daily CPU-seconds quota (small on the free tier). Running the old "enumerate 100,000 solutions" approach inside a request is not viable. Hence F-11 (a real objective with a few distinct solutions) and a configurable solver time limit.
- **No background workers on the free tier.** The free tier has no always-on tasks, and scheduled tasks run at most daily. The app therefore solves **synchronously inside the request** with a short time limit. If that ever proves too slow, the fallback is upgrading to a paid plan with an always-on task processing a PlanRun queue (the data model already supports this).
- **Package availability.** OR-Tools must install in a PythonAnywhere virtualenv. Check its install size against the disk quota.
- **Outbound internet.** The free tier only allows whitelisted outbound sites. This is fine as long as the app doesn't call Google APIs at runtime (F-2 uses CSV).
- **Database: SQLite, not MySQL.** The app does not need a database server, so the lack of MySQL on the free plan is not an issue. To manage SQLite there:
  - Store the DB file in the home directory **outside** the git checkout (for example `~/cokidoplanner-data/cokido.db`), with the path set in `.env`. Then a deploy (`git pull`) can never overwrite or commit it.
  - Enable SQLite WAL mode and a busy timeout, so a long solve request and a page load don't hit "database is locked". Keep write transactions short: solve first, then write the results in one transaction.
  - The daily backup task uses SQLite's online backup (`sqlite3 .backup` / `VACUUM INTO`), not a plain file copy. Keep the last N copies within the disk quota.
  - Stick to standard SQLAlchemy so a later move to MySQL or Postgres on a paid plan is just a change of database URL plus a data migration.
- **Custom domain.** Not available on the free plan, so the app runs at `<user>.pythonanywhere.com`.
- **Free-account expiry.** Free web apps must be renewed periodically from the PythonAnywhere dashboard, otherwise they are disabled. Put a reminder in `docs/DEPLOY.md`.

## 8. Migration

1. Export each Google Sheet tab to CSV.
2. Import with F-2 into a new period.
3. Run the new solver and compare with the last roster made by the old tool (score, constraint satisfaction).
4. Run both side by side for one period, then retire the sheet script.

## 9. Out of scope

Payments and invoicing, child administration beyond names, a native mobile app, multi-tenant use by other organisations.

## 10. Decisions

- **D-1**: Phase 1 is for planners only. User management and parent self-service come in phase 2 (F-19a, F-20).
- **D-2**: PythonAnywhere free plan, so solving is synchronous inside the request and there is no custom domain.
- **D-3**: Preferences are open-ended positive integers, normalised per family to 100 (F-7, F-11).
- **D-4**: The family quota is a maximum (days per family ≤ quota).

- **D-5**: The Google Sheet is a one-off migration source (F-2). The web app fully replaces it as the frontend, and there is no ongoing sync.
- **D-6**: Holidays and closed days are switched off by hand per period by the planner (F-4). There is no holiday calendar.
- **D-7**: Phase 1 has one shared planner account, created with a CLI command. Individual accounts come with phase 2 user management.
- **D-8**: The tech defaults are confirmed: Flask, SQLite/SQLAlchemy, Jinja templates without a JS build step, CSV import, CSV/XLSX export, Dutch UI with English code.
