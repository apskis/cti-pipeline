# Register the local pipeline schedule in Windows Task Scheduler (run once, as yourself).
#   .\scripts\register-schedule.ps1            # create or update the tasks
#   .\scripts\register-schedule.ps1 -Remove    # delete them
#   .\scripts\register-schedule.ps1 -Company acme          # the same schedule for another company
#   .\scripts\register-schedule.ps1 -Company acme -Remove  # delete only that company's tasks
# bulletin-scan Mon/Wed/Fri 09:00, weekly reporting Mon 11:00. Runs only while you are
# logged on (Docker Desktop lives in your session); a missed run starts when you log on.
# The no-op components (perimeter-scan, documentation-sync) are left out on purpose.
param(
  [switch]$Remove,
  [ValidatePattern('^[a-z0-9][a-z0-9-]{0,39}$')][string]$Company = "genelabs"
)
$ErrorActionPreference = "Stop"
$Repo = Resolve-Path (Join-Path $PSScriptRoot "..")
$Folder = "\CTI Pipeline\"
# GeneLabs keeps the task names it already has; another company's carry its slug.
$Prefix = if ($Company -eq "genelabs") { "CTI " } else { "CTI $Company " }
$Names = @("${Prefix}bulletin-scan", "${Prefix}reporting weekly")

if ($Remove) {
  # Only this company's tasks, matched by exact name.
  Get-ScheduledTask -TaskPath $Folder -ErrorAction SilentlyContinue |
    Where-Object { $Names -contains $_.TaskName } |
    Unregister-ScheduledTask -Confirm:$false
  "removed $($Names -join ', ') under $Folder"
  exit 0
}

$Script = Join-Path $Repo "scripts\run-scheduled.ps1"
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
  -ExecutionTimeLimit (New-TimeSpan -Hours 4) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
  -LogonType Interactive -RunLevel Limited
$Jobs = @(
  @{ Name = $Names[0]; Args = "bulletin-scan -Company $Company"
     Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Wednesday, Friday -At 9:00am },
  @{ Name = $Names[1]; Args = "reporting -Mode weekly -Company $Company"
     Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 11:00am }
)
foreach ($Job in $Jobs) {
  $Action = New-ScheduledTaskAction -Execute "powershell.exe" -WorkingDirectory $Repo `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Script`" $($Job.Args)"
  Register-ScheduledTask -TaskPath $Folder -TaskName $Job.Name -Action $Action `
    -Trigger $Job.Trigger -Settings $Settings -Principal $Principal -Force `
    -Description "CTI pipeline for $Company, local run on the Claude plan (CLOUD=local, no AWS)." | Out-Null
}
Get-ScheduledTask -TaskPath $Folder | Where-Object { $Names -contains $_.TaskName } | ForEach-Object {
  "{0}: next run {1}" -f $_.TaskName, ($_ | Get-ScheduledTaskInfo).NextRunTime
}
