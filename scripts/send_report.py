#!/usr/bin/env python3
"""
Daily Report - Telegram
Shows what was added today after the GitHub Action ran.
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
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
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


def count_files_in_dir(directory):
    """Recursively count files in a directory."""
    count = 0
    if os.path.exists(directory):
        for _, _, files in os.walk(directory):
            count += len(files)
    return count


def build_daily_report(data_dir):
    """Build a simple daily report: only what's new today."""
    now = datetime.utcnow()
    today_str = now.strftime("%Y-%m-%d")

    lines = []
    lines.append("📚 <b>گزارش روزانه کتابخانه Altium</b>")
    lines.append(f"📅 {today_str}")
    lines.append("")

    # Count actual files in libraries
    schlib_dir = os.path.join(data_dir, "..", "libraries", "SchLib")
    pcblib_dir = os.path.join(data_dir, "..", "libraries", "PcbLib")
    schlib_count = count_files_in_dir(schlib_dir)
    pcblib_count = count_files_in_dir(pcblib_dir)

    if schlib_count > 0 or pcblib_count > 0:
        lines.append("🔧 <b>کتابخانه‌های موجود:</b>")
        lines.append(f"   • SchLib (نمادها): {schlib_count}")
        lines.append(f"   • PcbLib (فوترپرینت): {pcblib_count}")
        lines.append("")

    # Count actual files in external
    ext_dir = os.path.join(data_dir, "external_catalog", "external")
    ext_count = count_files_in_dir(ext_dir)
    if ext_count > 0:
        lines.append("📦 <b>فایل‌های دانلود شده از GitHub:</b>")
        lines.append(f"   • مجموع: {ext_count} فایل")

        # Count by repo
        if os.path.exists(ext_dir):
            for repo_name in sorted(os.listdir(ext_dir)):
                repo_path = os.path.join(ext_dir, repo_name)
                if os.path.isdir(repo_path):
                    repo_files = count_files_in_dir(repo_path)
                    if repo_files > 0:
                        lines.append(f"   • {repo_name}: {repo_files}")
        lines.append("")

    # Load update summary for new additions
    summary_path = os.path.join(data_dir, "update_summary.json")
    if os.path.exists(summary_path):
        with open(summary_path, "r") as f:
            summary = json.load(f)
        
        sources = summary.get("sources", [])
        new_count = 0
        for src in sources:
            if src.get("source") == "Altium Generator":
                new_count = src.get("generated", 0)
        
        if new_count > 0:
            lines.append(f"➕ <b>کتابخانه‌های جدید امروز:</b> {new_count}")
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
    return send_telegram_message(bot_token, chat_id, report_text)


def run(config, data_dir):
    """Entry point."""
    return {"reported": send_daily_report(data_dir)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                       format="%(asctime)s [%(levelname)s] %(message)s")
    send_daily_report("./data")
