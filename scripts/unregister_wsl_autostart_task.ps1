<#
.SYNOPSIS
    移除 register_wsl_autostart_task.ps1 建立的 "PensieveWslAutostart" 工作排程器任務。

.NOTES
    powershell -ExecutionPolicy Bypass -File scripts\unregister_wsl_autostart_task.ps1
#>

$TaskName = "PensieveWslAutostart"

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "已移除工作排程器任務：$TaskName"
