$ErrorActionPreference = 'Stop'
if (-not $env:ADMIN_USERNAME -or -not $env:ADMIN_PASSWORD) { throw 'Set ADMIN_USERNAME and ADMIN_PASSWORD in the local environment before running this mock helper.' }
python -m scripts.mock_multi_tab_read --url http://127.0.0.1:5014 --tabs 8 --rounds 2 --charts --gzip
