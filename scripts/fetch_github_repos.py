#!/usr/bin/env python3
"""
GitHub Altium Library Aggregator
Searches and downloads Altium component libraries from GitHub repos.
"""

import requests
import json
import os
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"

# Known Altium library repos (will be expanded by search)
KNOWN_REPOS = [
    {"owner": "issus", "repo": "altium-library", "stars": 2415, "desc": "Large community Altium library"},
    {"owner": "gsuberland", "repo": "altium_jlcpcb_libraries", "stars": 68, "desc": "JLCPCB parts for Altium"},
    {"owner": "wavenumber-eng", "repo": "altium_monkey", "stars": 164, "desc": "Altium file generation tool"},
    {"owner": "Xilinx", "repo": "altium-library", "stars": 0, "desc": "Xilinx components for Altium"},
    {"owner": "niosii", "repo": "altium-library", "stars": 0, "desc": "Altium components"},
]

# File types to search for
ALTium_FILE_TYPES = [".SchLib", ".PcbLib", ".IntLib", ".DbLib", ".SchPrj", ".PcbPrj"]

# GitHub search query for finding repos
SEARCH_QUERIES = [
    "altium+library",
    "altium+components",
    "altium+SchLib",
    "altium+PcbLib",
    "jlcpcb+altium",
    "altium+footprint",
    "altium+symbol",
    "altium+IntLib",
    "altium+component+library",
    "altium+designer+library",
]


def search_github_repos(query, token=None, per_page=30, page=1):
    """Search GitHub for repos matching query."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "altium-library-aggregator",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    params = {
        "q": f"{query} in:name,description,readme",
        "sort": "stars",
        "order": "desc",
        "per_page": per_page,
        "page": page,
    }

    try:
        resp = requests.get(f"{GITHUB_API}/search/repositories",
                          headers=headers, params=params, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            return [
                {
                    "owner": r["owner"]["login"],
                    "repo": r["name"],
                    "url": r["html_url"],
                    "stars": r["stargazers_count"],
                    "desc": r.get("description", "") or "",
                    "updated": r["updated_at"],
                    "size": r["size"],  # KB
                    "clone_url": r["clone_url"],
                }
                for r in data.get("items", [])
            ]
        else:
            logger.warning(f"Search failed for '{query}': {resp.status_code}")
            return []
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []


def get_repo_file_tree(owner, repo, token=None):
    """Get file tree of a repo (recursive)."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "altium-library-aggregator",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        resp = requests.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/main?recursive=1",
            headers=headers, timeout=30
        )
        if resp.status_code == 200:
            return resp.json().get("tree", [])
        # Try master branch
        resp = requests.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/master?recursive=1",
            headers=headers, timeout=30
        )
        if resp.status_code == 200:
            return resp.json().get("tree", [])
    except Exception:
        pass
    return []


def find_altium_files(file_tree, repo_info):
    """Find Altium-related files in a repo tree."""
    altium_files = []
    for item in file_tree:
        if item["type"] != "blob":
            continue
        path = item["path"]
        for ext in [".SchLib", ".PcbLib", ".IntLib", ".DbLib"]:
            if path.endswith(ext):
                size_kb = item.get("size", 0) / 1024
                altium_files.append({
                    "path": path,
                    "type": ext,
                    "size_kb": round(size_kb, 2),
                    "url": f"{repo_info['url']}/blob/main/{path}"
                            if "main" in [b.get("path") for b in file_tree if b.get("type") == "tree"]
                            else f"{repo_info['url']}/blob/master/{path}",
                })
    return altium_files


def download_file(owner, repo, path, token=None):
    """Download a single file from GitHub."""
    headers = {
        "Accept": "application/vnd.github.v3.raw",
        "User-Agent": "altium-library-aggregator",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        resp = requests.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}",
            headers=headers, timeout=60
        )
        if resp.status_code == 200:
            return resp.content
    except Exception:
        pass
    return None


