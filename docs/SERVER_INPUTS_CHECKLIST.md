# Dashboard Server inputs checklist

The complete two-system checklist is maintained in the ML repository at `deployment/SERVER_INPUTS_CHECKLIST.md`. This repository-specific checklist records the values needed by the Dashboard.

## Required files

- `.env` created locally on Server from `.env.example`; never commit it.
- `requirements.txt`, `package-lock.json`, `schema.sql`, `app/`, `frontend/` and the production-built `public/` directory.
- Private-repository SSH deploy key or an approved credential helper; never store a GitHub token in `.env`.

## Required service values

| Setting | Intended value |
| --- | --- |
| App server | `10.195.17.69` |
| MySQL server | `10.195.17.73:3306` |
| Metadata schema | `predictive_maintenance` |
| Vacuum source | `vacuum_pump_db.vacuum_pump_readings` |
| Compressor source | `ht9046mx_iot.ht9046mx_readings` |
| Compressor output | v1 compatibility `ht9046mx_iot.compressor_health_scores`; keep disabled until staging acceptance |
| App timezone | `Asia/Bangkok` |
| Port | `5001` behind the approved HTTPS reverse proxy |

Use the following MySQL identities: `predictive_app` for Dashboard metadata read/write, `vacuum_reader` for Vacuum source `SELECT`, and `compressor_reader` for Compressor source/output `SELECT`. Their passwords, the application `SECRET_KEY`, and the Dashboard login passwords belong in the Server secret store and the ignored local handoff—not Git.

Production requires `APP_ENV=production`, a unique `SECRET_KEY` of at least 32 characters, and distinct `ADMIN_PASSWORD`/`USER_PASSWORD` values of at least 12 characters. Keep `MQTT_ENABLED=false` and `SEED_DEMO_DATA=false`.

Run before release:

```bash
python -m pytest -q
npm ci
npm run frontend:build
python -m uvicorn app.main:app --host 0.0.0.0 --port 5001
```

Do not enable `COMPRESSOR_HEALTH_ENABLED` until the ML table contract, freshness/timezone, profile approval, runtime model provenance, alert ownership and staging load tests pass.
