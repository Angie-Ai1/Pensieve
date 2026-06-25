<#
.SYNOPSIS
    註冊 Windows 工作排程器任務，定期執行 export_browser_history_for_sync.ps1，
    把這台電腦的瀏覽紀錄同步到 Google 雲端硬碟，供舊電腦合併讀取。

.DESCRIPTION
    建立名為 "PensieveBrowserHistoryExport" 的工作排程器任務：
    - 觸發時機：使用者登入時 + 之後每 1 小時重複執行一次(這台電腦不一定在舊
      電腦產生每日彙整的 23:30 當下開機，所以用「平時定期同步」取代「準時一次」)
    - 動作：執行 export_browser_history_for_sync.ps1

.NOTES
    需以系統管理員權限執行（否則 Register-ScheduledTask 會回傳 0x80070005 存取被拒）：
        Start-Process powershell -Verb RunAs
        powershell -ExecutionPolicy Bypass -File scripts\register_history_export_task.ps1
    移除任務請執行 scripts\unregister_history_export_task.ps1
#>

$TaskName = "PensieveBrowserHistoryExport"
$ScriptPath = Join-Path $PSScriptRoot "export_browser_history_for_sync.ps1"

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ScriptPath`""

$loginTrigger = New-ScheduledTaskTrigger -AtLogOn
$repeatingTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration ([TimeSpan]::MaxValue)

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

Register-ScheduledTask -TaskName $TaskName -Action $action `
    -Trigger @($loginTrigger, $repeatingTrigger) -Settings $settings `
    -Description "定期把本機 Chrome/Edge 瀏覽紀錄同步到 Google 雲端硬碟，供舊電腦 n8n 合併讀取" `
    -Force -ErrorAction Stop

Write-Host "已註冊工作排程器任務：$TaskName"
Write-Host "立即測試：Start-ScheduledTask -TaskName $TaskName"
Write-Host "查看狀態：Get-ScheduledTask -TaskName $TaskName | Get-ScheduledTaskInfo"
