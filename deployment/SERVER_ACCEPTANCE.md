# Dashboard Server acceptance — 6 October 2026

## Operation grants verified from .69 — 8 October 2026, 09:48 Bangkok

After the owner reported `.73` completing restricted reader grants, authenticated SELECT from the actual Dashboard account succeeded on all three analytics feed/sequence/identity tables. Each table currently contains zero rows. The prior 1044 blocker is resolved. Receiver observations ten seconds apart both reported enabled=true, connected=true, error_type=null, last_seq=0, backlog=0, with advancing successful poll timestamps; both raw telemetry sources also reported successful reads.

Metadata backup succeeded (7,843,691 bytes), then the installed API was restarted through its supervisor. Admin login, health and frontend returned HTTP 200; receiver reconnected and retained its single cursor at sequence 0. Before/after counts were unchanged: Operation identities 0, receipts 0 and existing Alerts 1. No extra delivery/Alert was observed during this empty-feed restart. Producer identity preservation, nonzero cursor advancement, payload ingestion and replay deduplication remain unverified until real eligible exports populate the producer tables. No source/sequence/Profile edits or fabricated evidence were used.

## GitHub update deployed — 8 October 2026

Owner requested pulling GitHub and updating the installed system. Clean tracked checkout fast-forwarded from `eb3b0972dd0c2d911942b15ee16aa2f63e26ab75` to `5bfa10a` (one-way Operation receiver/chart changes and Pending/Fleet trend cleanup). Existing `.env` values were compared and preserved; only seven new Operation settings were added by the release. Private pre-update config and built frontend are preserved in ignored `deployment/runtime/rollback-20261008/`. Metadata backups before pull and restart succeeded (approximately 7.5 MB). Existing supervisor, proxy, local MySQL, source grants and stored login accounts were retained.

Installed dependencies, 79 unittest tests / 91 pytest tests / 19 subtests, 13 Node tests and production frontend build all passed. Existing dependency audit/chunk warnings remain. API startup completed at 08:55:05 Bangkok; Admin login, frontend, device API and hourly Fleet trend API returned HTTP 200. Both actual raw-source reads succeeded without source errors. New Operation/hourly/status metadata tables were inspected and all use InnoDB. No telemetry or Profile/model data was altered.

**Outstanding dependency:** the configured Operation reader cannot access `.73` `ht9046mx_analytics` (MySQL 1044). Operation pull is enabled but unavailable, reported by the installed receiver while retaining its checkpoint. No valid feed result or cursor advancement is claimed; fresh Compressor modules without eligible evidence remain Pending. The `.73` operator/DBA must complete the companion export migrations and restricted SELECT grants on `ht9046mx_dashboard_feed`, `ht9046mx_dashboard_sequence` and `ht9046mx_dashboard_identity`, using the actual Dashboard reader from private `.env`. Operation Server access was not available in this session; no remote grant, firewall change or Worker restart was performed. Full instructions: ONE_WAY_MYSQL_UPDATE_20261007.md. Browser/LAN/reboot acceptance remains as previously documented.

## Compressor Handler signal policy — 18:35 Bangkok

Owner requested Online for Compressor readings through 30 minutes, removing earlier No signal behavior. Updated shared connectivity policy and source classification: real canonical HT9046MX Handler IDs now use stored Compressor module membership in both Handler list and summary, including shared Handlers. Pure Vacuum cadence and diagnostic evidence are unchanged. Missing/invalid time remains Offline; exactly 30 minutes remains Online, over 30 minutes Offline.

Final verification: 71 unittest tests / 83 pytest tests / 19 subtests passed; production frontend build passed with the existing chunk warning. Metadata backup succeeded and installed API was restarted. Authenticated deployed checks found 20 Compressor Handlers; all six with last readings within 30 minutes returned ONLINE, all older ones OFFLINE. Summary reported ONLINE 6 / NO_SIGNAL 0 / OFFLINE 15 across all Handlers, and health returned HTTP 200. No source reading or Profile was changed. Browser rendering was not separately verified.

## Dashboard admin login repair — 18:02 Bangkok

Owner reported invalid Dashboard login after editing bootstrap credentials. Verified the active `ADIadmin` account; backed up metadata, then updated only its password hash using the application's existing PBKDF2 helper to match the private saved `ADMIN_PASSWORD`. Actual login through nginx returned HTTP 200. Account identity/role/active state and the maintenance user's password were preserved. No restart or source write was required; no password/token value is recorded here.

## Owner-authorized metadata password reset — 17:58 Bangkok

Owner changed the private `.env` and explicitly requested an account reset/restart. Corrected the nonexistent configured `predictive_app` username to the installed `pm_dashboard` account; reset only that account's password to the owner's saved metadata password, preserving its existing privileges. Verified-admin metadata backup succeeded before the account change, and another backup succeeded before API restart. Preserved the prior `.env` privately in the configuration archive. API startup completed at 17:58:42; backend health and frontend both returned HTTP 200, and the corrected saved metadata account connected successfully. No source account/data or Dashboard login password was reset; no password values are recorded here.

