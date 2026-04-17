# tools/wipeout.py
"""
全滅時プロトコル
- 資産が元手の 10%(100,000 円)以下になったら morning.py から呼ばれる
- ポジションクローズ記録・原因分析テンプレート生成・メール通知
"""

import json
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
import pytz

JST = pytz.timezone("Asia/Tokyo")
STATE_DIR = os.path.join(os.path.dirname(__file__), "../state")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "../daily/reports")


def execute_wipeout_protocol(portfolio: dict) -> dict:
    """全滅時プロトコルを実行する"""
    now = datetime.now(JST)
    date_str = now.strftime("%Y%m%d")
    total_value = portfolio.get("total_value", 0)
    initial_capital = portfolio.get("total_capital", 1000000)
    loss_pct = round((total_value / initial_capital - 1) * 100, 2)

    print("\n" + "!" * 60)
    print(f"🚨 全滅プロトコル発動: 資産 {total_value:,.0f} 円 ({loss_pct:.1f}%)")
    print("!" * 60)

    # 1. 原因分析テンプレートを生成
    wipeout_report = {
        "triggered_at": now.isoformat(),
        "total_value": total_value,
        "initial_capital": initial_capital,
        "loss_pct": loss_pct,
        "portfolio_snapshot": portfolio,
        "cause_analysis": {
            "primary_cause": "【要記入】",
            "market_conditions": "【要記入】",
            "strategy_failures": "【要記入】",
            "risk_management_failures": "【要記入】",
            "lessons_learned": "【要記入】",
        },
        "restart_approved": False,
        "status": "WIPEOUT_HALTED",
        "note": "restart するには portfolio.json の wipeout_acknowledged を true に設定してください",
    }

    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_path = os.path.join(REPORTS_DIR, f"wipeout_{date_str}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(wipeout_report, f, ensure_ascii=False, indent=2)
    print(f"📄 全滅レポートを生成: {report_path}")

    # 2. ai_behavior_log.md に教訓セクションを追記
    ai_log_path = os.path.join(STATE_DIR, "ai_behavior_log.md")
    with open(ai_log_path, "a", encoding="utf-8") as f:
        f.write(f"\n## ⚠️ 全滅記録: {now.strftime('%Y-%m-%d')}\n")
        f.write(f"- 資産: {total_value:,.0f} 円 / 元手比 {loss_pct:.1f}%\n")
        f.write("- 教訓: 【wipeout レポートを確認して記入してください】\n")

    # 3. strategy.md に改訂促進コメントを追記
    strategy_path = os.path.join(STATE_DIR, "strategy.md")
    with open(strategy_path, "a", encoding="utf-8") as f:
        f.write(f"\n## ⚠️ 全滅後の改訂が必要({now.strftime('%Y-%m-%d')})\n")
        f.write("全滅プロトコルが発動しました。戦略の全面改訂を行ってください。\n")

    # 4. メール通知
    _send_wipeout_email(total_value, loss_pct, report_path)

    # 5. portfolio に全滅フラグを立てる
    portfolio["wipeout_acknowledged"] = False
    portfolio["forced_reflection_mode"] = True
    portfolio_path = os.path.join(STATE_DIR, "portfolio.json")
    with open(portfolio_path, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=2)

    print("\n📋 次のアクション:")
    print(f"   1. {report_path} の cause_analysis を記入してください")
    print("   2. state/strategy.md を全面改訂してください")
    print("   3. 準備ができたら portfolio.json の wipeout_acknowledged を true に変更してください")

    return wipeout_report


def _send_wipeout_email(total_value: float, loss_pct: float, report_path: str):
    """全滅通知メールを送信する(SMTP 設定がない場合はスキップ)"""
    notify_email = os.getenv("NOTIFY_EMAIL", "")
    smtp_host = os.getenv("SMTP_HOST", "")

    if not notify_email or not smtp_host:
        print("⚠️ メール通知設定なし(NOTIFY_EMAIL / SMTP_HOST 未設定)。通知をスキップします。")
        return

    try:
        subject = f"【緊急】トレーディングエージェント全滅プロトコル発動"
        body = (
            f"資産残高が元手の 10% 以下になりました。\n\n"
            f"現在の資産: {total_value:,.0f} 円 ({loss_pct:.1f}%)\n"
            f"レポートパス: {report_path}\n\n"
            f"原因分析と戦略改訂を行った後、portfolio.json の "
            f"wipeout_acknowledged を true に設定してください。"
        )
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = notify_email
        msg["To"] = notify_email

        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", notify_email)
        smtp_pass = os.getenv("SMTP_PASS", "")

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            if smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        print(f"✅ 全滅通知メールを送信しました: {notify_email}")
    except Exception as e:
        print(f"⚠️ メール送信失敗({e})。手動で確認してください。")
