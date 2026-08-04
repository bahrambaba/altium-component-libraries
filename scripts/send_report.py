#!/usr/bin/env python3
"""
Daily Report - Telegram
Only shows what was added today after the GitHub Action ran.
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


def build_daily_report(data_dir):
    """Build a simple daily report: only what's new today."""
    now = datetime.utcnow()
    today_str = now.strftime("%Y-%m-%d")

    lines = []
    lines.append("📚 <b>گزارش روزانه کتابخانه Altium</b>")
    lines.append(f"📅 {today_str}")
    lines.append("")

    # Load update summary
    summary_path = os.path.join(data_dir, "update_summary.json")
    if os.path.exists(summary_path):
        with open(summary_path, "r") as f:
            summary = json.load(f)
        
        # Sources
        sources = summary.get("sources", [])
        for src in sources:
            source_name = src.get("source", "?")
            if source_name == "JLCPCB/LCSC":
                cats = src.get("details", {}).get("categories", {})
                if cats:
                    lines.append("📦 <b>قطعات جدید:</b>")
                    for cat, count in cats.items():
                        lines.append(f"   • {cat}: {count}")
                    lines.append(f"   <b>مجموع: {src.get('total', 0)}</b>")
                    lines.append("")
            
            elif source_name == "GitHub Aggregator":
                repos_count = src.get("details", {}).get("repos", 0)
                downloaded = src.get("details", {}).get("downloaded", 0)
                if repos_count > 0:
                    lines.append("🔗 <b>GitHub:</b>")
                    lines.append(f"   • ریپوها: {repos_count}")
                    lines.append(f"   • فایل‌های دانلود شده: {downloaded}")
                    lines.append("")
            
            elif source_name == "Altium Generator":
                cats = src.get("details", {}).get("categories", [])
                if cats:
                    lines.append("🔧 <b>کتابخانه‌های جدید:</b>")
                    for c in cats:
                        name = c.get("name", "?")
                        comp_count = c.get("components", 0)
                        lines.append(f"   • {name}: {comp_count} قطعه")
                    lines.append(f"   <b>مجموع: {src.get('generated', 0)} جفت کتابخانه</b>")
                    lines.append("")

    # Load repo catalog
    catalog_path = os.path.join(data_dir, "external_catalog", "repo_catalog.json")
    if os.path.exists(catalog_path):
        with open(catalog_path, "r") as f:
            catalog = json.load(f)
        
        total_files = catalog.get("total_altium_files", 0)
        downloaded = catalog.get("total_downloaded", 0)
        repos_count = catalog.get("repos_with_altium_files", 0)
        
        lines.append("📦 <b>وضعیت کلی ریپوها:</b>")
        lines.append(f"   • فایل‌های Altium شناسایی شده: {total_files:,}")
        lines.append(f"   • فایل‌های دانلود شده: {downloaded}")
        lines.append(f"   • ریپوها: {repos_count}")
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
