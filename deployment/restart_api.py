"""Back up metadata and restart only the installed API; supervisor recovers it."""
import subprocess
from backup_metadata import main as backup

backup()
command = r'''
$ErrorActionPreference = 'Stop'
$apiListener = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 5001 -State Listen
$apiProcess = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $apiListener.OwningProcess)
if ($apiProcess.CommandLine -notmatch 'uvicorn app.main:app') {
    throw 'Unexpected listener; refusing restart.'
}
Stop-Process -Id $apiListener.OwningProcess
Write-Output 'Dashboard stopped; its supervisor will restart it.'
'''
subprocess.run(['powershell.exe','-NoProfile','-Command',command],check=True,creationflags=0x08000000)
