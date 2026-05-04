# NetSys-Home Changelog

## [1.1.0] — Docker packaging

### Added
- **`Dockerfile`** — multi-stage build that compiles the React frontend in a
  Node 20 stage, then drops the static bundle into a Python 3.12-slim runtime
  with the FastAPI backend. The classifier is trained at build time so the
  image is fully self-contained.
- **`docker-compose.yml`** — single-service compose that exposes port 5000
  and reads optional config from `backend/.env`. Sensible defaults via
  `${VAR:-default}` so the container starts even without an env file.
- **`.dockerignore`** — keeps `node_modules`, `.venv`, build artifacts, and
  the OpenWRT VM image out of the build context.
- **README "Docker (one command)"** quickstart section.

### Notes
- The OpenWRT VM still runs separately — Docker-in-QEMU is messy and not
  worth it for this app's use case. The container points at `OPENWRT_HOST`
  the same way local dev does.
- Local dev workflow is unchanged: `python3 app.py` + `npm run dev` still
  works exactly as before. Docker is purely additive.

---

## [1.0.0] — Phase 5: Release polish

### Added
- **Reverse enforcement on policy delete.** `DELETE /api/policies/{id}` now
  undoes the router-side effect before removing the local entry:
  `block` and `schedule_block` call `apply_firewall_rule(mac, "unblock")`,
  `isolate` calls `apply_isolation(mac, False)`. `guest_network` is left in
  place (teardown is destructive and ambiguous). Best-effort — a router
  failure does not block the local delete.
- **Light/dark theme toggle.** Sun/Moon button in the top bar flips between
  the two CSS-variable themes; choice persists in `localStorage` under
  `netsys-theme`. Dark remains the default.
- **Delete confirmation dialog.** A new `AlertDialog` UI primitive guards the
  trash button on `PoliciesPanel`; the destructive API call only fires after
  explicit confirm. Backdrop click cancels.
- **Configurable CORS origins.** `CORS_ORIGINS` env var (comma-separated)
  replaces the wildcard `["*"]`. Defaults to `localhost:5173,localhost:5000`
  so dev and bundled-prod both work out of the box. Methods locked to
  `GET, POST, DELETE` instead of wildcard.
- **3 new pytest cases** (33 total) covering reverse enforcement for
  `block`, `isolate`, and the no-MAC short-circuit path.

### Changed
- **Backend version → 1.0.0** (was 0.4.0). Frontend `package.json` and the
  sidebar pill bumped to match. Reflected in `GET /api/status.app_version`.
- **README rewritten** with a real quickstart, architecture summary, and API
  reference (was two lines).

### Notes
- Phase 5 explicitly does *not* include auth, multi-router, or real-time
  push — those remain future work. 1.0 is "the home-network app you can
  actually use end-to-end without surprises."

---

## [0.4.1] — Phase 4 live-verification fixes

### Fixed
- **`create_guest_network` returned `enforced: false` on a clean re-apply.**
  ubus `uci apply` returns code 5 (`NO_DATA`) when there are no pending
  staged changes (idempotent call on already-committed sections). The old
  code treated any non-zero return as failure. Both `_uci_commit_and_reload`
  and `create_guest_network` now treat codes 0 and 5 as success.
- **`create_guest_network` silently failed to bring up the guest interface.**
  `/etc/init.d/network restart` is blocked by the ubus file-service ACL
  (returns code 6 / PERMISSION_DENIED). Switched to `/sbin/ifup netsys_guest`
  which is permitted and sufficient to activate the new interface.

### Verified (live OpenWRT 23.05.5 VM)
- `GET /api/status` — connected, version/hostname/model all populated ✓
- `GET /api/devices` — live discovery + merge with persisted names ✓
- `POST /api/intent action=block` — UCI rule written, `enforced: true` ✓
- `POST /api/intent action=isolate` — two isolation rules written ✓
- `POST /api/intent action=guest_network` — all four UCI sections committed,
  interface brought up via ifup, `enforced: true` ✓
- `POST /api/intent action=schedule_block` — disabled UCI rule + cron
  entries written, `enforced: true` ✓
- ML text path (`text=` instead of `action=`) — classifier called,
  `classification` block included in response ✓
- All edge cases: no MAC device → `enforced: false`; enforcement failure
  → policy still persisted; unknown device → 404 ✓

---

## [0.4.0] — Phase 4: FastAPI + React + UI Overhaul

