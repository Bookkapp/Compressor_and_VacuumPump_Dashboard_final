$ErrorActionPreference = "Stop"

$mysqlRoot = Join-Path $PSScriptRoot ".mysql"
$mysqlExe = Join-Path $mysqlRoot "mysql-8.4.11-winx64\bin\mysqld.exe"
$mysqlConfig = Join-Path $mysqlRoot "my.ini"
$pythonExe = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $mysqlExe)) {
    throw "Portable MySQL Server was not found at $mysqlExe"
}

$mysqlListening = Test-NetConnection 127.0.0.1 -Port 3306 -InformationLevel Quiet -WarningAction SilentlyContinue
if (-not $mysqlListening) {
    Start-Process -FilePath $mysqlExe `
        -ArgumentList "--defaults-file=$mysqlConfig", "--console" `
        -WindowStyle Hidden

    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        if (Test-NetConnection 127.0.0.1 -Port 3306 -InformationLevel Quiet -WarningAction SilentlyContinue) {
            $mysqlListening = $true
            break
        }
        Start-Sleep -Seconds 1
    }
}

if (-not $mysqlListening) {
    throw "MySQL Server did not become ready on 127.0.0.1:3306"
}

& $pythonExe -m uvicorn app.main:app --host 0.0.0.0 --port 5001
