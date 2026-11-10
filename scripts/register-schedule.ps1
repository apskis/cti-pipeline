# Register the local pipeline schedule in Windows Task Scheduler (run once, as yourself).
#   .\scripts\register-schedule.ps1            # create or update the tasks
#   .\scripts\register-schedule.ps1 -Remove    # delete them
# bulletin-scan Mon/Wed/Fri 09:00, weekly reporting Mon 11:00. Runs only while you are
# logged on (Docker Desktop lives in your session); a missed run starts when you log on.
# The no-op components (perimeter-scan, documentation-sync) are left out on purpose.
param([switch]$Remove)
$ErrorActionPreference = "Stop"
$Repo = Resolve-Path (Join-Path $PSScriptRoot "..")
$Folder = "\CTI Pipeline\"

if ($Remove) {
  Get-ScheduledTask -TaskPath $Folder -ErrorAction SilentlyContinue |
    Unregister-ScheduledTask -Confirm:$false
  "removed the tasks under $Folder"
  exit 0
}

$Script = Join-Path $Repo "scripts\run-scheduled.ps1"
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
  -ExecutionTimeLimit (New-TimeSpan -Hours 4) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
  -LogonType Interactive -RunLevel Limited
$Jobs = @(
  @{ Name = "CTI bulletin-scan"; Args = "bulletin-scan"
     Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Wednesday, Friday -At 9:00am },
  @{ Name = "CTI reporting weekly"; Args = "reporting -Mode weekly"
     Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 11:00am }
)
foreach ($Job in $Jobs) {
  $Action = New-ScheduledTaskAction -Execute "powershell.exe" -WorkingDirectory $Repo `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Script`" $($Job.Args)"
  Register-ScheduledTask -TaskPath $Folder -TaskName $Job.Name -Action $Action `
    -Trigger $Job.Trigger -Settings $Settings -Principal $Principal -Force `
    -Description "GeneLabs CTI pipeline, local run on the Claude plan (CLOUD=local, no AWS)." | Out-Null
}
Get-ScheduledTask -TaskPath $Folder | ForEach-Object {
  "{0}: next run {1}" -f $_.TaskName, ($_ | Get-ScheduledTaskInfo).NextRunTime
}