### Backend (Flask → FastAPI)
- **Migrated `backend/app.py`** from Flask to FastAPI; uvicorn is the new
  dev/prod server. Same `/api/*` surface, same JSON shapes, but now with:
  - **Pydantic schemas** (`backend/schemas.py`) validating every request and
    response. Invalid payloads return `422` with structured detail; Pydantic
    rejects bad MACs, negative device IDs, blank names, etc.
  - **Auto OpenAPI docs** at `/docs` and `/redoc`
  - **`Action` literal type** so any future drift from the four valid actions
    is caught at the schema layer instead of in the route body
  - Static-file serving for the built React bundle preserved (was: `send_from_directory`)
- **`backend/tests/`**: 30 pytest cases using `fastapi.testclient.TestClient`
  - Per-test isolated `devices.json` / `policies.json` (tmp_path fixture)
  - `fake_openwrt` fixture monkeypatches the `openwrt` module to stub all
    six router calls — tests run in <1s and don't need a live VM
  - Coverage: status, device list/add/merge-live, intent (all 4 actions +
    edge cases: missing MAC, failed enforcement, invalid action, unknown
    device), policy CRUD, classify (parametrized + empty/missing input)
- **`requirements.txt`**: dropped Flask + flask-cors, added fastapi,
  uvicorn[standard], pydantic, pytest, httpx; relaxed sklearn/numpy pins
  to support Python 3.14
- **`.env.example`**: `FLASK_DEBUG` → `FASTAPI_DEBUG` (Flask key still honored
  as a fallback so existing `.env` files keep working)

### Frontend (Vue → React + TypeScript + Tailwind)
- **Full rewrite** of `frontend/src/`. Vue 3 + plain CSS replaced with
  React 18 + TypeScript + Vite 6 + Tailwind v3 + hand-rolled
  shadcn-style components (`Button`, `Card`, `Input`, `Select`, `Badge`,
  `Skeleton`, `Label`, plus a self-contained `Toaster`).
- **Real app shell** — sidebar nav + sticky top bar with live status pills
  (router connected, classifier active, app version), Lucide iconography,
  CSS-variable design tokens, dark by default with a light token set ready
  for a future theme toggle.
- **Hooks**: `useDevices`, `usePolicies`, `useStatus` (15s poll),
  `useDebounced`. All wrap `lib/api.ts`, which surfaces a typed `ApiError`
  carrying both status and FastAPI detail.
- **DevicesPanel**: live-discovery-aware table with type-icon avatars,
  refreshed-at timestamp, manual-add inline form, skeleton loader, empty
  state, retry-on-error banner.
- **IntentPanel**: free-text field with debounced `/api/classify` call,
  inline confidence meter (red/amber/green), MAC-warning callout when the
  selected device can't be enforced, live preview pane that becomes a
  result panel with `enforced` badge after submit. Schedule action now
  uses a real `<input type="time">`.
- **PoliciesPanel**: action-tinted rows with icons (block/isolate/guest/
  schedule), relative-time stamps, inline remove with toast feedback,
  proper empty/loading/error states.
- **Toast system**: `ToastProvider` + `useToast()`; four variants
  (default/success/destructive/warning) with auto-dismiss + manual close.
- **Build**: TS strict mode passes; production build is 64 KB gzipped JS
  + 5 KB gzipped CSS.

### Hardening / UX
- All network calls go through one typed client. Backend errors propagate
  to the UI with their FastAPI `detail` text (no more "Unable to load X"
  fog).
- Loading skeletons on first paint of every panel; spinning refresh icon
  while a manual refresh is in flight.
- Toast confirmations on every mutating operation; explicit "saved but not
  enforced" state when the router is offline or the device has no MAC.
- Status header polls `/api/status` every 15s so router/classifier state
  reflects reality without a page refresh.

### Notes
- `openwrt.py` is unchanged — the entire ubus client + policy enforcement
  engine from Phase 3 carries over untouched. The 30 pytest cases mock
  it; visual verification against a live VM is still recommended after
  pulling.
- Dev workflow: `python3 app.py` (still port 5000) + `npm run dev` (still
  port 5173, still proxies `/api`). Production: `npm run build` then
  `python3 app.py` serves the bundle.
- TypeScript is strict + `noUnusedLocals` + `noUnusedParameters` on, so
  CI builds will catch dead code early.

---

## [0.3.0] — Phase 3: OpenWRT Integration

### Added
- **Live ubus client** (`backend/openwrt.py`): authenticated JSON-RPC 2.0 session
  with auto token-refresh and graceful degradation when the router is offline
- **Policy enforcement engine** — four real OpenWRT operations:
  - `apply_firewall_rule(mac, "block"|"unblock")` — UCI firewall rule + reload
  - `apply_isolation(mac, bool)` — dual UCI rules blocking LAN↔device routed traffic
  - `create_guest_network(ssid)` — UCI network + DHCP pool + firewall zone + optional wireless SSID
  - `apply_schedule(mac, "HH:MM")` — disabled UCI rule + cron enable/disable jobs
