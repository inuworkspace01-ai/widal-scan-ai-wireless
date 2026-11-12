param(
    [string]$TaskName = "WIDAL-SCAN-AI-Weekly-Research-Training"
)

$ErrorActionPreference = "Stop"
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Write-Host "Scheduled task removed: $TaskName"
