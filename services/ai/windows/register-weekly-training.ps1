param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path,
    [string]$TaskName = "WIDAL-SCAN-AI-Weekly-Research-Training",
    [string]$StartTime = "03:00"
)

$ErrorActionPreference = "Stop"

$AiRoot = Join-Path $ProjectRoot "services\ai"
$Python = Join-Path $AiRoot ".venv\Scripts\python.exe"
$Runner = Join-Path $AiRoot "auto_train.py"
$Dataset = Join-Path $AiRoot "data\crops\dataset.csv"
$ImageRoot = Join-Path $AiRoot "data\crops"
$Approval = Join-Path $AiRoot "data\crops\dataset_approval.json"
$Output = Join-Path $AiRoot "artifacts\auto"

if (-not (Test-Path $Python)) {
    throw "Python environment not found: $Python. Create services\ai\.venv first."
}
if (-not (Test-Path $Runner)) {
    throw "Training runner not found: $Runner"
}

$time = [DateTime]::ParseExact($StartTime, "HH:mm", [Globalization.CultureInfo]::InvariantCulture)
$quotedArgs = '"{0}" --data-csv "{1}" --image-root "{2}" --approval-file "{3}" --out-dir "{4}" --epochs 40 --batch-size 16' -f $Runner, $Dataset, $ImageRoot, $Approval, $Output

$action = New-ScheduledTaskAction -Execute $Python -Argument $quotedArgs -WorkingDirectory $AiRoot
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At $time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 8)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "Train a local WIDAL-SCAN research candidate weekly only when the ATLM-approved dataset manifest has changed. Never promotes a model automatically." -Force | Out-Null

Write-Host "Scheduled task registered: $TaskName"
Write-Host "Runs every Sunday at $StartTime."
Write-Host "It skips unchanged manifests and refuses datasets without a matching ATLM approval file."
Write-Host "Training results are saved locally under: $Output"
