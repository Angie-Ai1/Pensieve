<#
.SYNOPSIS
    移除 register_pensieve_task.ps1 建立的 "Pensieve" 工作排程器任務。

.NOTES
    powershell -ExecutionPolicy Bypass -File scripts\unregister_pensieve_task.ps1
#>

$TaskName = "Pensieve"

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "已移除工作排程器任務：$TaskName"
