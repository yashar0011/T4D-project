# T4D‑Project – **Full‑Stack Guide**

*(FastAPI + amts\_pipeline + React/TypeScript UI)*

> **Copy‑paste ready.** Follow the commands at the bottom and you’ll have the back‑end watcher running, the REST API online at `http://localhost:8000`, and the front‑end dev server hot‑reloading at `http://localhost:5173`.

---

\## Table of Contents

1. [Repository layout](#repo)
2. [Python back‑end](#backend)
      2.1 [Requirements & setup](#req)
      2.2 [FastAPI app](#app)
      2.3 [Watcher thread](#watch)
      2.4 [Routes & schemas](#routes)
3. [React + Tailwind UI](#frontend)
      3.1 [Vite config](#vite)
      3.2 [TanStack Query pattern](#query)
      3.3 [shadcn/ui components](#shadcn)
4. [One‑line start/stop](#commands)
5. [Troubleshooting FAQ](#faq)

---

<a id="repo"></a>
\## 1 Repository Layout

```
T4D‑project/
├─ amts_pipeline/           ← existing robust data pipeline
│   └─ …
├─ api/                     ← FastAPI micro‑service
│   ├─ __init__.py
│   ├─ main.py             ← creates `app` + spawns watcher
│   ├─ routes.py           ← all `/api/*` endpoints
│   ├─ models.py           ← Pydantic DTOs
│   ├─ deps.py             ← thin wrappers around amts_pipeline
│   └─ watcher_runner.py   ← background file‑watcher thread
├─ outputs/                 ← generated Δ‑CSV / plots / logs
├─ Settings.xlsx            ← single source of truth for sensors
├─ requirements.txt         ← pinned Python deps  (see below)
└─ ui/                      ← React + Vite front‑end (TypeScript)
    ├─ src/
    │   ├─ components/…
    │   ├─ pages/…
    │   ├─ App.tsx
    │   └─ api.ts          ← Axios wrapper → `/api`
    ├─ tailwind.config.js
    ├─ tsconfig.app.json
    └─ vite.config.ts
```

---

<a id="backend"></a>
\## 2 Python Back‑End <a id="req"></a>
\### 2.1 Requirements & virtual‑env

```bash
python -m venv venv
source venv/bin/activate    # PowerShell: .\venv\Scripts\Activate
pip install -r requirements.txt
```

`requirements.txt` (pinned versions):

```
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
python-dotenv==1.0.1  # optional
ruff==0.4.8          # dev‑time linter
```

<a id="app"></a>
\### 2.2 `api/main.py`
Creates a FastAPI application, mounts CORS, includes routes, then spawns the background watcher so the Δ‑CSV and plots are generated continuously.

<a id="watch"></a>
\### 2.3 Background watcher (`watcher_runner.py`)
A daemon `threading.Thread` that forwards commands through a queue (`run_once`, `full_build`, `reload_settings`, `stop`). This isolates long‑running file IO from async request workers.

<a id="routes"></a>
\### 2.4 Key Endpoints

|  Method  |  Path                        |  Response       | Purpose                                           |
| -------- | ---------------------------- | --------------- | ------------------------------------------------- |
| GET      |  `/api/settings`             | `SettingsRow[]` | Live view of `Settings.xlsx` (only *active* rows) |
| PUT      |  `/api/settings/{row_id}`    | `{ok}`          | Update one row (immediately picked up by watcher) |
| GET      |  `/api/deltas?point=&hours=` | `DeltaResponse` | Last *n* hours of Δ‑values for a point            |
| GET      |  `/api/outputs/sites`        | `{sites:[…]}`   | List of output site folders (for tree)            |
| GET      |  `/api/outputs/file?path=`   | *file*          | Direct download of any generated artifact         |
| GET      |  `/api/logs?tail=`           | `LogTail`       | Tail of most recent site log                      |
| POST     |  `/api/command`              | `{queued}`      | Push a command to watcher queue                   |

---

<a id="frontend"></a>
\## 3 React Front‑End (Vite + Tailwind)

```bash
cd ui
npm install                # installs deps in package.json
npm run dev                # http://localhost:5173
```

<a id="vite"></a>
\### 3.1 `vite.config.ts`

* Tailwind plugin is injected: `plugins: [react(), tailwindcss()]`.
* Dev‑server proxies every `/api/*` call to `localhost:8000` so the JS code never needs the full origin.
* `@/` import alias → `src/` (configured both in Vite and `tsconfig.app.json`).

<a id="query"></a>
\### 3.2 Data‑loading pattern
All components use **TanStack Query v5** (formerly react‑query). **Only the object signature is allowed**:

```ts
const { data } = useQuery({
  queryKey: ["deltas", point],
  queryFn : () => api.get(`/deltas`, { params:{ point, hours:24 } })
                     .then(r => r.data),
  refetchInterval: 10000,
});
```

<a id="shadcn"></a>
\### 3.3 shadcn/ui

```bash
cd ui
npx shadcn@latest init              # once – scaffolds config files
npx shadcn@latest add button input card
```

Components are now imported as `@/components/ui/button` etc.

---

<a id="commands"></a>
\## 4 Run / Stop Commands

```bash
# 1)  activate venv then …
uvicorn api.main:app --reload     # localhost:8000

# 2)  in another terminal
cd ui && npm run dev             # localhost:5173

# optional: force rebuild all Δ files
curl -X POST localhost:8000/api/command -d '{"action":"full_build"}'
```

---

<a id="faq"></a>
\## 5 Troubleshooting FAQ

|  Issue                                            |  Fix                                                                                        |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `ImportError: cannot import name get_settings_df` | You saved an old `deps.py`. Ensure only **one** helper set – copy the full file above.      |
| `shadcn init: No Tailwind config`                 | Run `npm install tailwindcss postcss autoprefixer && npx tailwindcss init -p` inside *ui/*. |
| Vite white page, console 404 `/api/deltas`        | FastAPI not running or proxy mis‑configured. Start back‑end then reload.                    |
| TanStack Query “Bad argument type”                | Use the **object** form: `useQuery({ queryKey:[…], queryFn })`.                             |

---

**Happy monitoring!**  Adjust baselines in `Settings.xlsx`, commit everything to Git, and deploy with any process‑manager (e.g. `gunicorn -k uvicorn.workers.UvicornWorker api.main:app`).
