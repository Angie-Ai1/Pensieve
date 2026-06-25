<#
.SYNOPSIS
    移除 register_history_export_task.ps1 建立的 "PensieveBrowserHistoryExport" 工作排程器任務。

.NOTES
    powershell -ExecutionPolicy Bypass -File scripts\unregister_history_export_task.ps1
#>

$TaskName = "PensieveBrowserHistoryExport"

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "已移除工作排程器任務：$TaskName"
