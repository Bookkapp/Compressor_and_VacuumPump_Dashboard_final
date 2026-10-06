# Web App QA Report

**Assessment:** Needs revision before this dashboard is used for maintenance decisions or exposed beyond a tightly controlled network.

## 2026-09-23 integration and multi-tab checkpoint

- Correctness: Compressor Alert generation now belongs to OPERATION; Dashboard retains Vacuum Alerts. Direct Work Order `DONE` is rejected; linked Service Log and completion commit atomically.
- Latest local mock load (read-only app data, one process, local MySQL, gzip): 8 simultaneous simulated tabs × 2 rounds, 128 API requests including Compressor chart reads, 0 errors, p95 3.02 s; 16 tabs × 2 rounds, 256 requests, 0 errors, p95 3.62 s. An earlier non-gzip/cache run at 8 tabs had 19 timeouts and p95 13.4 s. These are separate bounded local observations, not a controlled benchmark, production capacity, or a browser-render benchmark. The current multi-worker architecture is not validated: each worker would own a poller, cache and WebSocket client set; use a single ingestion owner plus shared pub/sub before scaling out.
- With browser-style gzip request, average Compressor chart response transfer was 24.4 KB versus roughly 794 KB uncompressed in a local 4-tab sample; chart rendering speed was not measured.
- QA-01 mitigation in current source: an unset/weak `SECRET_KEY` is replaced by a random per-process development key; `APP_ENV=production` rejects it at startup. Unit tests cover this behavior. The historical deployed-server finding below remains a record of that earlier assessment; the production server was not modified or retested in this checkpoint.
- QA-02 mitigation in current source: magnitude-based automatic Compressor scaling was removed. `COMPRESSOR_SENSOR_SCALE` is explicit (`1` or `0.1`, default `1`), with a regression test using the recorded high-pressure example. Column-by-column unit confirmation with the source owner is still required before production. The earlier finding below records the old behavior.
- QA-04 mitigation in current source: startup user bootstrap now inserts missing accounts without updating existing password hashes, roles, or active flags. Production mode also refuses default/short/reused bootstrap passwords. Existing production accounts and provisioning still need an operations review; no deployed database was changed.
- QA-06/QA-11 mitigation in current source: recording a manual or linked Service Log no longer forces module/device status to NORMAL. Closing the Work Order remains independent of live fault state; telemetry/diagnostics must report recovery. Staging workflow verification remains open.
- Remaining production blockers: no accepted active ML/calibration profile, verified source timezone or approved alert budget/rollback in OPERATION SOT; no staging end-to-end test or prolonged concurrent soak; chart history source query still reads up to 2,000/3,000 recent rows rather than guaranteeing the selected entire time range; query plans/indexes need DBA review.

**QA date:** 2026-09-03 (Asia/Bangkok)

**Scope:** FastAPI API and authentication, MySQL metadata and read-only telemetry integration, React UI, Handler/Module hierarchy, charts, data quality, responsive rendering, accessibility, dependencies, and server operation.

No application fixes were made during this pass. The production frontend was rebuilt for verification, and QA screenshots were saved under `.tmp/`.

## Highest-priority blockers

### QA-01 — Critical — Authentication can be forged

The deployed `SECRET_KEY` is an empty string. Tokens are a custom base64 payload signed directly with that value in `app/auth.py`. A read-only runtime proof created a token without logging in: it received HTTP 200 from both `/api/users` and `/api/devices`; `/api/auth/me` returned 401 only because that one endpoint re-checks the user table.

**Impact:** Anyone who can reach port 5001 can create an admin token and read or modify dashboard data.

**Required fix:** Refuse startup when the secret is empty/weak, rotate it, invalidate all existing tokens, and use a standard session/JWT implementation that re-checks account state for privileged operations.

### QA-02 — Critical — Compressor values are conditionally divided by ten

`app/telemetry_sources.py` chooses a scale of `0.1` when any pressure or temperature field in a module is above 250, then applies that scale to every pressure and temperature field in the module.

Traced source row, Handler `070`, Compressor `M5`, recorded `2026-09-03 13:35:04`:

| Field | Raw MySQL | Dashboard mapping |
| --- | ---: | ---: |
| Hp 1st | 151.9 | 15.19 |
| Lp 1st | 30.4 | 3.04 |
| Hp 2nd | 314.8 | 31.48 |
| Lp 2nd | 38.3 | 3.83 |
| Temp High | 95.0 | 9.5 |
| Temp Low | -29.1 | -2.91 |