- **Live device discovery** (`openwrt.discover_devices()`) — merges `luci-rpc getHostHints`
  and `getDHCPLeases`; returns connected hosts with MAC, IP, and hostname
- **`devices.merge_live()`** — non-destructive sync: preserves user-assigned names/types,
  updates IPs, appends newly discovered MACs
- **`GET /api/devices`** now returns live router data when connected, stored fallback when not
- **`POST /api/intent`** response now includes `"enforced": true/false`
- **`GET /api/status`** now reports real router firmware version and hostname
- **`.env` config** via `python-dotenv` (`OPENWRT_HOST`, `PORT`, `USER`, `PASS`, `TIMEOUT`)
- **`.env.example`** committed as credential template
- **`scripts/start-openwrt-vm.sh`** — one-command QEMU VM launcher with boot-wait and
  health check; KVM-accelerated, subnet-matched networking (`192.168.1.0/24`)

### Changed
- `app.py` loads `.env` at startup before any imports that read env vars
- `GET /api/status` delegates to `openwrt.get_status()` instead of returning a hardcoded stub

### Notes
- Bridge-level (L2) isolation between devices on the same segment requires `ebtables`;
  `apply_isolation` blocks routed traffic only
- Guest network wireless SSID is skipped on the x86 QEMU VM (no radio present);
  works on real hardware with at least one radio
- `.env`, `*.img`, and `model.pkl` are all gitignored

---

## [0.2.0] — Phase 2: ML Intent Engine

### Added
- **`IntentClassifier`** (`backend/classifier/intent_classifier.py`): real
  `TfidfVectorizer(ngram_range=(1,2), sublinear_tf=True)` +
  `RandomForestClassifier(n_estimators=200, class_weight="balanced")` sklearn pipeline
- **Training dataset** (`backend/data/training_data.json`): 120 labeled examples,
  30 per class (`block`, `isolate`, `guest_network`, `schedule_block`)
- **`classifier/train.py`**: runnable training script — `python3 -m classifier.train`
- **`POST /api/classify`**: live ML endpoint returning `{predicted_action, confidence, model}`
- **`POST /api/intent`** accepts `text` field — classifies via ML when `action` not provided;
  response includes `classification: {predicted_action, confidence}` when text path used
- **`GET /api/status`** reports `"classifier": "random_forest"` or `"stub"`
- **`openwrt.py`** stub adapter created with finalized function signatures for Phase 3
- **Free-text input in `IntentForm.vue`**: 400ms debounced live classification via
  `/api/classify`; updates action dropdown and shows confidence badge

### Changed
- `IntentClassifier` replaced Phase 1 stub (always returned `"block"`, no confidence)
- `requirements.txt` updated: added `scikit-learn==1.6.1`, `numpy==2.2.5`

---

## [0.1.0] — Phase 1: Foundation

### Added
- **`backend/devices.py`**: device CRUD with JSON file persistence (`data/devices.json`);
  atomic writes via `os.replace()`; `mac` field added for future OpenWRT compatibility
- **`backend/policies.py`**: policy CRUD with JSON file persistence (`data/policies.json`);
  enriched schema (`device_id`, `action`, `created_at`)
- **`backend/classifier/`**: empty scaffold (`__init__.py`, stub `intent_classifier.py`,
  skeleton `train.py`)
- **`backend/data/training_data.json`**: 12 initial labeled examples (3/class)
- **`GET /api/status`**: stub returning `{"openwrt": "disconnected"}`
- **`POST /api/classify`**: stub returning `{"predicted_action": "block", "confidence": null}`
- **`frontend/src/composables/useDevices.js`**: module-level singleton with single-fetch guard —
  eliminates duplicate `GET /api/devices` calls from `DeviceList` + `IntentForm`
- **`frontend/src/composables/usePolicies.js`**: shared policy state; `IntentForm` calls
  `fetchPolicies()` after submit so `PolicyList` auto-refreshes
- **`IntentForm`**: loading/disabled button state during POST; `schedule_block` time field

### Changed
- `app.py` split from 137-line monolith into routes-only file importing `devices`, `policies`
- Dual routing (`/devices` AND `/api/devices`) removed — `/api/` prefix only
- `debug=True` replaced with `FLASK_DEBUG` env var
- All endpoints now return proper 400/404 JSON errors instead of crashing
- `requirements.txt` pinned to exact versions
- `DeviceList.vue`, `IntentForm.vue`, `PolicyList.vue` migrated to composables

### Removed
- Hardcoded in-memory device and policy state
- Unused frontend assets: `vite.svg`, `vue.svg`, `hero.png`, `icons.svg`
- Generic Vite template `frontend/README.md`
- `<title>frontend</title>` → `<title>NetSys Home</title>`
