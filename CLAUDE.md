# Cokidoplanner

Scheduling tool for Cokido: it assigns parents to babysitting ("oppas") days with an OR-Tools CP-SAT solver. A Google Sheet is both the input and the output.

## Setup & run

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

- You need `gs_credentials.json` (a Google service-account key) in the repo root. It is gitignored. Never commit it or print its contents.
- `main.py` polls the sheet every 20 s. When the `Readme!D20` cell is `1`, it runs the calculation and writes the result back into that cell.
- No test suite exists.

## Layout

- `main.py`: polling loop (run flag in `Readme!D20`)
- `GsheetWrapper.py`: authenticates with gspread and opens the spreadsheet by its hardcoded ID
- `DataHandler.py`: `CokidoDataHandler` reads the worksheets `children`, `parents`, `presence`, `availability`, `availability-fix`, `oppasdagen`, and `oppassers_per_dag` into pandas, then writes the results back as new worksheets
- `Calculation.py`: `run_calculation()` builds and solves the CP-SAT model
- `SolutionPrint.py`: solver callback that keeps the top solutions

## Notes

- Running the code edits the live Google Sheet: it deletes and recreates the result tabs. Don't run it against production data unless asked.
- Comments and sheet names are in Dutch.
