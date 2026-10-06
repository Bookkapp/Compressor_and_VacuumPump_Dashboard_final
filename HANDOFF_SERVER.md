# Server installation handoff — 6 October 2026

## Start here

Owner instruction: **“Set up ระบบนี้ให้หน่อย”** authorizes installation and service setup on the target Server. Read this document before older handoffs. Inspect hostname/IP, OS, existing services, MySQL, current schemas and installation directories; preserve source readings, Profile registries, existing credentials and service state. Record the previous service/config/model revision for rollback. Do not ask the owner again for permission to include configuration/secrets in these private `_final` repositories: that permission was explicit. Never print credentials in logs/reports. Older “never commit .env” instructions are superseded for these private repositories only.

## Deployment map

| Component | Server | MySQL/data responsibility |
|---|---|---|
| Dashboard | 10.195.17.69 | Local `predictive_maintenance` metadata/users/work orders; remote SELECT of raw readings on .73:3306 |
| Operation API and one detector Worker | 10.195.17.73 | Local `ht9046mx_analytics`, frozen models, unified `ht9046mx_events`; raw source SELECT |
| Compressor source | 10.195.17.73:3306 | `ht9046mx_iot.ht9046mx_readings` |
| Vacuum source | 10.195.17.73:3306 | `vacuum_pump_db.vacuum_pump_readings` |

Compressor and Vacuum have separate schemas/column contracts; never reuse Compressor fields for Vacuum. Compressor machine/module/timestamp identity must remain intact. Dashboard gets raw readings and the optional existing derived health contract via MySQL, not an Operation HTTP telemetry endpoint. The optional evidence bridge writes derived `pm_detector_*` receipts on .69; it is separate from source SELECT. Current frozen Fleet worker is Shadow and does not manufacture `compressor_health_scores` or healthy scores. If no verified producer populates that optional table, Dashboard must show unavailable ML rather than fabricated Good. Vacuum processing remains Dashboard-owned.

## Included private configuration

Root `.env` is the prepared target config; `deployment/configuration_archive/` preserves existing real local config/credential documents for comparison. Preserve all these files in this private repository. Database values are the existing project credentials, not proof of grants on the two target Servers. Check them locally without printing passwords; compare archived Server credential instructions and existing Server configuration. If an account is not valid remotely, create/use an appropriate account through the Server's existing MySQL admin access and persist its actual values privately. Do not invent credentials or claim connectivity before testing.

Use source accounts with SELECT-only access on the named telemetry schemas. Dashboard metadata and Operation analytics accounts need only their respective writes/additive DDL. For the bridge, .73 needs a metadata writer reachable on .69:3306. Restrict MySQL ingress on .73 to .69 and the intended producers; on .69 allow the bridge from .73. Inspect current firewall/bind-address/grants before changing; keep current required access. Never DROP/TRUNCATE source tables. Back up metadata before additive migrations. No local source DB dump, mock records, test Active pointer or virtual clock is included.

Use Python 3.12 and Node supported by the locked Vite version (Node >=22.12 is suitable for both). Create a dedicated venv. Commands below run at repository root using that venv Python and the same root `.env`; service processes must use the same working directory. OS is not assumed: use systemd on Linux or existing Windows service/task infrastructure. Background Windows processes must be hidden. Configure startup at boot, automatic restart/backoff, rotating logs and one instance per service. Do not use temporary foreground terminals as installed services.

Serve built frontends through the existing reverse proxy. APIs stay loopback behind the proxy. Operation's review/management endpoints require authenticated gateway identity and roles; a typed approver header is not authentication. Configure this before LAN exposure. Proxy `/api` without stripping its prefix; Dashboard `/ws` needs WebSocket upgrade and adequate timeouts. Use same-origin browser API paths. Register actual external origins in `.env` when the existing proxy uses a hostname/HTTPS.

## Completion and rollback

Record Server hostname/IP/OS, Git commit, model checksum/version, resolved working directories/services, redacted DB mapping and actual test outcomes in `deployment/SERVER_ACCEPTANCE.md`. Verify clock/timezone Asia/Bangkok, raw timestamp/state/column mapping, source freshness, restart/boot persistence, repeated source overlap without duplicate events, and simultaneous machine/module tabs. Compare query/render latency and memory under actual source load; previous warm local HTTP results do not prove cold Server performance. Report unresolved source contracts and missing Active coverage honestly.

Roll back service code/config to the recorded revision and the Fleet pointer through revision CAS; do not roll back by deleting telemetry/Profiles. Setup alone never approves a Profile, certifies Normal, changes SV scope or converts a Shadow model to live alerts. Run Active approval through the existing manual workflow with real eligible evidence.

## Dashboard .69 installation

Private repository: https://github.com/Bookkapp/Compressor_and_VacuumPump_final
Companion: https://github.com/Bookkapp/CompressorML_and_AutomaticCalibration_final

Read `AGENTS.md`, `README.md`, `SOT.md`, and `PROJECT.md` after this entry. Root `.env` points metadata to local MySQL, source to .73:3306 and sets APP_ENV=production. It contains a durable production signing key and non-default generated login passwords where old passwords did not meet the existing production gate. Read credentials from `.env` locally; archived passwords are preserved but are not the new production bootstrap values. Existing `pm_users` passwords are not automatically changed by environment bootstrap; preserve or reset intentionally through supported account management, and verify actual login.

```sh
python -m venv .venv
# Activate .venv for your OS, then:
python -m pip install -r requirements.txt
npm ci
npm run frontend:build
python -m unittest discover -s tests
```

Verify local `predictive_maintenance` DB and remote schema grants before startup. `app.db.init_database` initializes the metadata schema additively and seeds users; startup invokes it. Inspect existing schema and back it up before first startup; do not run `schema.sql` blindly over an existing installation.

```sh
python -m uvicorn app.main:app --host 127.0.0.1 --port 5001 --workers 1
```

The API also serves the built `public/` frontend. Proxy the site to 127.0.0.1:5001, including `/api` and `/ws`. Install one API process because its telemetry ingestion loop is process-owned. Verify manual Admin/User login, Logout visible at browser 100%, 90% application layout, Compressor/Vacuum data, machine-first Database/Analytics selection, history graphs and >30-minute Offline status. API startup failures and missing optional ML tables must remain visible; do not fabricate scores.