Status: **portable Dashboard installed and running; both source accounts verified**.
This is the user-approved alternative to an elevated Windows service installation.
Full deployment acceptance is pending remote LAN/browser checks, boot persistence and sustained load.

## Installed on .69

- Host: `th1pmappdev1w`, `10.195.17.69`, Windows Server 2022 Standard, build `10.0.20348`.
- Clock/timezone: Windows `SE Asia Standard Time`; app `Asia/Bangkok`; local MySQL/API timestamps agree. No clock or timezone change was needed.
- Working directory: `C:\Compressor_and_VacuumPump_final-main` for every Dashboard process.
- Checkout is an extracted archive with no `.git`. Packaging manifest source head is `5ca9b227f2990278bf59a5d10dbe162ef7af43e1`, **including uncommitted packaging changes**. This is not a verified final repository HEAD.
- Python `3.12.14`, dedicated `.venv`; Node `24.19.0`; locked npm install and Vite production build.
- Official MySQL portable `8.4.11`; downloaded ZIP MD5 matches published `2e833921898a9a030ea6bfe81bd811bc`.
- Official nginx portable `1.30.5`; configuration syntax checked.
- No pre-existing MySQL, Dashboard, reverse proxy listener or corresponding service/task was found. Existing `C:\HT9046MX` installation/configuration was preserved.
- MySQL is loopback-only `127.0.0.1:3306`; API loopback-only `127.0.0.1:5001`, one API worker; nginx listens on port 80 and preserves `/api` and `/ws` with WebSocket upgrade.
- URL: `http://10.195.17.69`. HTTP and health were checked from .69 using loopback and the LAN IP. **Connectivity from another machine, firewall ingress and TLS have not been verified/configured.**

## Process lifecycle and private configuration

- User task `ADI-PM-Dashboard-Portable` runs the hidden Python supervisor at login for `ANALOG\SSricha2`, without elevation. Task is Running; duplicate supervisors are prevented by a filesystem lock.
- Supervisor restarts each owned process with 2–60 second backoff and rotates captured logs at 5 MB, four retained copies per component. One nginx master/worker and one MySQL launcher/server pair are normal Windows process arrangements.
- User task `ADI-PM-Metadata-Backup` runs a metadata-only consistent dump daily at 03:00 Bangkok time when the user session is available; missed starts are configured to run when available. An immediate scheduled backup was also executed.
- Runtime, data, backups and admin credential files are in ignored `deployment/runtime/`, with inherited folder access replaced by current-user, SYSTEM and Administrators access. No raw source dump is included.
- Original target `.env` is preserved privately in `deployment/configuration_archive/.env.before-portable-20261006`; earlier archives remain intact. No credential value is recorded here.
- Dedicated local `pm_dashboard` account has SELECT/INSERT/UPDATE/DELETE and additive schema privileges only on `predictive_maintenance.*`; the generated local MySQL admin credential is stored privately inside runtime. Application signing/bootstrap secrets remain the prepared production values.
- An `AtStartup` task using noninteractive S4U was attempted and rejected by Windows. **No boot-before-login persistence, logout survival, reboot test or Windows service is claimed.** A logged-in/disconnected session is required for this user-task deployment.

## Source truth

- Compressor: remote `10.195.17.73:3306`, `ht9046mx_iot.ht9046mx_readings`. The original packaged and archived credentials failed authentication. The existing `C:\HT9046MX` runtime account was verified to have **SELECT only on this exact table**, then reused privately for the Dashboard. Its other grants are only USAGE.
- Compressor fields include raw machine number, recorded time, Status, and M1–M8 HP/LP/Valve/temperature/Busy/SV fields. Actual source reads discovered **20 machines, 160 modules**. Raw source machine IDs are retained; module-specific histories return their mapped data.
- Source sample timestamps observed during setup were 6 October 2026 around 17:15–17:20 Bangkok time. Successful poll time is distinct from raw sample freshness. Source units/scale remain the supplied explicit configuration; owner unit confirmation is still pending.
- Vacuum: owner supplied the correct username `vacuum_pump_db_reader`; its existing prepared password authenticates successfully and SHOW GRANTS confirms SELECT only on `vacuum_pump_db.vacuum_pump_readings`. The actual identity column is `device_id`, so `VACUUM_DEVICE_COLUMN=device_id` replaces the packaged default `devices_id`. Actual columns include temperature/current/vibration/accel X/Y/Z; no measured pressure column exists. Latest real source timestamp observed was 6 October 2026 17:33:39 Bangkok. After restart both sources report successful reads with no source errors. Two Vacuum modules are discovered, with one sharing an existing machine Handler; total 21 Handlers / 162 modules. Vacuum pressure remains Estimated Pressure.
- Optional Compressor ML lookup is disabled because the verified account only reads raw telemetry and no verified Health Score producer/table access was established. Scores remain null / Awaiting ML Score; no replacement score is generated.
- Operation `.73` API/worker/Profiles/models were not installed or altered. Integrated WinRM inspection of `.73` was unavailable. No model checksum, Active coverage, Shadow-to-live conversion or event-overlap acceptance is claimed for Operation.

