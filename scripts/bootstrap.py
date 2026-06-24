#!/usr/bin/env python3
"""跨平台啟動檢查腳本，設計依據見 Instruction/auto_restart.md。

用法：
    python3 scripts/bootstrap.py

只用標準函式庫，因為這支腳本本身要在 poetry/專案依賴裝好「之前」就能跑。
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_TOOLS = ["git", "docker", "node", "npx", "jq", "uv", "poetry"]

INSTALL_HINTS = {
    "wsl": {
        "git": "sudo apt-get install -y git",
        "docker": "未偵測到 docker：請在 Windows 端安裝 Docker Desktop，並於 Settings → Resources → WSL Integration 對這個 distro 開啟",
        "node": "sudo apt-get install -y nodejs npm",
        "npx": "隨 node/npm 一起安裝，缺 npx 通常代表 node 也沒裝好",
        "jq": "sudo apt-get install -y jq",
        "uv": "curl -LsSf https://astral.sh/uv/install.sh | sh",
        "poetry": "curl -sSL https://install.python-poetry.org | python3 -",
    },
    "linux": {
        "git": "sudo apt-get install -y git",
        "docker": "依你的 distro 安裝 Docker Engine：https://docs.docker.com/engine/install/",
        "node": "sudo apt-get install -y nodejs npm",
        "npx": "隨 node/npm 一起安裝，缺 npx 通常代表 node 也沒裝好",
        "jq": "sudo apt-get install -y jq",
        "uv": "curl -LsSf https://astral.sh/uv/install.sh | sh",
        "poetry": "curl -sSL https://install.python-poetry.org | python3 -",
    },
    "mac": {
        "git": "brew install git",
        "docker": "brew install --cask docker（或直接到官網下載 Docker Desktop for Mac）",
        "node": "brew install node",
        "npx": "隨 node 一起安裝，缺 npx 通常代表 node 也沒裝好",
        "jq": "brew install jq",
        "uv": "curl -LsSf https://astral.sh/uv/install.sh | sh",
        "poetry": "curl -sSL https://install.python-poetry.org | python3 -",
    },
    "windows-native": {
        "git": "winget install Git.Git",
        "docker": "winget install Docker.DockerDesktop",
        "node": "winget install OpenJS.NodeJS",
        "npx": "隨 node 一起安裝，缺 npx 通常代表 node 也沒裝好",
        "jq": "winget install jqlang.jq",
        "uv": "powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\"",
        "poetry": "(curl -sSL https://install.python-poetry.org | py -)",
    },
}

PRIVATE_FILES = [
    ".env",
    ".env.docker",
    "CLAUDE.md",
    "log.md",
    "learn.md",
    "Instruction/",
    "logs/",
    "Upgrade/",
    ".claude/settings.local.json",
]


def banner(title: str) -> None:
    print(f"\n=== {title} ===")


def detect_env() -> str:
    system = platform.system()
    if system == "Linux":
        version_file = Path("/proc/version")
        if version_file.exists() and "microsoft" in version_file.read_text().lower():
            return "wsl"
        return "linux"
    if system == "Darwin":
        return "mac"
    if system == "Windows":
        return "windows-native"
    return "unknown"


def check_tools(env: str) -> list[str]:
    missing = []
    hints = INSTALL_HINTS.get(env, {})
    for tool in REQUIRED_TOOLS:
        if shutil.which(tool) is None:
            missing.append(tool)
            hint = hints.get(tool, "(此平台沒有對應的安裝提示，請自行查詢)")
            print(f"  [缺] {tool} -> {hint}")
        else:
            print(f"  [OK] {tool}")
    return missing


def check_docker_wsl_integration(env: str) -> None:
    if env != "wsl":
        return
    if shutil.which("docker") is None:
        return
    result = subprocess.run(["docker", "info"], capture_output=True, text=True)
    if result.returncode != 0:
        print(
            "  [警告] docker 指令存在但連不上 Docker Desktop，"
            "請確認 Settings → Resources → WSL Integration 已對這個 distro 開啟"
        )
    else:
        print("  [OK] docker 可正常連線 Docker Desktop")


def check_venv(missing_tools: list[str]) -> None:
    venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"
    if venv_python.exists():
        print(f"  [OK] 已存在 {venv_python}，跳過建置")
        return

    if "uv" in missing_tools or "poetry" in missing_tools:
        print("  [跳過] uv/poetry 尚未安裝，先處理上面的工具缺漏再重跑這支腳本")
        return

    print("  尚未建置 .venv，依以下固定順序手動執行(腳本不自動跑，避免互動式安裝卡住)：")
    print("    1) uv python install 3.13")
    print("    2) $(uv python find 3.13) -m venv .venv")
    print("    3) poetry env use ./.venv/bin/python")
    print("    4) poetry install")
    print("  (順序原因見 Instruction/auto_restart.md 第 3 節：")
    print("   poetry 直接指到 uv 裝的 standalone Python 會誤判成既有 venv，污染共用環境)")


def pick_env_template(env: str) -> None:
    env_file = PROJECT_ROOT / ".env"
    example_file = PROJECT_ROOT / ".env.example"

    if env_file.exists():
        print(f"  [OK] {env_file} 已存在，不覆蓋")
    elif example_file.exists():
        shutil.copy(example_file, env_file)
        print(f"  已複製 {example_file.name} -> {env_file.name}，內容需要手動填寫")
    else:
        print("  [警告] 找不到 .env.example，無法自動建立 .env")

    path_style = "/mnt/c/... 或 WSL 原生路徑" if env in ("wsl", "linux", "mac") else "C:/Users/... 這種 Windows 路徑"
    print(f"  此平台({env})的路徑欄位請填成：{path_style}")

    docker_env_file = PROJECT_ROOT / ".env.docker"
    if env in ("wsl", "linux", "mac") and not docker_env_file.exists():
        print("  [提醒] 若要用 docker compose --env-file .env.docker 啟動，需自行建立 .env.docker(WSL/Unix 路徑風格)")


def check_private_files() -> list[str]:
    missing = []
    for rel_path in PRIVATE_FILES:
        full_path = PROJECT_ROOT / rel_path
        if full_path.exists():
            print(f"  [OK] {rel_path}")
        else:
            missing.append(rel_path)
            print(f"  [缺] {rel_path}")
    if missing:
        print("  以上缺漏的檔案/資料夾不在 git 裡(.gitignore 排除)，需從雲端硬碟/USB 從舊機器手動複製過來")
    return missing


def ask_role() -> None:
    banner("7. 角色判斷(server vs dev)")
    print("這台機器要設定成：")
    print("  [1] 24 小時常駐伺服器(會用到 pensieve 常駐服務 + 開機自動啟動)")
    print("  [2] 日常開發/瀏覽機器(不設常駐 pensieve，只用獨立測試 bot 做開發測試)")
    try:
        choice = input("請輸入 1 或 2(直接 Enter 跳過)：").strip()
    except EOFError:
        choice = ""

    if choice == "1":
        print("  -> 常駐伺服器角色，後續手動步驟：")
        print("     1) 確認 .env / .env.docker 路徑正確")
        print("     2) 參考 scripts/pensieve.service，sudo cp 到 /etc/systemd/system/ 後")
        print("        sudo systemctl daemon-reload && sudo systemctl enable --now pensieve")
        print("     3) Windows 端需要開機喚醒 WSL 的話，跑 scripts/register_wsl_autostart_task.ps1(系統管理員權限)")
    elif choice == "2":
        print("  -> 開發/瀏覽機器角色，後續手動步驟：")
        print("     1) 不要安裝/啟用 pensieve.service，避免跟正式版搶同一個 Telegram bot")
        print("     2) 需要手動測試 pensieve 時，先建立獨立測試 bot + .env.test(目前專案還沒有現成範本，")
        print("        需自行新增，內容比照 .env.example 但換成測試 bot 的 TELEGRAM_BOT_TOKEN)")
        print("     3) 詳見 Instruction/model_change.md 第 5 節")
    else:
        print("  -> 已跳過，之後想清楚再重跑這支腳本")


def main() -> None:
    banner("1. 平台偵測")
    env = detect_env()
    print(f"  偵測結果：{env}")
    if env == "unknown":
        print("  [警告] 無法識別平台，以下步驟可能需要手動調整")

    banner("2. 工具齊備檢查")
    missing_tools = check_tools(env)
    check_docker_wsl_integration(env)

    banner("3. Python/Poetry 虛擬環境")
    check_venv(missing_tools)

    banner("4. 設定檔(.env)選擇")
    pick_env_template(env)

    banner("5/6. 私人檔案(.gitignore 排除清單)檢查")
    check_private_files()

    ask_role()

    banner("完成")
    print("這支腳本只負責偵測/提示/建立範本，實際安裝(sudo/系統管理員權限步驟)請依上面印出的指令自行執行。")
    if missing_tools:
        print(f"提醒：以下工具尚未安裝，先處理完再重跑一次本腳本：{', '.join(missing_tools)}")


if __name__ == "__main__":
    sys.exit(main() or 0)
