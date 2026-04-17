# tools/backup.py
"""GitHub 自動バックアップ(毎日 23:00 JST に実行)"""

import os
import subprocess
from datetime import datetime
import pytz

JST = pytz.timezone("Asia/Tokyo")
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def run_git(args: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(
        ["git"] + args,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def backup() -> bool:
    """state/ と daily/reports/ と CLAUDE.md を GitHub にコミット・プッシュする"""
    now = datetime.now(JST)
    date_str = now.strftime("%Y-%m-%d %H:%M JST")
    print(f"🔄 バックアップ開始: {date_str}")

    code, _, err = run_git(["add", "state/", "daily/reports/", "CLAUDE.md"])
    if code != 0:
        print(f"❌ git add 失敗: {err}")
        return False

    code, changed, _ = run_git(["diff", "--cached", "--name-only"])
    if not changed:
        print("✅ 変更なし。バックアップをスキップします。")
        return True

    code, _, err = run_git(["commit", "-m", f"auto-backup: {date_str}"])
    if code != 0:
        print(f"❌ git commit 失敗: {err}")
        return False

    code, out, err = run_git(["push"])
    if code != 0:
        print(f"❌ git push 失敗: {err}")
        print("   → ネットワーク問題の場合は翌日再試行します")
        return False

    print(f"✅ バックアップ完了")
    return True


if __name__ == "__main__":
    import schedule
    import time

    schedule.every().day.at("23:00").do(backup)
    print("⏰ バックアップスケジューラー起動(毎日 23:00 JST)")
    while True:
        schedule.run_pending()
        time.sleep(60)
