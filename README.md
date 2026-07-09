# Apple-Data-Visualizer

A visually appealing desktop app that imports Apple Health export data, stores normalized health metrics in a MariaDB database on your network, and presents them in a modern analytics dashboard with a strong focus on sleep analysis.

## Current Status

The repository now includes the first implementation pass for the documented architecture:

- runnable `main.py` desktop entrypoint
- `app/` package with UI, services, parser, database, models, charts, and utils modules
- PySide6 application shell with sidebar navigation and scaffolded pages
- first-run MariaDB schema bootstrap with the initial MVP tables (see "Database Setup (MariaDB)" below — a running MariaDB server and connection settings are required before the app will launch)
- import-file inspection stub for `export.xml` and zip inputs

Parser, import persistence, and sleep analytics are the next implementation steps.

## Database Setup (MariaDB)

The app stores data in a MariaDB database on your network — there is no
local/file-based storage mode. See `docs/mariadb-migration-spec.md` and
`docs/mariadb-migration-plan.md` for the full design and phased rollout that
produced this.

You'll need a MariaDB server already running on your network (10.5+). Create
the application database, user, and privileges by running the following
against it (for example via `mysql -h <server-host> -u root -p`):

```sql
CREATE DATABASE IF NOT EXISTS apple_health_data
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'apple_health_app'@'%' IDENTIFIED BY 'change-me-strong-password';

GRANT ALL PRIVILEGES ON apple_health_data.* TO 'apple_health_app'@'%';

FLUSH PRIVILEGES;
```

Notes:

- Replace `change-me-strong-password` with a strong password of your own —
  do not commit real credentials to this repo.
- `'apple_health_app'@'%'` allows the app user to connect from any host on
  the network. If you want to restrict this to your LAN subnet, replace `%`
  with a host pattern such as `'192.168.1.%'`.

Then tell the app how to reach that database. Copy `.env.example` to `.env`
in the repo root and fill in your values:

```bash
cp .env.example .env
```

```
APPLE_DV_DB_HOST=192.168.1.50
APPLE_DV_DB_PORT=3306
APPLE_DV_DB_NAME=apple_health_data
APPLE_DV_DB_USER=apple_health_app
APPLE_DV_DB_PASSWORD=change-me-strong-password
```

`.env` is gitignored. The app also reads these from real environment
variables if you'd rather set them that way instead of using a `.env` file.
On first launch the app connects to the configured server and creates its
tables automatically. If the server is unreachable or the credentials are
wrong, the app shows an error dialog instead of launching.

## Run

### With uv

1. Install dependencies and create the project environment:

```bash
uv sync
```

2. Set up your `.env` file as described in "Database Setup (MariaDB)" above — the app will not launch without it.

3. Launch the app:

```bash
uv run apple-data-visualizer
```

### Linux (Ubuntu) Qt runtime dependency

If you see an error about the Qt platform plugin `xcb` not loading, install the missing runtime dependency:

```bash
sudo apt update && sudo apt install -y libxcb-cursor0
```

Then run the app again:

```bash
uv run apple-data-visualizer
```

If needed, install additional common Qt xcb dependencies:

```bash
sudo apt install -y libxkbcommon-x11-0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-xinerama0 libxcb-xinput0 libegl1 libgl1-mesa-glx
```

You can also run the existing module entrypoint directly:

```bash
uv run python main.py
```

### With pip/venv

1. Create and activate a Python 3 virtual environment.
2. Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

3. Launch the app:

```bash
python3 main.py
```

## Import Apple Health Data

### Export from the Health app on iPhone

1. Open the `Health` app on your iPhone.
2. Tap `Summary`.
3. Tap your profile picture or initials in the top-right corner.
4. Tap `Export All Health Data`.
5. Choose a sharing method and save/send the export to your computer.

Apple exports your data as a zip archive. This app can import that zip directly, so you do not need to extract it first unless you want to work with the raw `export.xml` file yourself.

### Import into Apple Data Visualizer

1. Launch the app.
2. Click `Import Apple Health Export`.
3. Select either:
   - the Apple Health export `.zip` file
   - the extracted `export.xml` file
4. Wait for the import confirmation dialog.

The app stores imported data in your configured MariaDB database, skips duplicate imports automatically, and will show a warning count if some Apple Health record types were not imported.

## Planning Docs

The repo's implementation source of truth now lives in:

- `docs/spec-sheet.md`
- `docs/implementation-plan.md`

These docs translate the original design brief into an MVP-first product spec and phased execution roadmap for the project.

The SQLite → MariaDB storage migration is tracked separately in:

- `docs/mariadb-migration-spec.md`
- `docs/mariadb-migration-plan.md`
