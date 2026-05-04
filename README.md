# NetSys-Home

An intent-based home Wi-Fi management app backed by OpenWRT. You type what you
want in plain English ("block my gaming console", "create a guest network"),
a Random Forest classifier maps it to one of four actions, and the app writes
the corresponding firewall, isolation, guest-network, or scheduled-block rules
straight to your router via ubus.

```
┌────────────┐   intent text    ┌──────────────┐   action   ┌───────────────┐
│  React UI  │ ───────────────▶ │  FastAPI     │ ─────────▶ │  OpenWRT      │
│  (Vite)    │ ◀─────────────── │  + sklearn   │ ◀───────── │  ubus / UCI   │
└────────────┘   policy + MAC   └──────────────┘  firewall  └───────────────┘
```

## Features

- **Plain-English intents.** TF-IDF + Random Forest classifier (120 labelled
  examples, 30 per class) maps free text to `block`, `isolate`,
  `guest_network`, or `schedule_block`. Confidence is surfaced live in the UI.
- **Real router enforcement.** Authenticated ubus JSON-RPC client writes UCI
  firewall rules, dual isolation rules, full guest networks (interface +
  DHCP pool + zone + optional SSID), and cron-driven scheduled blocks.
- **Live device discovery.** Merges `luci-rpc getHostHints` and DHCP leases
  with the persisted device list, preserving user-assigned names.
- **Reversible policies.** Deleting a policy undoes its router-side effect.
- **Graceful degradation.** Every router call falls back cleanly when the
  router is offline — the app stays usable, policies stay saved, enforcement
  flag tells you what actually got applied.
- **Light/dark theme**, delete confirmations, toast feedback, skeleton loaders
  — the small things that make a real app feel like a real app.

## Quick start

### Option A — Docker (one command, recommended for graders)

```bash
cp backend/.env.example backend/.env   # edit OPENWRT_PASS
docker compose up --build
# App at http://localhost:5000
```

The container builds the React frontend, installs Python deps, trains the ML
model, and starts uvicorn — all in one step. The OpenWRT VM still runs
separately (or skip it; the app degrades gracefully when offline).

### Option B — Local dev

#### 1. OpenWRT VM (optional)

```bash
./scripts/start-openwrt-vm.sh
# LuCI:   http://localhost:8080
# ubus:   http://localhost:8080/ubus
# SSH:    ssh root@localhost -p 2222
```

#### 2. Backend (FastAPI on port 5000)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit credentials
python3 -m classifier.train   # trains model.pkl
python3 app.py                # http://127.0.0.1:5000  ·  /docs for Swagger
```

#### 3. Frontend (Vite on port 5173)

```bash
cd frontend
npm install
npm run dev                   # proxies /api → uvicorn:5000
```

For a single-port production deployment, run `npm run build` then
`python3 app.py` — FastAPI serves `frontend/dist/` directly.

### 4. Tests

```bash
cd backend && source .venv/bin/activate
python3 -m pytest tests/ -v   # 33 cases, ~1s, mocks the router
```

## API

| Method | Path                       | Description                                    |
| ------ | -------------------------- | ---------------------------------------------- |
| GET    | `/api/devices`             | Live (merged) or stored device list            |
| POST   | `/api/devices`             | Add device manually                            |
| POST   | `/api/intent`              | Classify + persist + enforce                   |
| GET    | `/api/policies`            | List active policies                           |
| DELETE | `/api/policies/{id}`       | Remove policy (reverses router-side effect)    |
| POST   | `/api/classify`            | ML-classify free text only                     |
| GET    | `/api/status`              | Router + classifier health + app version       |
| GET    | `/docs`, `/redoc`          | Auto-generated OpenAPI explorers               |

`POST /api/intent` accepts either `{action}` or `{text}` (free-form, classified
on the server). Response includes `enforced: bool` so the UI can distinguish
"saved locally" from "applied on the router."

## Configuration

`backend/.env` (gitignored — copy from `.env.example`):

| Variable          | Default                                       | Notes                                |
| ----------------- | --------------------------------------------- | ------------------------------------ |
| `OPENWRT_HOST`    | `192.168.1.1`                                 | Use `127.0.0.1` against the QEMU VM  |
| `OPENWRT_PORT`    | `80`                                          | `8080` against the QEMU VM           |
| `OPENWRT_USER`    | `root`                                        |                                      |
| `OPENWRT_PASS`    | —                                             | Required                             |
| `OPENWRT_TIMEOUT` | `10`                                          | Per-request seconds                  |
| `FASTAPI_DEBUG`   | `0`                                           | `1` enables uvicorn `--reload`       |
| `CORS_ORIGINS`    | `http://localhost:5173,http://localhost:5000` | Comma-separated allowed origins      |

## Architecture

```
backend/
  app.py                  FastAPI routes + uvicorn entry
  schemas.py              Pydantic request/response models
  devices.py              Device CRUD + merge_live()
  policies.py             Policy CRUD with JSON persistence
  openwrt.py              ubus client + policy enforcement engine
  classifier/
    intent_classifier.py  TF-IDF + Random Forest pipeline
    train.py              python3 -m classifier.train
  data/
    devices.json          Persisted devices (auto-merged with live)
    policies.json         Persisted policies
    training_data.json    120 labelled intents
  tests/                  pytest + FastAPI TestClient (33 cases)
  Dockerfile              Container build (frontend + backend in one image)

frontend/src/
  components/             AppShell, DevicesPanel, IntentPanel, PoliciesPanel
  components/ui/          shadcn-style primitives (no shadcn CLI)
  hooks/                  useDevices, usePolicies, useStatus, useDebounced
  lib/api.ts              Typed fetch client with structured ApiError
  lib/types.ts            TS mirrors of the Pydantic schemas

docker-compose.yml        Single-service compose for one-command launch
```

See [`CHANGELOG.md`](CHANGELOG.md) for the per-version history.

## Limitations

- **No auth.** Anyone on the same network as the API can change policies.
- **Single router.** Multi-router routing is not modelled.
- **Bridge-level isolation** between devices on the same L2 segment requires
  `ebtables` or per-VLAN assignment; `apply_isolation` blocks routed traffic
  only.
- **Guest network teardown is manual** — deleting a `guest_network` policy
  removes the local entry but leaves the SSID/zone in place.
- **Wireless SSID creation** is skipped on the x86 QEMU VM (no radios) and
  works only on real hardware with a radio present.
