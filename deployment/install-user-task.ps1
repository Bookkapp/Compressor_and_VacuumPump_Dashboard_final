$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$taskUser = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$taskAction = New-ScheduledTaskAction -Execute "$projectRoot\.venv\Scripts\pythonw.exe" -Argument ('"' + "$PSScriptRoot\portable_supervisor.py" + '"') -WorkingDirectory $projectRoot
$taskTrigger = New-ScheduledTaskTrigger -AtLogOn -User $taskUser
$taskPrincipal = New-ScheduledTaskPrincipal -UserId $taskUser -LogonType Interactive -RunLevel Limited
$taskSettings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -RestartCount 10 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
if (Get-ScheduledTask -TaskName 'ADI-PM-Dashboard-Portable' -ErrorAction SilentlyContinue) {
    throw 'Task already exists; inspect it before updating.'
}
Register-ScheduledTask -TaskName 'ADI-PM-Dashboard-Portable' -Action $taskAction -Trigger $taskTrigger -Principal $taskPrincipal -Settings $taskSettings
Start-ScheduledTask -TaskName 'ADI-PM-Dashboard-Portable'
