#!/usr/bin/env python3
"""
Daily Report Sender - Telegram
Sends a daily summary of repo activity and components added.
"""

import os
import json
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def send_telegram_message(bot_token, chat_id, text):
    """Send message via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    try:
        resp = requests.post(url, json=payload, timeout=30)
        if resp.status_code == 200:
            logger.info("Telegram message sent successfully")
            return True
        else:
            logger.error(f"Telegram error: {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Telegram send error: {e}")
        return False


def send_telegram_document(bot_token, chat_id, file_path, caption=""):
    """Send document via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    try:
        with open(file_path, "rb") as f:
            files = {"document": f}
            data = {"chat_id": chat_id, "caption": caption[:1024]}
            resp = requests.post(url, data=data, files=files, timeout=60)
            if resp.status_code == 200:
                logger.info("Telegram document sent successfully")
                return True
            else:
                logger.error(f"Telegram document error: {resp.text}")
                return False
    except Exception as e:
        logger.error(f"Telegram document send error: {e}")
        return False


def build_daily_report(data_dir):
    """Build the daily report text from data files."""
    lines = []
    lines.append("📊 <b>گزارش روزانه آرشیو کتابخانه قطعات Altium</b>")
    lines.append(f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")

    # Load update summary
    summary_path = os.path.join(data_dir, "update_summary.json")
    if os.path.exists(summary_path):
        with open(summary_path, "r") as f:
            summary = json.load(f)
        lines.append(f"📥 <b>قطعات جمع‌آوری شده:</b> {summary.get('total_fetched', 0)}")
        lines.append(f"📚 <b>کتابخانه‌های تولید شده:</b> {summary.get('total_generated', 0)}")
        lines.append("")

    # Load JLCPCB stats
    jlpcb_stats_path = os.path.join(data_dir, "jlpcb_stats.json")
    if os.path.exists(jlpcb_stats_path):
        with open(jlpcb_stats_path, "r") as f:
            stats = json.load(f)
        lines.append("🔧 <b>تفکیک دسته‌بندی:</b>")
        for cat, count in stats.get("categories", {}).items():
            lines.append(f"   • {cat}: {count} قطعه")
        lines.append("")

    # Load repo catalog
    catalog_path = os.path.join(data_dir, "external_catalog", "repo_catalog.json")
    if os.path.exists(catalog_path):
        with open(catalog_path, "r") as f:
            catalog = json.load(f)
        lines.append("📦 <b>ریپوهای اسکن شده:</b>")
        lines.append(f"   • کل ریپوهای پیدا شده: {catalog.get('repos_found', 0)}")
        lines.append(f"   • ریپوهای اسکن شده: {catalog.get('repos_scanned', 0)}")
        lines.append(f"   • ریپوهای دارای فایل Altium: {catalog.get('repos_with_altium_files', 0)}")
        lines.append(f"   • کل فایل‌های Altium: {catalog.get('total_altium_files', 0)}")
        lines.append("")

        # Top 5 repos by file count
        repos = catalog.get("repos", [])
        repos_sorted = sorted(repos, key=lambda r: r["altium_file_count"], reverse=True)
        if repos_sorted:
            lines.append("🏆 <b>Top 5 ریپوها:</b>")
            for i, r in enumerate(repos_sorted[:5], 1):
                lines.append(f"   {i}. <a href=\"{r['url']}\">{r['repo']}</a>")
                lines.append(f"      ⭐ {r['stars']} | 📁 {r['altium_file_count']} فایل")
    else:
        lines.append("ℹ️ <b>اسکن ریپوهای خارجیまだ</b> انجام نشده")

    lines.append("")
    lines.append("🔗 <a href=\"https://github.com/bahrambaba/altium-component-libraries\">ریپو GitHub</a>")

    return "\n".join(lines)


def send_daily_report(data_dir):
    """Main function to build and send daily report."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not bot_token or not chat_id:
        logger.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        return False

    report_text = build_daily_report(data_dir)

    # Send message
    success = send_telegram_message(bot_token, chat_id, report_text)

    # Also send catalog file if exists
    catalog_path = os.path.join(data_dir, "external_catalog", "repo_catalog.json")
    if os.path.exists(catalog_path) and success:
        send_telegram_document(
            bot_token, chat_id, catalog_path,
            "📋 کاتالوگ کامل ریپوهای Altium"
        )

    return success


def run(config, data_dir):
    """Entry point."""
    return {"reported": send_daily_report(data_dir)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                       format="%(asctime)s [%(levelname)s] %(message)s")
    send_daily_report("./data")