def aggregate_repos(output_dir, token=None, max_repos=50):
    """Main aggregation function."""
    logger.info("=" * 60)
    logger.info("Starting GitHub Altium Library Aggregation")
    logger.info("=" * 60)

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "external"), exist_ok=True)

    all_repos = {}

    # Step 1: Search for repos
    logger.info("\n📡 Step 1: Searching GitHub for Altium library repos...")

    for query in SEARCH_QUERIES:
        logger.info(f"  Searching: {query}")
        results = search_github_repos(query, token, per_page=30)
        for r in results:
            key = f"{r['owner']}/{r['repo']}"
            if key not in all_repos:
                all_repos[key] = r
                logger.info(f"    Found: {key} ({r['stars']} stars)")
        time.sleep(2)  # Rate limit

    # Add known repos
    for kr in KNOWN_REPOS:
        key = f"{kr['owner']}/{kr['repo']}"
        if key not in all_repos:
            all_repos[key] = {
                "owner": kr["owner"],
                "repo": kr["repo"],
                "url": f"https://github.com/{key}",
                "stars": kr["stars"],
                "desc": kr["desc"],
                "updated": "",
                "size": 0,
                "clone_url": f"https://github.com/{key}.git",
            }

    logger.info(f"\n  Total unique repos found: {len(all_repos)}")

    # Step 2: Scan repos for Altium files
    logger.info("\n📂 Step 2: Scanning repos for Altium files...")

    repo_catalog = []
    total_altium_files = 0
    repos_scanned = 0

    for key, repo_info in sorted(all_repos.items(),
                                  key=lambda x: x[1]["stars"], reverse=True):
        if repos_scanned >= max_repos:
            logger.info(f"  Reached max repos limit ({max_repos})")
            break

        logger.info(f"  Scanning: {key}")
        tree = get_repo_file_tree(repo_info["owner"], repo_info["repo"], token)
        if not tree:
            logger.info(f"    No file tree found, skipping")
            continue

        altium_files = find_altium_files(tree, repo_info)
        if altium_files:
            total_altium_files += len(altium_files)
            logger.info(f"    Found {len(altium_files)} Altium files")

            repo_entry = {
                "repo": key,
                "url": repo_info["url"],
                "stars": repo_info["stars"],
                "desc": repo_info["desc"],
                "altium_file_count": len(altium_files),
                "files": altium_files,
            }
            repo_catalog.append(repo_entry)

            # Download files to external dir
            safe_name = key.replace("/", "_")
            repo_dir = os.path.join(output_dir, "external", safe_name)
            os.makedirs(repo_dir, exist_ok=True)

            for af in altium_files:
                content = download_file(
                    repo_info["owner"], repo_info["repo"],
                    af["path"], token
                )
                if content:
                    filename = os.path.basename(af["path"])
                    filepath = os.path.join(repo_dir, filename)
                    with open(filepath, "wb") as f:
                        f.write(content)
                    logger.info(f"    Downloaded: {filename} ({len(content)} bytes)")

            time.sleep(1)
        else:
            logger.info(f"    No Altium files found")

        repos_scanned += 1

    # Step 3: Save catalog
    catalog_path = os.path.join(output_dir, "repo_catalog.json")
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump({
            "scan_time": datetime.utcnow().isoformat(),
            "repos_found": len(all_repos),
            "repos_scanned": repos_scanned,
            "repos_with_altium_files": len(repo_catalog),
            "total_altium_files": total_altium_files,
            "repos": repo_catalog,
        }, f, ensure_ascii=False, indent=2)

    logger.info(f"\n{'=' * 60}")
    logger.info(f"AGGREGATION COMPLETE")
    logger.info(f"  Repos found: {len(all_repos)}")
    logger.info(f"  Repos scanned: {repos_scanned}")
    logger.info(f"  Repos with Altium files: {len(repo_catalog)}")
    logger.info(f"  Total Altium files: {total_altium_files}")
    logger.info(f"  Catalog saved: {catalog_path}")
    logger.info(f"{'=' * 60}")

    return {
        "repos_found": len(all_repos),
        "repos_scanned": repos_scanned,
        "repos_with_altium_files": len(repo_catalog),
        "total_altium_files": total_altium_files,
        "catalog": repo_catalog,
    }


def run(config, data_dir):
    """Entry point for update_all.py"""
    token = os.environ.get("GITHUB_TOKEN", "")
    output_dir = os.path.join(data_dir, "external_catalog")
    max_repos = config.get("aggregator", {}).get("max_repos", 50)

    stats = aggregate_repos(output_dir, token, max_repos)
    return {"total": stats["total_altium_files"], "repos": stats["repos_with_altium_files"]}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                       format="%(asctime)s [%(levelname)s] %(message)s")
    token = os.environ.get("GITHUB_TOKEN", "")
    aggregate_repos("./data/external_catalog", token)
