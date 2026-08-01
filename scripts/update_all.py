#!/usr/bin/env python3
"""
Altium Component Libraries - Master Update Script
Runs all fetchers, aggregators, generates Altium libraries, and sends report.
"""

import os
import sys
import yaml
import json
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fetch_jlcpcb import run as fetch_jlcpcb
from fetch_github_repos import run as fetch_github
from generate_altium_libs import run as generate_libs
from send_report import run as send_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/update.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_summary(stats_list, output_path):
    summary = {
        "update_time": datetime.utcnow().isoformat(),
        "sources": [],
        "total_fetched": 0,
        "total_generated": 0,
    }

    for s in stats_list:
        source = s.get("source", "Unknown")
        if "error" in s:
            summary["sources"].append({"source": source, "error": s["error"]})
        else:
            total = s.get("total", 0)
            generated = s.get("generated", 0)
            summary["sources"].append({
                "source": source,
                "total": total,
                "generated": generated,
                "details": {k: v for k, v in s.items()
                           if k not in ("source", "total", "generated", "error")}
            })
            summary["total_fetched"] += total
            summary["total_generated"] += generated

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return summary


def main():
    logger.info("=" * 60)
    logger.info("ALTium COMPONENT LIBRARIES - UPDATE STARTED")
    logger.info(f"Time: {datetime.utcnow().isoformat()}")
    logger.info("=" * 60)

    config = load_config()

    base_dir = os.path.dirname(os.path.dirname(__file__))
    data_dir = os.path.join(base_dir, "data")
    lib_dir = os.path.join(base_dir, "libraries")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(os.path.join(data_dir, "categories"), exist_ok=True)

    stats_list = []

    # Step 1: Fetch from JLCPCB/LCSC (curated database)
    if config.get("jlpcb", {}).get("enabled", False):
        logger.info("\n📡 Step 1: Fetching from JLCPCB/LCSC...")
        try:
            stats = fetch_jlcpcb(config, data_dir)
            stats_list.append({"source": "JLCPCB/LCSC", **stats})
        except Exception as e:
            logger.error(f"JLCPCB fetch failed: {e}")
            stats_list.append({"source": "JLCPCB/LCSC", "error": str(e)})
    else:
        logger.info("Step 1: JLCPCB disabled, skipping")

    # Step 2: Aggregate from GitHub repos
    if config.get("aggregator", {}).get("enabled", True):
        logger.info("\n📡 Step 2: Aggregating from GitHub repos...")
        try:
            stats = fetch_github(config, data_dir)
            stats_list.append({"source": "GitHub Aggregator", **stats})
        except Exception as e:
            logger.error(f"GitHub aggregation failed: {e}")
            stats_list.append({"source": "GitHub Aggregator", "error": str(e)})
    else:
        logger.info("Step 2: GitHub aggregator disabled, skipping")

    # Step 3: Generate Altium libraries
    logger.info("\n🔧 Step 3: Generating Altium libraries...")
    try:
        stats = generate_libs(config, data_dir, lib_dir)
        stats_list.append({"source": "Altium Generator", **stats})
    except Exception as e:
        logger.error(f"Library generation failed: {e}")
        stats_list.append({"source": "Altium Generator", "error": str(e)})

    # Step 4: Create summary
    summary = create_summary(stats_list, os.path.join(data_dir, "update_summary.json"))

    # Step 5: Send daily report to Telegram
    logger.info("\n📤 Step 5: Sending daily report to Telegram...")
    try:
        send_report(config, data_dir)
    except Exception as e:
        logger.error(f"Report sending failed: {e}")

    logger.info("\n" + "=" * 60)
    logger.info("UPDATE COMPLETED")
    logger.info(f"Total components fetched: {summary['total_fetched']}")
    logger.info(f"Total libraries generated: {summary['total_generated']}")
    logger.info("=" * 60)

    return summary


if __name__ == "__main__":
    main()
