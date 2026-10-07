$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Start-Process -FilePath "$projectRoot\.venv\Scripts\pythonw.exe" -ArgumentList ('"' + "$PSScriptRoot\portable_supervisor.py" + '"') -WorkingDirectory $projectRoot -WindowStyle Hidden
