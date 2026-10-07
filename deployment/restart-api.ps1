$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
& "$projectRoot\.venv\Scripts\python.exe" "$PSScriptRoot\backup_metadata.py"
if ($LASTEXITCODE -ne 0) { throw 'Backup failed; refusing restart.' }
$apiListener = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 5001 -State Listen
$apiProcess = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $apiListener.OwningProcess)
if ($apiProcess.CommandLine -notmatch 'uvicorn app.main:app') {
    throw 'Unexpected listener; refusing restart.'
}
Stop-Process -Id $apiListener.OwningProcess
Write-Output 'Dashboard stopped; supervisor will restart it with the current root .env.'
