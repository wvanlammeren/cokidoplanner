# Cokidoplanner: original code

This document describes the code as it was first imported into this repository (commits `6c43452` / `d87a087`).

## What the app does

Cokidoplanner plans the babysitting ("oppas") roster for Cokido, a parent-run childcare group. Each day a number of parents have to be present to look after the children. The app decides **which parent is present on which day**:

- The number of parents present each day equals the number that day requires.
- No family is scheduled for more days than its quota.
- Parents are only scheduled on days they marked as available.
- Optional per-parent minimum and maximum day counts are respected.
- Assignments the planner fixed by hand are kept.
- Among valid rosters, it prefers the ones that best match parents' stated preferences.

The model is a constraint-satisfaction problem solved with Google OR-Tools CP-SAT. The app has no user interface of its own. A Google Sheet holds all input data, shows all results, and acts as the "Run" button.

## Main files

| File | Role |
|---|---|
| `main.py` | Entry point. Runs forever: every 20 seconds it reads a run-flag cell in the sheet, and if the cell says `1` it runs the calculation and writes a status back. |
| `GsheetWrapper.py` | `GsheetWrapper` loads the service-account credentials and opens the spreadsheet by its (hardcoded) ID through `gspread`. |
| `DataHandler.py` | `CokidoDataHandler` reads every input tab into pandas DataFrames and derives defaults (parents per day, days per family). It builds the numpy matrices the solver needs, writes derived values back, writes result tabs, and reads/writes the run flag. |
| `Calculation.py` | `run_calculation()` opens the sheet, imports data, builds the CP-SAT model (boolean variable `shift[parent, day]` plus constraints 1–6 below), solves it, and writes the best solutions back. It returns a status string such as `"123 oplossingen"` or `"geen oplossingen"`. |
| `SolutionPrint.py` | `SolutionPrinter`, a CP-SAT solution callback. It scores every solution found with the preference cost matrix and keeps a rolling list of the 10 most recent best-so-far solutions. It stops after 100,000 solutions. |
| `requirements.txt` | Pinned dependencies. |

### Calculation flow

1. `main.py` sees `Readme!D20 == "1"` and sets it to `Calculating`.
2. `run_calculation()` creates a new sheet connection and calls `CokidoDataHandler.import_data()`.
3. `update_gsheet()` writes the derived family table and the parents-per-day table back to the `oppasdagen` and `oppassers_per_dag` tabs.
4. It builds the model with these constraints:
   1. Parents per day equals the day's required number (`oppassers`).
   2. Total days per family is at most the family quota (`oppasdagen`). Families of 1–5 parents are supported, and more than 5 raises an error.
   3. `shift[p, d] <= available[p, d]`.
   4. Per-parent `maxdays` (empty cells become 1000).
   5. Per-parent `mindays` (empty cells become 0).
   6. Non-empty cells in `availability-fix` force `shift[p, d]` to that value.
5. It solves for up to 60 s with `enumerate_all_solutions=True`. The objective is not given to the solver. `SolutionPrinter` instead scores each enumerated solution (sum of normalised preference values) and keeps the better ones.
6. `write_results()` deletes all old tabs whose names contain `_result_`. It then creates one new tab per kept solution, named `_result_<random 1–10000>`. Each tab has the columns `Name`, `parentID` and one column per day, with `1` where the parent is scheduled.
7. `main.py` writes the returned status string into `Readme!D20`.

## Google Sheet as UI and data store

The sheet is opened by spreadsheet ID. The app expects these tabs:

| Tab | Direction | Contents |
|---|---|---|
| `Readme` | read/write | Cell **D20** is the control: a user types `1` to start a run. The app sets it to `Calculating`, then `writing results`, then the result status (`N oplossingen` / `geen oplossingen`). |
| `children` | read | One row per child: `KidID`, `FamID`, ... |
| `parents` | read | One row per parent: `ParentID`, `FamID`, `Name`, `maxdays`, `mindays`. Sorted by `ParentID`, `FamID` must be non-decreasing in steps of at most 1. |
| `presence` | read | `KidID`, `Name` and one column per day. A non-empty value means the child attends that day. The day columns define the planning horizon. |
| `availability` | read | `ParentID`, `Name` and one column per day. 0 or empty means unavailable. A higher number means a stronger preference. Values are normalised per family to 100 for the cost matrix. |
| `availability-fix` | read | Same shape. Leave a cell empty for "solver decides", or enter a value to force that assignment. |
| `oppasdagen` | read/write | Days per family. Empty entries default to `round(total child-days of the family / 5)`. The full family table is written back. |
| `oppassers_per_dag` | read/write | Parents needed per day (`oppassers`). Empty entries default to `ceil(children present / 6)`. Written back with a `TotalChildren` column. |
| `_result_*` | write | Generated result tabs (see the flow above). They are deleted and recreated on every run. |

Every column read from a tab is treated as a day column, so the day columns in `presence`, `availability`, `availability-fix` and the rows of `oppassers_per_dag` must line up.

## External services and credentials

| Service | Used for | Credential / config |
|---|---|---|
| Google Sheets API | Reading and writing all tabs | Service-account key file `gs_credentials.json` in the working directory, loaded with `oauth2client.ServiceAccountCredentials`. Scope: `https://www.googleapis.com/auth/spreadsheets`. The file is **not** in the repo and is gitignored. Contents: `[REDACTED]`. |
| Google Drive API | Required by gspread to open the spreadsheet | Same service account. Scope: `https://www.googleapis.com/auth/drive`. |
| The Cokido spreadsheet | The data store/UI described above | The spreadsheet ID is hardcoded in `GsheetWrapper.py` (`SAMPLE_SPREADSHEET_ID = "[REDACTED]"`). The spreadsheet must be shared with the service account's e-mail address. |

There are no environment variables, databases or other network services. OR-Tools runs locally.

## Python packages imported

| Package | Imported in | Used for |
|---|---|---|
| `gspread` | `GsheetWrapper.py` | Google Sheets client (authorize, open by key, worksheets, cell read/write). |
| `oauth2client` (`oauth2client.service_account`) | `GsheetWrapper.py` | Service-account credentials. This library is deprecated upstream. |
| `ortools` (`ortools.sat.python.cp_model`) | `Calculation.py`, `SolutionPrint.py` | CP-SAT model, solver and solution callback. |
| `pandas` | `Calculation.py`, `DataHandler.py` | Sheet data as DataFrames, grouping and merging. |
| `numpy` | `DataHandler.py`, `SolutionPrint.py` | Matrices for the solver, solution arrays. |
| `math`, `time`, `random` | standard library | NaN checks, polling sleep/timestamps, result-tab names. |

The other entries in `requirements.txt` (google-auth, httplib2, protobuf, requests, etc.) are transitive dependencies.

## Known issues observed in the original code

These describe the code as found. None of them have been changed.

- **Run flag set early:** `Calculation.py` sets the run flag to `writing results` before the solver starts.
- **Invalid raise:** `raise '...'` (more than 5 parents in a family) raises a string. That is a `TypeError` in Python 3, so the intended message is lost.
- **Possible crash when writing results:** `SolutionPrinter` starts with 10 placeholder `0` entries. If fewer than 10 improving solutions are found, `write_results()` receives an integer `0`, and `pd.DataFrame(0)` raises.
- **"Top 10" is not really top 10:** the kept list holds the most recent solutions that were at least as good as the best so far, not a ranked top 10. Its scores are passed to `write_results()` but never written to the sheet.
- **Result-tab name collisions:** result tabs get random names (1–10000), which can collide.
- **Unclear note in `main.py`:** it contains the comment "update gsheet zegt dat het geen json is", which points to an unresolved issue with the gsheet update call.
- **Assumed row order:** the cost matrix assumes the `availability` and `parents` rows are in the same order (both are sorted by `ParentID`).