**Impact:** Charts, health scores, alarms, and exported data can be wrong by 10× depending on another channel's value.

**Required fix:** Define the unit/scale for every source column explicitly. Do not infer one shared scale from magnitude.

### QA-03 — Critical — “Predictive” diagnostics are not valid for compressor data

Each external update calls `compute_diagnostics()` with a list containing only the current sample. The local database currently contains **4,664 diagnostic snapshots; every snapshot has `sample_count = 1`, and zero snapshots have a non-zero temperature trend**. The AI fields are explicitly `MODEL_PENDING / ai-placeholder-v0`.

The same routine also treats Compressor `Hp_1st` as `pressure_kpa` and applies the Vacuum Pump target of **-95 to -60 kPa**. The rendered Compressor M1 page shows this incorrect target beneath a positive pressure value. Current module state is **78 WARNING + 75 MAINTENANCE_REQUIRED, with zero normal modules**.

**Impact:** The dashboard's maintenance recommendations and trend claims are not trustworthy.

**Required fix:** Use equipment-specific schemas, units, thresholds, and a real history window. Rename the feature from predictive/AI until a validated model is connected.

## Security and authorization

### QA-04 — High — Startup resets user security state

`seed_users()` runs on every startup and uses `ON DUPLICATE KEY UPDATE` to replace password hashes and roles and force `is_active = 1`. A disabled account is reactivated and any password/role change is overwritten after a restart.

### QA-05 — High — Token revocation and storage are unsafe

Most protected routes trust the signed token's user ID and role without checking that the account still exists or is active. WebSockets do the same. Tokens last 12 hours, are stored in browser `localStorage`, and are placed in the WebSocket URL query string, which can leak into access logs and diagnostics.

### QA-06 — High — A normal user can reset an arbitrary module to NORMAL

`create_maintenance_log()` allows any authenticated user to submit a log without a work order. If a `module_id` is supplied, it directly calls `update_module(..., {status: NORMAL})`, bypassing the admin dependency used by the module route.

### QA-07 — High — Weak perimeter controls

- Port 5001 listens on `0.0.0.0` over plain HTTP.
- Application and database passwords are very short; login has no throttling, lockout, or delay.
- CORS reflects an arbitrary origin while allowing credentials, methods, and headers.
- CSP, HSTS, frame protection, MIME-sniffing protection, referrer policy, permissions policy, and cache-control headers are absent.
- `/api/db/status` is public and returns hosts, ports, schema/table names, poll state, and raw error text.

### QA-08 — Medium — Known vulnerable JavaScript packages are installed

The installed tree contains ECharts 5.6.0, Browserslist 4.28.4, PostCSS 8.5.15, and Nano ID 3.3.15. Primary advisories mark these ranges as affected, although the current `npm audit` response reports zero findings. The build-tool issues have limited runtime reach in this app, but ECharts is shipped to browsers.

- ECharts XSS: https://github.com/advisories/GHSA-fgmj-fm8m-jvvx
- Browserslist crash/prototype write: https://github.com/advisories/GHSA-73wf-gq98-2v4g
- PostCSS source-map file disclosure: https://github.com/postcss/postcss/security/advisories/GHSA-fxqj-rqcc-2cmp
- Nano ID infinite loop: https://github.com/advisories/GHSA-2v37-7h3g-55p8

## Data and functional behavior

### QA-09 — High — The requested two-source Handler cannot appear with current data

The current sources contain one Vacuum handler (`HT9046MX-30`) and 19 Compressor handlers, with **zero shared handler keys**. `HT9046MX-111` is present in neither source. The grouping code can combine matching machine codes, but MySQL currently supplies no match or mapping table.

**Required fix:** Add/correct matching source records or maintain an authoritative source-device-to-handler mapping.

### QA-10 — High — Telemetry is mostly stale

Across runtime snapshots, 19–20 of 20 handlers were offline. The rendered Handler page showed `HT9046MX-115` roughly 341 hours stale. The UI still displays old health states and active alarms, so operators can mistake last-known values for live conditions.

### QA-11 — High — Maintenance completion can hide an active fault

Completing a work order or submitting a module service log changes the module to `NORMAL` without recomputing from telemetry. For external sources, it may stay normal until a new source row creates a different `source_id`.

### QA-12 — Medium — Analytics silently compares unlike modules

When a selected module code does not exist on a handler, Analytics silently falls back to that handler's “worst” module. Selecting a compressor module can therefore compare compressor data with a Vacuum Pump. “Worst module per device” also mixes equipment types and units. The summary status is the handler status, not the selected module status.

