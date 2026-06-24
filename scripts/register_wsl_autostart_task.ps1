<#
.SYNOPSIS
    註冊 Windows 工作排程器任務，於使用者登入時喚醒 WSL（Ubuntu）VM，
    讓裡面的 systemd 自動把 pensieve.service 啟動起來。

.DESCRIPTION
    pensieve 已改為在 WSL 內以 systemd service 常駐執行（見 scripts/pensieve.service），
    systemd 會在 WSL VM 啟動時自動啟動 pensieve，但 WSL VM 本身預設不會隨 Windows
    登入自動啟動。本腳本建立名為 "PensieveWslAutostart" 的工作排程器任務：
    - 觸發時機：使用者登入時
    - 動作：執行 `wsl.exe -d Ubuntu -e true`，只負責把 VM 叫醒，不直接啟動 pensieve
      （此機器的 WSL 預設 distro 是 docker-desktop，不是 Ubuntu，故必須明確帶 -d）
    - VM 啟動後續流程交給 WSL 內的 systemd 處理，本任務不需要重試邏輯

.NOTES
    需以系統管理員權限執行（否則 Register-ScheduledTask 會回傳 0x80070005 存取被拒）：
        Start-Process powershell -Verb RunAs
        powershell -ExecutionPolicy Bypass -File scripts\register_wsl_autostart_task.ps1
    移除任務請執行 scripts\unregister_wsl_autostart_task.ps1
#>

$TaskName = "PensieveWslAutostart"
$WslDistro = "Ubuntu"

$action = New-ScheduledTaskAction -Execute "wsl.exe" -Argument "-d $WslDistro -e true"
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Seconds 30)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
    -Description "登入時喚醒 WSL $WslDistro，讓裡面的 systemd 啟動 pensieve.service" -Force -ErrorAction Stop

Write-Host "已註冊工作排程器任務：$TaskName"
Write-Host "立即測試：Start-ScheduledTask -TaskName $TaskName"
Write-Host "查看狀態：Get-ScheduledTask -TaskName $TaskName | Get-ScheduledTaskInfo"
