T4D-Project – End-to-End Monitoring Pipeline
This guide provides a zero-to-running walkthrough for the T4D project. By following the commands, you will have:

The AMTS watcher generating Δ-files from your settings.

The REST API running on http://localhost:8000.

The React UI hot-reloading on http://localhost:5173.

Table of Contents
Repository Layout

Python Back-end

Setup & Requirements

The run.py Launcher

CSV Splitter Details

FastAPI Service

React Front-end

Run / Stop Quick-start

Troubleshooting FAQ

1. Repository Layout
The project is organized into distinct modules for data processing, API services, and the user interface.

T4D-project/
├─ amts_pipeline/       ← Core data-processing package
│  ├─ cleaner.py
│  ├─ splitter.py        ← Simple CSV splitter (CLI: -m amts_pipeline.splitter)
│  ├─ watcher.py         ← File-watcher for Settings.xlsx
│  ├─ settings.py        ← Loads the "Settings" sheet
│  ├─ file_profiles.py   ← Loads the "FileProfiles" sheet
│  └─ ...
├─ api/                 ← FastAPI micro-service
│  ├─ main.py            ← Creates `app` + spawns the watcher thread
│  ├─ routes.py          ← All /api/* endpoints
│  ├─ models.py          ← Pydantic data transfer objects (DTOs)
│  └─ deps.py            ← Thin wrappers around amts_pipeline
├─ ui/                  ← React + Vite front-end (TypeScript)
│  ├─ src/...
│  └─ tailwind.config.js
├─ run.py               ← Interactive launcher (splitter / watcher / full-run)
├─ Settings.xlsx        ← Workbook with two sheets:
│  │ • Settings        (Point-level config, one row = one slice)
│  │ • FileProfiles    (File-level config: Match, TimeZone, column names…)
└─ requirements.txt     ← Pinned Python dependencies

2. Python Back-end
Setup & Requirements
First, create and activate a Python virtual environment, then install the required packages.

# Create the virtual environment
python -m venv .venv

# Activate it (command differs by shell)
# Windows PowerShell:
.\.venv\Scripts\Activate
# macOS / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

The requirements.txt file contains all necessary packages, tested on Python 3.11+.

The run.py Launcher
For ease of use, an interactive launcher is provided. Simply run the script and choose an option. It will prompt for any required paths and build the correct CLI command for you.

(.venv) PS> python run.py

=== AMTS launcher ===
 1) Run CSV splitter (live)
 2) Run Settings watcher (live Δ-generator)
 3) One-off full pipeline run
 q) Quit
Select option:

CSV Splitter Details
The splitter module (amts_pipeline.splitter) can be run standalone to watch a folder, split raw CSVs into per-point files, and archive the originals. The glob pattern, time zone, and column names are configured in the FileProfiles sheet of Settings.xlsx.

python -m amts_pipeline.splitter \
    --export-root    "C:/T4D_Export/PapeSOE_TTC" \
    --separated-root "D:/Separated"

3. FastAPI Service
The API is the central hub, providing data to the front-end.

Creates a FastAPI() app with permissive CORS for local development.

Mounts all API routes from api/routes.py.

Spawns the watcher.py script in a background thread so that Δ-files and plots update automatically as Settings.xlsx is changed.

Runs under Uvicorn, which provides hot-reloading during development.

Key Endpoints
Method

Path

Response

Purpose

GET

/api/settings

SettingsRow[]

Live view of all active rows.

PUT

/api/settings/{row_id}

{ok}

Patch a single cell in the settings.

GET

/api/deltas

DeltaResponse

Get deltas for a point over the last n hours.

GET

/api/outputs/sites

list

Get the root of the output directory tree.

GET

/api/logs

log tail

Live tail of logs on a per-site basis.

POST

/api/command

{queued}

Send commands like full_build or stop.

4. React Front-end
The UI is a modern React application built with Vite.

Proxy: Vite is configured to rewrite all /api/* requests to the back-end at http://localhost:8000.

Styling: Tailwind CSS v3 with tailwindcss-animate.

Components: Uses shadcn/ui for pre-built, accessible components.

State Management: TanStack Query (v5) for server-state management.

Setup Commands
# Navigate to the UI directory
cd ui

# Install dependencies
npm install

# Start the development server
npm run dev

The UI will be available at http://localhost:5173.

5. Run / Stop Quick-start
Follow these steps in separate terminals to get the full system running.

Start the Back-end API This also starts the file watcher automatically.

# Run with hot-reloading enabled
uvicorn api.main:app --reload

The API will be live at http://localhost:8000, with interactive docs at http://localhost:8000/docs.

Start the Front-end

# In a new terminal
cd ui && npm run dev

The UI will be live at http://localhost:5173.

(Optional) Run the CSV Splitter If you need to process raw CSVs, run the splitter in a third terminal.

python -m amts_pipeline.splitter \
    --export-root    "C:/T4D_Export/PapeSOE_TTC" \
    --separated-root "D:/Separated"

6. Troubleshooting FAQ
Issue / Error Message

Fix

worksheet "FileProfiles" not found

Your Settings.xlsx must contain two sheets named Settings and FileProfiles. Check spelling.

Splitter does nothing

Confirm the Match glob pattern in FileProfiles actually matches your CSV filenames.

Bad argument type – TanStack Query

The query must be in object form: useQuery({ queryKey, queryFn }).

FastAPI 500 error

A NaN or Inf value may have been included in JSON. Ensure the UI calls /api/settings which sanitizes values.

ImportError: get_logger

You may have an old import. Ensure it is from amts_pipeline.log_utils import get_logger.

That’s it! Adjust baselines in Settings.xlsx, and the entire pipeline will update automatically. Happy monitoring!