### QA-13 — Medium — Time and unit semantics are ambiguous

Source timestamps have timezone information stripped, backend age calculations use local naive time, and browsers parse/display those values in their own locale. Most chart x-axes show only time-of-day, so multi-day history repeats labels without dates. Several compressor pressure channels have no declared unit, but `Hp_1st` is exposed as `pressure_kpa`.

### QA-14 — Medium — Alert handling is not an operational workflow

There is no per-alert acknowledge, assign, resolve, or audit state. Badge acknowledgement is browser-local storage, while the admin action permanently deletes all alert records. Current metadata contained 215 alerts during QA.

### QA-15 — Medium — External history has no durable fallback

Raw readings and dynamic metrics are queried directly from the remote source and are not cached locally. If `10.195.17.73` is unavailable, historical charts and exports disappear even though local diagnostic/alert metadata remains.

## API, reliability, and performance

### QA-16 — High — Invalid limits cause server errors

All tested negative limits returned HTTP 500:

- `/api/alerts?limit=-1`
- `/api/work-orders?limit=-1`
- `/api/maintenance-logs?limit=-1`
- `/api/devices/17/history?limit=-1`
- `/api/devices/17/metrics?limit=-1`

Request bodies are untyped dictionaries with inconsistent manual validation, so invalid enum values, IDs, dates, oversized text, `NaN`, and foreign-key combinations can reach MySQL and become 500 responses.

### QA-17 — Medium — Excessive refresh and connection churn

Every WebSocket message schedules a full refresh of five or six endpoints, and the browser repeats the same full refresh every five seconds. Backend calls open fresh MySQL connections rather than using a pool. The port snapshot showed many local and remote MySQL connections in `TIME_WAIT`.

### QA-18 — Medium — Long-running process resilience is weak

- The metadata DB connector has no connect/read/write timeout.
- Startup catches database initialization failure and continues serving; the public status route still returns HTTP 200 when disconnected.
- The poller retains every processed `source_id` in an unbounded in-memory set.
- Compressor `source_id` omits the source row ID, so equal machine/timestamp/module rows collide.
- The supplied launcher is not a Windows service and has no automatic restart, log rotation, backup, or restore workflow.

### QA-19 — Low — Resource semantics are inconsistent

Deleting a missing device/module reports success instead of 404. `machine_code` is indexed but not unique, even though grouping relies on it as a handler identity. Most list routes provide only a hard cap, not pagination metadata.

## Frontend, UX, and accessibility

### QA-20 — Medium — Responsive layout has clipping/discoverability problems

The real 390 px login render clips the form on the right. At the smallest authenticated render, the horizontal navigation hides later items with an invisible scrollbar. Wide data tables depend on horizontal scrolling. See the screenshots below.

### QA-21 — Medium — Charts and state controls are not accessible

ECharts renders into an unlabeled canvas container with no text alternative. Active navigation/filter/module tabs expose only CSS classes, not `aria-current`, `aria-selected`, or `aria-pressed`. Toasts have no live region, the search field has no accessible label, and animations do not honor `prefers-reduced-motion`.

### QA-22 — Low — Visual and content consistency needs cleanup

User-facing operations mix English and Thai, chart units are inconsistent, and stale diagnostic status is not always labeled as last-known outside Handler cards. `styles.css` contains several repeated/overriding definitions for the same core grids and cards, increasing visual-regression risk.

### QA-23 — Medium — Static asset delivery is inefficient

The ECharts chunk is 553,377 bytes. A request advertising gzip/Brotli received the full uncompressed file and no `Cache-Control`; the server also reveals `uvicorn`.

## Dedicated frontend UX/UI audit

The visual direction is strong for an industrial operations product: the dark control-room theme is consistent, the Handler card hierarchy is easy to scan, status chips include text as well as color, buttons have visible keyboard focus, and Handler cards can be opened from the keyboard. The intended hierarchy now works: one Handler card opens its available source modules, and Compressor opens M1–M8 inside the same detail view.

The following issues keep the interface from being safe and efficient for real maintenance decisions.

### UX-01 — Critical — Stale readings look like current operating data

The detail view can say `No Signal` while still presenting large KPI values, health score, `Repair now`, gauges, and charts with the visual treatment of live data. Overview also presents active-alert and condition counts without a dominant fleet-level "last known / as of" warning. With most handlers roughly 14 days stale during QA, an operator can reasonably mistake historical values for current plant conditions.

