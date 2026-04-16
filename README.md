# Apple-Data-Visualizer

A visually appealing desktop app that imports Apple Health export data, stores normalized health metrics in SQLite, and presents them in a modern analytics dashboard with a strong focus on sleep analysis.

## Current Status

The repository now includes the first implementation pass for the documented architecture:

- runnable `main.py` desktop entrypoint
- `app/` package with UI, services, parser, database, models, charts, and utils modules
- PySide6 application shell with sidebar navigation and scaffolded pages
- first-run SQLite bootstrap with the initial MVP tables
- import-file inspection stub for `export.xml` and zip inputs

Parser, import persistence, and sleep analytics are the next implementation steps.

## Run

1. Create and activate a Python 3 virtual environment.
2. Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

3. Launch the app:

```bash
python3 main.py
```

## Planning Docs

The repo's implementation source of truth now lives in:

- `docs/spec-sheet.md`
- `docs/implementation-plan.md`

These docs translate the original design brief into an MVP-first product spec and phased execution roadmap for the project.