## Actual checks

- `python -m unittest discover -s tests`: **70 passed**.
- Final `python -m pytest -q`: **82 passed**, 19 subtests passed; one existing Starlette/AnyIO deprecation warning.
- `npm ci` and `npm run frontend:build`: passed. Existing large ECharts chunk warning remains; npm reported six dependency audit findings. No broad dependency upgrades were performed.
- Windows clean-install issues fixed by adding `tzdata` to runtime requirements and `httpx`/`pytest` to separate development requirements.
- The historical Vacuum fixture previously depended on the loaded `.env` identity column. It now isolates and verifies both `devices_id` and actual-server `device_id`, including the unchanged Estimated Pressure calculation and null current value. Both test suites were rerun successfully with the final Server configuration.
- Actual Admin and User login through nginx: HTTP 200; authenticated metadata/source status: connected; WebSocket `/ws` negotiated `adi-v1` through nginx.
- Eight concurrent history requests across four machines/two modules each, four in flight: all HTTP 200 with 200 real samples. Initial run 0.61–1.31 s; post-restart run 0.13–0.24 s. These short runs do not prove sustained production performance or browser rendering.
- Metadata-only backup succeeded before restart (44,394 bytes in the first dump); no pre-existing metadata database was present before initialization.
- Controlled API stop at 17:30:13: supervisor relaunched at 17:30:15, API startup completed at 17:30:18. Both logins, authenticated reads and WebSocket passed again afterward. Configured origins were applied on restart.
- Repeated ingestion/restart: 20 devices/160 modules, zero duplicate machine/module identities; zero alerts and work orders in this newly initialized database. This is not proof of Operation event deduplication.
- Short observed working sets: API around 67 MB, MySQL server around 394 MB, nginx processes around 9 MB each; no sustained memory/load claim.
- Browser QA was blocked: automatic approval review rejected the hidden headless Edge launch with `blocked by policy`. Logout visibility, 90% layout, graphs rendered in browser, mobile and simultaneous actual browser tabs remain unverified this installation.
- Latest machine-readable API evidence: `deployment/runtime/acceptance-api.json` (no passwords/tokens).
- Final combined-source run: ten history requests, four in flight, eight Compressor/two Vacuum modules, all HTTP 200 with 200 real samples each; 0.18–0.35 s in this short run. Both login roles and proxy WebSocket passed again after applying the Vacuum account/mapping. The earlier Vacuum failures above were resolved without changing source grants or data.
- Current Windows policy rejects unsigned `.ps1` script files. Use the Python restart entrypoint below; it makes the same guarded process stop through inline PowerShell without changing execution policy. Installed user tasks do not depend on unsigned PowerShell scripts.
- Actual `history-page` and `history-chart` checks returned HTTP 200 / 100 real samples for each source. Compressor fields are HP/LP/temperatures/valve/busy/Status/SV; Vacuum fields are temperature/Estimated Pressure/current/vibration/accel. Their identity/source responses remain distinct.

## Remaining work and operation

1. Keep the verified separate SELECT-only source accounts and actual Vacuum `device_id` mapping. For later private config changes, run the Python restart entrypoint below after comparing/backing up the configuration.
2. Check `http://10.195.17.69` from a different LAN computer. If ingress is blocked, the Server administrator must apply the intended scoped firewall rule. Nothing changed the current firewall.
3. Verify real browser login/logout, source-specific data/empty states, charts and concurrent tabs; confirm source units and run sustained source-load/reboot acceptance.
4. If boot-before-login is required, an administrator must install a proper service or authorized noninteractive boot task; current login task is explicitly a limited fallback.
5. Set backup retention/off-host copies according to Operations policy. Current backups are retained locally without automatic deletion.

Maintenance commands from repository root:

```powershell
.venv\Scripts\python.exe deployment\check_portable.py
.venv\Scripts\python.exe deployment\backup_metadata.py
.venv\Scripts\python.exe deployment\restart_api.py
```

Rollback: preserve runtime data, source tables and Profiles. Stop the installation's user task/processes using their owned identities, restore the prior application/config revision and prior private config only after comparing it (the original metadata config cannot serve this new dedicated account). Current metadata backups can be restored to the metadata instance only. No code revision was replaced in an existing production service, and no Fleet pointer was changed. Avoid blindly rerunning `bootstrap_portable.py`: it deliberately refuses an existing data directory.

Vendor instructions: [MySQL Windows ZIP installation](https://dev.mysql.com/doc/refman/8.4/en/windows-installation.html), [official MySQL downloads/checksum](https://dev.mysql.com/downloads/mysql/8.4.html), [nginx Windows process behavior](https://nginx.org/en/docs/windows.html).
