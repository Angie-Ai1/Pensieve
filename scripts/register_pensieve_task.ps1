<#
.SYNOPSIS
    註冊 Windows 工作排程器任務，於使用者登入時自動啟動 pensieve（失敗時自動重啟）。

.DESCRIPTION
    建立名為 "Pensieve" 的工作排程器任務：
    - 觸發時機：使用者登入時
    - 動作：在專案目錄下執行 `poetry run python -m pensieve.main`
    - 失敗時：1 分鐘後自動重試，最多 3 次
    - 無執行時間上限（預設 72 小時會中止常駐 process，已關閉此限制）

.NOTES
    需以一般使用者權限執行：
        powershell -ExecutionPolicy Bypass -File scripts\register_pensieve_task.ps1
    移除任務請執行 scripts\unregister_pensieve_task.ps1
#>

$TaskName = "Pensieve"
$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path
$Poetry = Get-Command poetry -ErrorAction Stop

$action = New-ScheduledTaskAction -Execute $Poetry.Source -Argument "run python -m pensieve.main" -WorkingDirectory $ProjectRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Seconds 0) `
    -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
    -Description "pensieve 互動式 AI Agent（Telegram Bot 問答 + 每日推播）常駐執行" -Force

Write-Host "已註冊工作排程器任務：$TaskName"
Write-Host "立即啟動：Start-ScheduledTask -TaskName $TaskName"
Write-Host "查看狀態：Get-ScheduledTask -TaskName $TaskName | Get-ScheduledTaskInfo"
