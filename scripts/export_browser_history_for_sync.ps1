<#
.SYNOPSIS
    將本機 Chrome/Edge 的瀏覽紀錄(History)複製到 Google 雲端硬碟同步資料夾，
    讓舊電腦的 n8n workflow 之後可以合併讀取。

.DESCRIPTION
    Chrome/Edge 開著時 History 資料庫會被鎖定，所以用複製(而非直接掛載)的方式
    取得一份快照，行為對應 workflows/01_browser_history.json 內既有的
    fs.copyFileSync 做法。複製目的地是 Google Drive 桌面版同步出來的本機資料夾，
    存進去後會自動上傳，舊電腦端裝有同一 Google 帳號的 Drive 桌面版即可在自己的
    本機路徑讀到。

    請先把下方 $SyncFolder 改成本機 Google Drive 桌面版實際同步出來的路徑
    (磁碟機代號因機器而異，無法寫死)。

.NOTES
    需搭配 scripts\register_history_export_task.ps1 註冊排程，定期自動執行。
    手動測試：powershell -ExecutionPolicy Bypass -File scripts\export_browser_history_for_sync.ps1
#>

$SyncFolder = "G:\我的雲端硬碟\Pensieve_BrowserHistorySync"

$sources = @(
    @{ Name = "chrome"; Path = "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\History" },
    @{ Name = "edge";   Path = "$env:LOCALAPPDATA\Microsoft\Edge\User Data\Default\History" }
)

if (-not (Test-Path $SyncFolder)) {
    Write-Error "找不到同步資料夾：$SyncFolder(請確認 Google Drive 桌面版已同步、磁碟機代號是否正確)"
    exit 1
}

foreach ($source in $sources) {
    $dest = Join-Path $SyncFolder "$($source.Name)_History"
    try {
        Copy-Item -Path $source.Path -Destination $dest -Force -ErrorAction Stop
        Write-Host "[$($source.Name)] 已複製到 $dest"
    } catch {
        Write-Warning "[$($source.Name)] 複製失敗：$($_.Exception.Message)"
    }
}
