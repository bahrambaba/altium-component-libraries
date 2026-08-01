#!/usr/bin/env python3
"""
Altium Component Libraries - Master Update Script
Runs all fetchers and generates Altium libraries.
"""

import os
import sys
import yaml
import json
import logging
from datetime import datetime

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fetch_jlcpcb import run as fetch_jlcpcb
from fetch_ultra_librarian import run as fetch_ultra_librarian
from generate_altium_libs import run as generate_libs

# Setup logging
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
    """Load configuration file."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_summary(stats_list, output_path):
    """Create a summary report of the update."""
    summary = {
        "update_time": datetime.utcnow().isoformat(),
        "sources": stats_list,
        "total_fetched": sum(s.get("total", 0) for s in stats_list),
        "total_generated": sum(s.get("generated", 0) for s in stats_list),
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    return summary


def main():
    """Main update function."""
    logger.info("=" * 60)
    logger.info("ALTium COMPONENT LIBRARIES - UPDATE STARTED")
    logger.info(f"Time: {datetime.utcnow().isoformat()}")
    logger.info("=" * 60)
    
    # Load config
    config = load_config()
    
    # Ensure data directory exists
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    lib_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "libraries")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(os.path.join(data_dir, "categories"), exist_ok=True)
    
    stats_list = []
    
    # Step 1: Fetch from JLCPCB/LCSC
    if config.get("jlpcb", {}).get("enabled", False):
        logger.info("\n📡 Step 1: Fetching from JLCPCB/LCSC...")
        try:
            stats = fetch_jlcpcb(config, data_dir)
            stats_list.append({"source": "JLCPCB/LCSC", **stats})
        except Exception as e:
            logger.error(f"JLCPCB fetch failed: {e}")
            stats_list.append({"source": "JLCPCB/LCSC", "error": str(e)})
    else:
        logger.info("⏭️  JLCPCB disabled in config, skipping")
    
    # Step 2: Fetch from Ultra Librarian
    if config.get("ultra_librarian", {}).get("enabled", False):
        logger.info("\n📡 Step 2: Fetching from Ultra Librarian...")
        try:
            stats = fetch_ultra_librarian(config, data_dir)
            stats_list.append({"source": "Ultra Librarian", **stats})
        except Exception as e:
            logger.error(f"Ultra Librarian fetch failed: {e}")
            stats_list.append({"source": "Ultra Librarian", "error": str(e)})
    else:
        logger.info("⏭️  Ultra Librarian disabled or no API key, skipping")
    
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
    
    logger.info("\n" + "=" * 60)
    logger.info("UPDATE COMPLETED")
    logger.info(f"Total components fetched: {summary['total_fetched']}")
    logger.info(f"Total libraries generated: {summary['total_generated']}")
    logger.info("=" * 60)
    
    return summary


if __name__ == "__main__":
    main()
