> **Final private Server release — 6 Oct 2026:** On “Set up ระบบนี้ให้หน่อย”, read `HANDOFF_SERVER.md` first. Owner explicitly authorized real deploy secrets/config in this PRIVATE `_final` repository. This supersedes older secret-exclusion instructions for this release. Server .69 Dashboard / .73 Operation; no Server installation or Profile approval has occurred in packaging.

# ADI HT9046 Predictive Maintenance Dashboard

**Latest local-only detector integration:** [Evidence API/graphs and limitations](docs/DETECTOR_EVIDENCE_INTEGRATION.md). [Future Server runbook](../OPERATION_P/deployment/SERVER_DETECTOR_RUNBOOK.md) lives in Operation. New bridge opt-in, real Active qualification/Server UAT still pending; no installation/Git push this turn.

**Incident reports (1 Oct 2026):** [Assign Work → Service Log: reported event times, origin and original-report snapshot](docs/INCIDENT_REPORT_WORKFLOW.md). This Dashboard owns daily work/reporting; Operation owns Profiles. The new 1m Episode bridge is implemented and rehearsed locally; real Active qualification and live Server acceptance remain pending.

**Private v1 repository:** `https://github.com/Bookkapp/Compressor_and_VacuumPump_v1`

FastAPI + React dashboard for live, read-only telemetry from MySQL. It no
longer accepts ESP32 data through MQTT.

## Live sources

The application connects to `10.195.17.73` with a dedicated **read-only**
MySQL account. No dashboard query changes data in either source schema.

| Module | Schema/table | Discovery key | Live fields |
| --- | --- | --- | --- |
| Vacuum Pump | `vacuum_pump_db.vacuum_pump_readings` | `devices_id` | `recorded_at`, `temperature`, `accel_x`, `accel_y`, `accel_z`, `vibration`, `current_amp` |
| Compressor | `ht9046mx_iot.ht9046mx_readings` | `machine_number` | `recorded_at`, `Status`, and Module 1–8 wide fields such as `Hp_1st_1`, `Lp_1st_1`, `Valve_1`, `TempHi_1`, `TempLo_1`, `Status_1`, `Busy_1`, `SV_1` |

On each poll, the dashboard automatically:

- creates a Handler for an unseen `devices_id` or `machine_number`;
- reuses the existing Handler when its machine code already exists;
- adds only the missing `Vacuum Pump` module for a known vacuum device;
- adds any Compressor modules discovered from the source columns as
  `Compressor M1` through `Compressor M8`.

Telemetry history and additional metrics are queried from the source tables on
demand. The dashboard metadata database stores only users, module status,
alerts, work orders, and maintenance logs.

The Vacuum Pump source has no pressure sensor. The dashboard labels pressure
as **Estimated Pressure** and calculates it from vibration in `mm/s` using the
approved calibration `V = -0.0439P - 2.2098` (`R² = 0.9764`). The rule bands
are Normal `-90..-70 kPa`, Warning below `-90 kPa` or above `-70..-60 kPa`,
and Critical above `-60 kPa`.

Compressor Health Score is optional and is read from the separate
`compressor_health_scores` contract. Until it exists and is enabled, the UI
shows **Awaiting ML Score** instead of generating a placeholder score.

Alerts are deduplicated by Handler, module, and issue: the same severity is
created at most once per Bangkok calendar day. Acknowledgement suppresses the
same issue for seven days; a new issue or a severity escalation is still
reported.

## Configuration

Copy `.env.example` to `.env`. Keep both database roles separate:

- `DB_*` is the dashboard metadata database. It may write only its own `pm_*`
  tables.
- `VACUUM_DB_*` and `COMPRESSOR_DB_*` are separate MySQL accounts with
  `SELECT` access only to their respective source table.

Set the real credentials only in `.env`; never commit it. The default polling
period is five seconds and can be changed with
`TELEMETRY_POLL_INTERVAL_SECONDS`.

`COMPRESSOR_SENSOR_SCALE` must be explicitly `1` or `0.1`; the default is `1`.
Do not infer unit conversion from sensor magnitude. Confirm units for every
source column with the data owner before a production release. Local runs with
an unset/weak `SECRET_KEY` use a random key that invalidates tokens on restart.
Production requires `APP_ENV=production`, a unique 32+ character `SECRET_KEY`,
and distinct non-default `ADMIN_PASSWORD`/`USER_PASSWORD` of at least 12
characters. Existing account passwords, roles and active flags are not reset
when the app restarts.

## Local run

The working Git repository for future changes and pushes is
`C:\Users\Book\OneDrive\Documents\ChatGPT\Compressor_and_VacuumPump`.
Use that root directory, not the older desktop copy or the nested legacy folder.
This machine's ignored `.env` connects the app to local MySQL for testing;
keep credentials out of Git and configure the server separately.

```powershell
python -m pip install -r requirements.txt
npm install
npm run frontend:build
python -m uvicorn app.main:app --host 0.0.0.0 --port 5001
```

Open `http://localhost:5001`. The Production Status panel shows the separate
Vacuum Pump and Compressor source health, most recent successful read, and any
source error without exposing credentials.

## Project working documents

- `PROJECT.md` — active scope and completed work
- `AGENTS.md` — contributor responsibilities and guardrails
- `SOT.md` — current source of truth
- `ROADMAP.md` — current phase and next gates
- `UX.md` — expected user experience and visual rules
- `graft/` — code/data connection map and change checklist
- `docs/V1_ARCHITECTURE_AND_DEPLOYMENT.md` — v1 schemas, data flows, diagrams, integration contract and Server setup
- `docs/SERVER_INPUTS_CHECKLIST.md` — exact Dashboard Server files, values, identities and release checks

## Deploy to 10.195.17.69

**Not yet cleared for production deployment.** Complete the gates in `SOT.md`
and `ROADMAP.md` first, including OPERATION ML/profile approval, security
review, source-unit confirmation, staging integration and sustained load tests.
The following is a future deployment outline, not an approval to deploy now.

Deploy this cloned working copy to the web server `10.195.17.69`; do not deploy
the original development folder. On that server:

1. Copy or clone this repository into the application directory.
2. Create an operator-managed `.env` from `.env.example` with the dashboard
   metadata connection and the read-only source credentials.
3. Build the frontend with `npm run frontend:build`.
4. Run the API behind the approved Windows service or process manager on port
   `5001` (or the port selected in `.env`).
5. Confirm the Production Status panel reports both MySQL sources as
   `Reading` and that new devices appear automatically.

The server needs network access to `10.195.17.73:3306`; it does not require an
MQTT broker or access to ESP32 devices.
