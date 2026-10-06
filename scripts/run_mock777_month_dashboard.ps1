$ErrorActionPreference = 'Stop'
if (-not $env:ADMIN_USERNAME -or -not $env:ADMIN_PASSWORD) { throw 'Set ADMIN_USERNAME and ADMIN_PASSWORD in the local environment before running this mock helper.' }
$env:DB_NAME = 'pm_mock777_month_dashboard'
$env:COMPRESSOR_SCHEMA = 'ht_mock777_month_source'
$env:COMPRESSOR_HEALTH_SCHEMA = 'ht_mock777_month_source'
$env:VACUUM_SCHEMA = 'ht_mock777_month_source'
$env:TELEMETRY_DB_HOST = '127.0.0.1'
$env:TELEMETRY_POLL_INTERVAL_SECONDS = '5'
$env:SEED_DEMO_DATA = 'false'
python -m uvicorn app.main:app --host 127.0.0.1 --port 5015 --no-access-log --log-level warning