Add an explicit data-freshness banner, timestamp every snapshot/chart, dim or lock stale values, and separate **connection state** from **last-known equipment condition** everywhere. Any recommendation based on stale data should be labeled accordingly.

### UX-02 — High — Several charts are visually polished but analytically misleading

- The Vacuum Pump overview puts temperature (°C), current (A), and vibration (g) on one generic `Sensor` y-axis. These quantities cannot share a meaningful numerical scale.
- `connectNulls: true` draws continuous lines across missing samples and outages, concealing telemetry gaps.
- Compressor pressure charts use `source units`, while HP/LP KPI cards have no unit. Valve also has no unit or percent indication.
- Time labels use only the local time of day. They omit date, timezone, selected date range, sample count, and the actual start/end timestamps.
- The charts have no warning/critical reference lines, acceptable operating bands, outage markers, or alert annotations, even though those are the main decision context.
- The initial zoom silently displays only the last 35% of returned data. The UI does not state that the earlier 65% is hidden.

Use one unit per axis, split incompatible signals into small multiples, preserve gaps, show source units explicitly, display the date range/timezone/sample count, and overlay thresholds or operating bands only after the equipment-specific limits are validated.

### UX-03 — High — Loading and empty states can briefly report false fleet health

The primary application state starts with empty arrays/null summary and has no page-level loading skeleton. During a real navigation test, Overview briefly rendered zeros before the API data arrived. A failed or slow request can therefore resemble a healthy empty fleet rather than an unknown state.

Use explicit `loading`, `loaded`, `empty`, `stale`, and `error` states. Never render a zero KPI until the request has completed successfully and the value is genuinely zero.

### UX-04 — Medium — Status summaries combine overlapping dimensions

Overview shows `Need Attention`, `No Signal`, warning/repair distribution, and offline totals together, but the same Handler can contribute to more than one of these figures. The status distribution visually implies mutually exclusive categories even though `Offline` is connectivity and `Repair now` is a last-known condition. `0 ESP32 online` also implies a direct ESP32 connection even though the application reads MySQL sources.

Separate connectivity from condition into distinct visual groups, explain denominators and overlap, and rename source-specific labels to match the actual MySQL ingestion architecture.

### UX-05 — Medium — Detail navigation loses application context

The Handler detail is a full-screen fixed overlay. It hides the global navigation and provides only `Back` as an exit. The active Handler, source, module, filters, and scroll position are component state rather than URL state, so the view cannot be bookmarked, shared, restored after refresh, or opened in a new tab. On a long detail page, the source/M1–M8 selectors are not sticky.

Give details a route such as `/handlers/:handler/:source/:module`, preserve the originating filter/scroll state, retain a compact global breadcrumb, and keep the module selector visible while scrolling.

### UX-06 — Medium — Mobile navigation and login are not reliable

At a real 390 px viewport, the login panel clips on the right. On the smallest authenticated layout available in the test browser, global navigation becomes a horizontal strip whose scrollbar is deliberately hidden; later destinations such as Database, Analytics, and Admin are not discoverable without an unprompted swipe. Wide tables use fixed minimum widths and horizontal scrolling.

Remove the login overflow, replace hidden horizontal navigation with a visible menu/overflow control, and provide responsive table alternatives such as priority columns, stacked rows, or an explicit column chooser.

### UX-07 — Medium — Operational scanning and terminology need refinement

- Long Handler names wrap awkwardly at the identifier boundary.
- Technical source IDs such as `compressor:115` are more prominent than location/context useful to a technician.
- Handler-level and module-level `Repair now` labels repeat without explaining aggregation.
- Vacuum and Compressor naming is not fully consistent across cards and details.
- Ages such as `341h` are harder to scan than `14d 5h` plus an exact timestamp.
- The condition score presents a precise number even though the UI identifies the current model as `MODEL_PENDING / ai-placeholder-v0`.

Prioritize machine/location, use consistent equipment vocabulary, explain how Handler health aggregates module health, format long ages in days, and avoid numerical model authority until the model is validated.

### UX-08 — Medium — Accessibility is incomplete beyond basic keyboard focus

Positive: status is not communicated by color alone, buttons have a visible focus treatment, Handler cards support Enter/Space, theme buttons expose `aria-pressed`, and the icon-only alert button has an accessible label.

Remaining problems:

- Chart canvases have no accessible name, summary, or tabular alternative.
- Navigation, Handler filters, source tabs, and M1–M8 tabs do not expose their selected state with `aria-current`, `aria-pressed`, or tab semantics.
- Toasts are not announced through a live region, and Handler search has no programmatic label.
- Chart pan/zoom is pointer-dependent; `Scroll to zoom` conflicts with ordinary page scrolling and has no keyboard controls or Reset button.
- There is no skip link and no `prefers-reduced-motion` treatment.
- Global `body { zoom: 0.8 }` makes an already dense 13 px interface smaller and can produce inconsistent browser zoom/accessibility behavior.

### UX-09 — Medium — Forms and destructive workflows are inconsistent

Admin and maintenance workflows rely heavily on transient toasts rather than inline validation and field-specific recovery guidance. Destructive actions use native `window.confirm` dialogs, with a mix of Thai and English copy. The administration page combines several high-impact workflows in one dense surface, increasing selection and submission errors.

Use consistent application dialogs that name the exact target and consequence, inline validation attached to fields, persistent error summaries, and separate high-risk administration tasks into focused sections.

### UX-10 — Low — CSS architecture makes visual regressions likely

Core selectors such as `.handler-grid`, `.handler-card`, `.detail-grid`, `.detail-view`, and `.chart` are defined repeatedly across the 3,000+ line stylesheet. Later overrides make the final responsive behavior difficult to predict and contributed to contradictory spacing/scaling rules.

Consolidate component styles, define a small spacing/type/color token system, and add screenshot regression tests at desktop, tablet, and 390 px mobile widths.

### Frontend UX/UI repair order

1. Make freshness unmistakable and prevent stale/unknown data from appearing live or zero.
2. Correct chart units, axes, gaps, ranges, timezone/date labeling, and equipment-specific thresholds.
3. Fix 390 px login overflow and replace the hidden-scroll mobile navigation.
4. Add routable Handler/source/module details with persistent module navigation.
5. Complete accessibility semantics and accessible chart summaries.
6. Refine operational labels, hierarchy, dialogs, and form recovery.
7. Consolidate CSS and add visual, responsive, keyboard, and accessibility regression tests.

## Tests, documentation, and delivery

### QA-24 — High — Automated coverage is insufficient

Only two backend mapping unit tests exist. Both pass, and Python compilation passes, but there are no API, authentication/authorization, database-integration, frontend, chart, E2E, accessibility, responsive, load, migration, backup/restore, or failure-mode tests. No lint/type-check scripts exist. `pytest` and `pip-audit` are not installed in the project environment, so Python dependency CVEs were not automatically assessed.

### QA-25 — Medium — Deployment documentation is incomplete/broken

`README.md` tells operators to copy `.env.example`, but that file does not exist on disk. The README also documents `devices_id` while this server is configured for `device_id`, contains a corrupted `1â€“8` string, and asks for an approved service/process manager that the local launcher does not provide. This working copy has no `.git` directory, so it has no local change history or easy rollback.

## Checks that passed

- Production frontend build passed: 2,130 modules transformed.
- Both existing backend mapping tests passed.
- Python source compilation passed.
- Normal authenticated API reads returned 200; missing/invalid tokens returned 401; user access to admin-only status/users returned 403.
- Handler hierarchy rendered as intended: Handler card → Compressor/Vacuum source → Compressor M1–M8.
- The desktop Overview, Handler grid, and Module detail render without visible overlap or broken components.
- MySQL listens only on `127.0.0.1:3306`.
- The app listens on port 5001; ports 8000 and 5173 are closed.
- Metadata checks found no duplicate device UID, duplicate machine code, or orphan module/diagnostic rows at the time tested.

## Visual evidence

- [Desktop Overview](.tmp/qa-dashboard-desktop.png)
- [Handler Overview](.tmp/qa-handlers-desktop.png)
- [Compressor Module Detail](.tmp/qa-module-detail-desktop.png)
- [390 px Login](.tmp/qa-login-mobile.png)
- [Small-screen Dashboard](.tmp/qa-dashboard-mobile.png)

## Recommended repair order

1. Close the forged-token path: strong non-empty secret, rotation, account-state checks, TLS/reverse proxy, CORS and security headers.
2. Stop using dashboard health/alerts for decisions until compressor scaling, units, equipment-specific thresholds, and history-based diagnostics are corrected and back-tested.
3. Fix authorization and state transitions for maintenance/work orders; add server-side alert lifecycle.
4. Add typed request/query validation and regression tests for every confirmed failure.
5. Reduce refresh/DB connection churn and add readiness, timeouts, service supervision, logs, backups, and a local history fallback.
6. Repair mobile/accessibility issues, package versions, `.env.example`, and deployment documentation.
