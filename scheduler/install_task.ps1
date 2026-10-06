$ErrorActionPreference = 'Stop'
Write-Warning 'DEPRECATED V1: production chạy trên GitHub Actions. Script này chỉ để tham khảo, không đăng ký lại lịch local.'
return
$projectRoot = Split-Path -Parent $PSScriptRoot
$config = Get-Content -LiteralPath (Join-Path $projectRoot 'config\config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$taskName = 'AI_MORNING_NEWS_AGENT_0700'
$action = New-ScheduledTaskAction -Execute (Join-Path $projectRoot 'RUN_AGENT.cmd') -WorkingDirectory $projectRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $config.scheduler_time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 20) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
$task = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'Bản tin sáng miễn phí; RSS công khai, publish GitHub Pages.'
Register-ScheduledTask -TaskName $taskName -InputObject $task -Force | Out-Null
Export-ScheduledTask -TaskName $taskName | Set-Content -LiteralPath (Join-Path $PSScriptRoot ($taskName + '.xml')) -Encoding Unicode
Get-ScheduledTask -TaskName $taskName | Select-Object TaskName,State,Actions,Triggers,Settings
Get-ScheduledTaskInfo -TaskName $taskName | Select-Object NextRunTime,LastRunTime,LastTaskResult
Write-Output '[PASS] Task Scheduler registered'
