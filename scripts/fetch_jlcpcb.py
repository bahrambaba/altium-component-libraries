#!/usr/bin/env python3
"""
JLCPCB/LCSC Component Fetcher
Fetches component data from JLCPCB/LCSC API and saves to JSON.
"""

import requests
import json
import os
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# LCSC API endpoints (try multiple)
LCSC_SEARCH_URLS = [
    "https://wmsc.lcsc.com/ftps/wm/product/search",
    "https://wmsc.lcsc.com/wmsc/search/global",
    "https://wmsc.lcsc.com/ftps/wm/search/global",
]

# EasyEDA API (LCSC backend)
EASYEDA_SEARCH_URL = "https://easyeda.com/api/products/search"

# Headers to mimic browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.lcsc.com/",
    "Origin": "https://www.lcsc.com",
}


def search_components(keyword, page=1, page_size=100):
    """Search for components on LCSC with fallback endpoints."""
    params = {
        "keyword": keyword,
        "currentPage": page,
        "pageSize": page_size,
        "param": "",
        "sort": "",
    }
    
    # Try LCSC endpoints first
    for url in LCSC_SEARCH_URLS:
        try:
            response = requests.get(url, params=params, headers=HEADERS, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if "result" in data and data["result"]:
                result = data["result"]
                if "productSearchResultVO" in result:
                    result = result["productSearchResultVO"]
                return {
                    "total": result.get("total", 0),
                    "products": result.get("productList", []),
                    "page": page,
                    "page_size": page_size,
                }
        except Exception as e:
            logger.debug(f"LCSC endpoint {url} failed: {e}")
            continue
    
    # Fallback to EasyEDA
    try:
        response = requests.get(
            EASYEDA_SEARCH_URL,
            params={"keyword": keyword, "currPage": page, "pageSize": page_size},
            headers=HEADERS,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        
        if "result" in data:
            return {
                "total": data["result"].get("total", 0),
                "products": data["result"].get("productList", []),
                "page": page,
                "page_size": page_size,
            }
    except Exception as e:
        logger.debug(f"EasyEDA endpoint failed: {e}")
    
    return {"total": 0, "products": [], "page": page, "page_size": page_size}


def get_component_detail(product_code):
    """Get detailed component data."""
    detail_urls = [
        f"https://wmsc.lcsc.com/ftps/wm/product/detail?productCode={product_code}",
        f"https://wmsc.lcsc.com/wmsc/product/detail?productCode={product_code}",
    ]
    
    for url in detail_urls:
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if "result" in data and data["result"]:
                return data["result"]
        except Exception as e:
            logger.debug(f"Detail endpoint {url} failed: {e}")
            continue
    
    return None


def parse_component(product, category_name):
    """Parse a product from LCSC search into our format."""
    return {
        "mpn": product.get("productModel", ""),
        "lscs_code": product.get("productCode", ""),
        "manufacturer": product.get("brandNameEn", ""),
        "description": product.get("productDescEn", ""),
        "category": category_name,
        "package": product.get("encapName", ""),
        "price_usd": product.get("productPriceList", [{}])[0].get("productPrice", 0) if product.get("productPriceList") else 0,
        "stock": product.get("stockNumber", 0),
        "datasheet": product.get("dataManual", ""),
        "image_url": product.get("productImage", ""),
        "lcsc_url": f"https://www.lcsc.com/product-detail/{product.get('productCode', '')}.html",
        "parameters": {},
        "fetched_at": datetime.utcnow().isoformat(),
    }


def fetch_category(category, max_pages=5):
    """Fetch all components for a category."""
    keyword = category["keyword"]
    name = category["name"]
    page_size = category.get("page_size", 100)
    max_pages = category.get("max_pages", max_pages)
    
    all_components = []
    page = 1
    
    logger.info(f"Fetching category: {name} (keyword: {keyword})")
    
    while page <= max_pages:
        result = search_components(keyword, page=page, page_size=page_size)
        
        if not result["products"]:
            break
        
        for product in result["products"]:
            comp = parse_component(product, name)
            all_components.append(comp)
        
        logger.info(f"  Page {page}: {len(result['products'])} components (total: {result['total']})")
        
        if page * page_size >= result["total"]:
            break
        
        page += 1
        time.sleep(1)  # Rate limiting
    
    logger.info(f"  Total fetched for {name}: {len(all_components)}")
    return all_components


def run(config, output_dir="data"):
    """Main fetch function."""
    logger.info("=" * 50)
    logger.info("Starting JLCPCB/LCSC component fetch")
    logger.info("=" * 50)
    
    os.makedirs(output_dir, exist_ok=True)
    categories = config.get("jlpcb", {}).get("categories", [])
    
    all_components = {}
    stats = {"total": 0, "categories": {}}
    
    for category in categories:
        name = category["name"]
        components = fetch_category(category)
        all_components[name] = components
        stats["categories"][name] = len(components)
        stats["total"] += len(components)
    
    # Save to JSON files
    for name, components in all_components.items():
        filepath = os.path.join(output_dir, "categories", f"{name}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(components, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(components)} components to {filepath}")
    
    # Save combined file
    combined_path = os.path.join(output_dir, "jlpcb_components.json")
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(all_components, f, ensure_ascii=False, indent=2)
    
    # Save stats
    stats["timestamp"] = datetime.utcnow().isoformat()
    stats_path = os.path.join(output_dir, "jlpcb_stats.json")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Total components fetched: {stats['total']}")
    logger.info(f"Stats saved to {stats_path}")
    
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
