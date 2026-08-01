#!/usr/bin/env python3
"""
Ultra Librarian Component Fetcher
Fetches component data and BXL files from Ultra Librarian API.
"""

import requests
import json
import os
import time
import logging
import base64
from datetime import datetime

logger = logging.getLogger(__name__)

ULTRA_LIB_API = "https://www.ultralibrarian.com/api"


def search_components(api_key, keyword, page=1, page_size=50):
    """Search Ultra Librarian for components."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "searchTerm": keyword,
        "pageNumber": page,
        "pageSize": page_size,
        "sortBy": "relevance",
    }
    
    try:
        response = requests.post(
            f"{ULTRA_LIB_API}/components/search",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        
        return {
            "total": data.get("totalCount", 0),
            "components": data.get("components", []),
        }
    except Exception as e:
        logger.error(f"Search error for '{keyword}': {e}")
        return {"total": 0, "components": []}


def download_bxl(api_key, component_id, output_dir):
    """Download BXL file for a component."""
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    
    try:
        response = requests.get(
            f"{ULTRA_LIB_API}/components/{component_id}/download/bxl",
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()
        
        # Save BXL file
        filename = f"{component_id}.bxl"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "wb") as f:
            f.write(response.content)
        
        return filepath
    except Exception as e:
        logger.error(f"Download error for {component_id}: {e}")
        return None


def download_altium(api_key, component_id, output_dir):
    """Download Altium format files for a component."""
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    
    try:
        response = requests.get(
            f"{ULTRA_LIB_API}/components/{component_id}/download/altium",
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()
        
        # Save ZIP file
        filename = f"{component_id}_altium.zip"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "wb") as f:
            f.write(response.content)
        
        return filepath
    except Exception as e:
        logger.error(f"Altium download error for {component_id}: {e}")
        return None


def parse_component(comp_data, category_name):
    """Parse Ultra Librarian component data."""
    return {
        "mpn": comp_data.get("mpn", ""),
        "manufacturer": comp_data.get("manufacturer", ""),
        "description": comp_data.get("description", ""),
        "category": category_name,
        "package": comp_data.get("package", ""),
        "ultra_lib_id": comp_data.get("id", ""),
        "ultra_lib_url": comp_data.get("url", ""),
        "fetched_at": datetime.utcnow().isoformat(),
    }


def run(config, output_dir="data"):
    """Main fetch function for Ultra Librarian."""
    logger.info("=" * 50)
    logger.info("Starting Ultra Librarian component fetch")
    logger.info("=" * 50)
    
    ul_config = config.get("ultra_librarian", {})
    api_key = ul_config.get("api_key", "")
    
    if not api_key:
        logger.warning("Ultra Librarian API key not configured. Skipping.")
        logger.warning("Get your free API key at: https://www.ultralibrarian.com")
        return {"total": 0, "categories": {}}
    
    os.makedirs(output_dir, exist_ok=True)
    categories = ul_config.get("categories", [])
    
    all_components = {}
    stats = {"total": 0, "categories": {}}
    
    for category in categories:
        name = category["name"]
        keyword = category["keyword"]
        
        logger.info(f"Fetching category: {name} (keyword: {keyword})")
        
        result = search_components(api_key, keyword)
        components = []
        
        for comp_data in result["components"]:
            comp = parse_component(comp_data, name)
            
            # Try to download Altium files
            altium_dir = os.path.join(output_dir, "altium_downloads", name)
            os.makedirs(altium_dir, exist_ok=True)
            
            altium_path = download_altium(api_key, comp_data.get("id"), altium_dir)
            if altium_path:
                comp["altium_file"] = altium_path
            
            components.append(comp)
            time.sleep(0.5)  # Rate limiting
        
        all_components[name] = components
        stats["categories"][name] = len(components)
        stats["total"] += len(components)
        
        # Save category file
        filepath = os.path.join(output_dir, "categories", f"ul_{name}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(components, f, ensure_ascii=False, indent=2)
    
    # Save combined file
    combined_path = os.path.join(output_dir, "ultra_librarian_components.json")
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(all_components, f, ensure_ascii=False, indent=2)
    
    stats["timestamp"] = datetime.utcnow().isoformat()
    logger.info(f"Total Ultra Librarian components: {stats['total']}")
    
    return stats


if __name__ == "__main__":
    import yaml
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    run(config)
