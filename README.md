# T4D‑Project – **End‑to‑End Guide**

FastAPI • amts\_pipeline • CSV Splitter • React / Tailwind UI

> **Zero‑to‑running.** Follow the commands at the bottom and you’ll have
> – the AMTS watcher generating Δ‑files
> – the REST API on `http://localhost:8000`
> – the React UI hot‑reloading on `http://localhost:5173`.

---

## Table of Contents

1. [Repo layout](#repo)
2. [Python back‑end](#backend)
   2.1 [Setup](#setup) 2.2 [run.py launcher](#launcher) 2.3 [CSV splitter](#splitter)
3. [FastAPI service](#api)
4. [React front‑end](#frontend)
5. [One‑liner start/stop](#commands)
6. [Troubleshooting FAQ](#faq)

---

<a id="repo"></a>

## 1 Repository layout

```text
T4D‑project/
├─ amts_pipeline/           ← core data‑processing package
│   ├─ cleaner.py
│   ├─ splitter.py          ← simple splitter  (CLI: -m amts_pipeline.splitter)
│   ├─ watcher.py           ← file‑watcher for Settings.xlsx
│   ├─ settings.py          ← loads “Settings” sheet
│   ├─ file_profiles.py     ← loads “FileProfiles” sheet
│   └─ …
├─ api/                     ← FastAPI micro‑service
│   ├─ main.py              ← creates `app` + spawns watcher‑thread
│   ├─ routes.py            ← all `/api/*` endpoints
│   ├─ models.py            ← Pydantic DTOs
│   └─ deps.py              ← thin wrappers around amts_pipeline
├─ run.py                   ← **interactive launcher** (splitter / watcher / full‑run)
├─ Settings.xlsx            ← workbook with two sheets:
│     • Settings       (point‑level config, one row = one slice, contains SliceID)
│     • FileProfiles  (file‑level config: Match, TimeZone, column names…)
├─ requirements.txt         ← pinned Python deps
└─ ui/                      ← React + Vite front‑end (TypeScript)
    ├─ src/ …
    └─ tailwind.config.js
```

---

<a id="backend"></a>

## 2 Python back‑end

<a id="setup"></a>
\### 2.1 Requirements & virtual‑env

```bash
python -m venv .venv
# Windows‑PS:  .\.venv\Scripts\Activate
source .venv/bin/activate
pip install -r requirements.txt         # pinned, builds cleanly on Python 3.11+
```

`requirements.txt`

```text
fastapi==0.111.0
uvicorn[standard]==0.30.1
pydantic==2.7.1
pandas==2.2.2
numpy==1.26.4
openpyxl==3.1.2
XlsxWriter==3.2.0
matplotlib==3.9.0
watchdog==4.0.1
python-dateutil==2.9.0
tzdata==2024.1
```

<a id="launcher"></a>
\### 2.2 `run.py` – interactive launcher
Run **one command** and pick what you need:

```powershell
(.venv) PS> python run.py
=== AMTS launcher ===
 1) Run CSV splitter (live)
 2) Run Settings watcher (live Δ‑generator)
 3) One‑off full pipeline run
 q) Quit
Select option:
```

Prompts for paths, builds exact CLI, spawns child process.

<a id="splitter"></a>
\### 2.3 CSV splitter (`amts_pipeline.splitter`)
Splits each raw CSV into per‑point CSVs under `SeparatedRoot`, then moves the raw file to `archive/`.

```bash
python -m amts_pipeline.splitter \
       --export-root    "C:/T4D_Export/PapeSOE_TTC" \
       --separated-root "D:/Separated"
```

Patterns, TZ and column names come from **FileProfiles** sheet.

---

<a id="api"></a>
\## 3 FastAPI service (`api/main.py`)

* creates `FastAPI()` with CORS
* mounts `/api` router
* starts watcher‑thread so Δ‑files & plots update

\### Endpoints

| Method | Path                     | Response        | Purpose            |
| ------ | ------------------------ | --------------- | ------------------ |
| GET    | `/api/settings`          | `SettingsRow[]` | Active rows        |
| PUT    | `/api/settings/{row_id}` | `{ok}`          | Patch cell         |
| GET    | `/api/deltas`            | `DeltaResponse` | Last *n* hours     |
| GET    | `/api/outputs/sites`     | list            | Browse outputs     |
| GET    | `/api/logs`              | text            | Tail logs          |
| POST   | `/api/command`           | `{queued}`      | `full_build` / etc |

---

<a id="frontend"></a>
\## 4 React front‑end

```bash
cd ui
npm install
npm run dev     # http://localhost:5173
```

* Vite proxy rewrites `/api/*` → `localhost:8000`.
* Tailwind v3 + `@tailwindcss/vite`.
* Components via `shadcn/ui`.
* Data via **TanStack Query** object form.

---

<a id="commands"></a>
\## 5 Run / Stop quick‑start

```bash
# back‑end + hot‑reload
uvicorn api.main:app --reload

# OR interactive launcher
python run.py

# front‑end dev
cd ui && npm run dev
```

---

<a id="faq"></a>
\## 6 Troubleshooting FAQ

| Problem                              | Fix                                                              |
| ------------------------------------ | ---------------------------------------------------------------- |
| `worksheet "FileProfiles" not found` | Ensure workbook has **Settings** and **FileProfiles** sheets.    |
| Splitter does nothing                | Confirm `Match` glob actually matches (`dir` the folder).        |
| TanStack “Bad argument type”         | Use object form: `useQuery({ queryKey, queryFn })`.              |
| Duplicate logs in console            | Logging propagates; call `get_logger(__name__)` once per module. |

---

**Happy monitoring!** Update baselines in *Settings.xlsx*, commit, deploy.