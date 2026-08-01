#!/usr/bin/env python3
"""
GitHub Altium Library Aggregator
Searches and downloads REAL .SchLib/.PcbLib/.IntLib/.DbLib files from GitHub repos.
Also scrapes github.com/topics/altium-library for repo discovery.
"""

import requests
import json
import os
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"

# Pre-known repos with real Altium files
KNOWN_REPOS = [
    {"owner": "issus", "repo": "altium-library", "stars": 2418, "desc": "200K+ components with 3D models"},
    {"owner": "ximtech", "repo": "altium-library", "stars": 48, "desc": "Large database component library"},
    {"owner": "WurthElektronik", "repo": "Altium-Library", "stars": 70, "desc": "Wurth Elektronik official library"},
    {"owner": "chilaboard", "repo": "Altium-Library", "stars": 126, "desc": "4000+ IPC compliant components"},
    {"owner": "gsuberland", "repo": "altium_jlcpcb_libraries", "stars": 68, "desc": "JLCPCB parts for Altium"},
    {"owner": "aKaReZa75", "repo": "Altium-Library", "stars": 68, "desc": "Altium component library"},
    {"owner": "FMCHUB", "repo": "Lib_Altium", "stars": 46, "desc": "FMC hardware Altium library"},
    {"owner": "wavenumber-eng", "repo": "altium_monkey", "stars": 165, "desc": "Altium file generation tool"},
]

# File types to search for
ALTIUM_EXTS = [".SchLib", ".PcbLib", ".IntLib", ".DbLib"]

# GitHub search queries
SEARCH_QUERIES = [
    "altium+library",
    "altium+SchLib",
    "altium+PcbLib",
]

# GitHub topics to scrape
GITHUB_TOPICS = [
    "altium-library",
    "altium-designer",
    "altium",
    "altium-components",
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
                    "size_kb": r["size"],
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


def search_github_topics(topic, token=None, per_page=30):
    """Search GitHub topics for repos."""
    headers = {
        "Accept": "application/vnd.github.mercy-preview+json",
        "User-Agent": "altium-library-aggregator",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    params = {"q": topic, "per_page": per_page}

    try:
        resp = requests.get(f"{GITHUB_API}/search/repositories",
                          headers=headers, params=params, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            results = []
            for r in data.get("items", []):
                topics = r.get("topics", [])
                if any(t in topics for t in ["altium", "altium-library", "altium-designer", "altium-components"]):
                    results.append({
                        "owner": r["owner"]["login"],
                        "repo": r["name"],
                        "url": r["html_url"],
                        "stars": r["stargazers_count"],
                        "desc": r.get("description", "") or "",
                        "updated": r["updated_at"],
                        "size_kb": r["size"],
                        "clone_url": r["clone_url"],
                        "topics": topics,
                    })
            return results
        return []
    except Exception as e:
        logger.error(f"Topic search error: {e}")
        return []


def get_repo_file_tree(owner, repo, token=None):
    """Get file tree of a repo (recursive)."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "altium-library-aggregator",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    for branch in ["main", "master"]:
        try:
            resp = requests.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1",
                headers=headers, timeout=30
            )
            if resp.status_code == 200:
                return resp.json().get("tree", [])
        except Exception:
            continue
    return []


def find_altium_files(file_tree):
    """Find Altium-related files in a repo tree."""
    altium_files = []
    for item in file_tree:
        if item.get("type") != "blob":
            continue
        path = item["path"]
        for ext in ALTIUM_EXTS:
            if path.lower().endswith(ext.lower()):
                altium_files.append({
                    "path": path,
                    "type": ext,
                    "size_kb": round(item.get("size", 0) / 1024, 2),
                })
                break
    return altium_files


def download_file(owner, repo, path, token=None):
    """Download a single file from GitHub raw API."""
    headers = {
        "Accept": "application/vnd.github.v3.raw",
        "User-Agent": "altium-library-aggregator",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        resp = requests.get(
            f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{path}",
            headers=headers, timeout=60
        )
        if resp.status_code == 200:
            return resp.content
    except Exception:
        pass
    return None


def aggregate_repos(output_dir, token=None, max_repos=30, max_files_per_repo=50):
    """Main aggregation function - downloads REAL .SchLib/.PcbLib files."""
    logger.info("=" * 60)
    logger.info("Starting GitHub Altium Library Aggregation")
    logger.info("=" * 60)

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "external"), exist_ok=True)

    all_repos = {}

    # Step 1: Add known repos
    logger.info("\n📡 Step 1: Adding known Altium library repos...")
    for kr in KNOWN_REPOS:
        key = f"{kr['owner']}/{kr['repo']}"
        if key not in all_repos:
            all_repos[key] = {
                "owner": kr["owner"],
                "repo": kr["repo"],
                "url": f"https://github.com/{key}",
                "stars": kr["stars"],
                "desc": kr["desc"],
                "clone_url": f"https://github.com/{key}.git",
            }
            logger.info(f"  Added: {key} ({kr['stars']} stars)")

    # Step 2: Search GitHub
    logger.info("\n📡 Step 2: Searching GitHub for Altium library repos...")
    for query in SEARCH_QUERIES:
        logger.info(f"  Searching: {query}")
        results = search_github_repos(query, token, per_page=20)
        for r in results:
            key = f"{r['owner']}/{r['repo']}"
            if key not in all_repos:
                all_repos[key] = r
                logger.info(f"  Found: {key} ({r['stars']} stars)")
        time.sleep(1)

    # Step 3: Search GitHub topics
    logger.info("\n📡 Step 3: Searching GitHub topics...")
    for topic in GITHUB_TOPICS:
        logger.info(f"  Searching topic: {topic}")
        results = search_github_topics(topic, token, per_page=30)
        for r in results:
            key = f"{r['owner']}/{r['repo']}"
            if key not in all_repos:
                all_repos[key] = r
                logger.info(f"  Found via topic: {key} ({r['stars']} stars)")
        time.sleep(1)

    logger.info(f"\n  Total unique repos found: {len(all_repos)}")

    # Step 4: Scan repos and download real Altium files
    logger.info("\n📂 Step 4: Scanning repos and downloading REAL .SchLib/.PcbLib files...")

    repo_catalog = []
    total_altium_files = 0
    total_downloaded = 0
    repos_scanned = 0

    repos_sorted = sorted(all_repos.values(), key=lambda x: x["stars"], reverse=True)

    for repo_info in repos_sorted[:max_repos]:
        key = f"{repo_info['owner']}/{repo_info['repo']}"
        logger.info(f"  Scanning: {key}")

        tree = get_repo_file_tree(repo_info["owner"], repo_info["repo"], token)
        if not tree:
            logger.info(f"    No file tree, skipping")
            continue

        altium_files = find_altium_files(tree)
        if not altium_files:
            logger.info(f"    No Altium files found")
            repos_scanned += 1
            continue

        total_altium_files += len(altium_files)
        logger.info(f"    Found {len(altium_files)} REAL Altium files")

        # Save file list to catalog
        repo_entry = {
            "repo": key,
            "url": repo_info["url"],
            "stars": repo_info["stars"],
            "desc": repo_info["desc"],
            "altium_file_count": len(altium_files),
            "files": altium_files[:max_files_per_repo],
        }
        repo_catalog.append(repo_entry)

        # Download REAL .SchLib/.PcbLib files
        safe_name = key.replace("/", "_")
        repo_dir = os.path.join(output_dir, "external", safe_name)
        os.makedirs(repo_dir, exist_ok=True)

        download_count = 0
        for af in altium_files[:max_files_per_repo]:
            # Preserve directory structure
            rel_path = af["path"]
            filepath = os.path.join(repo_dir, os.path.basename(rel_path))
            
            if os.path.exists(filepath):
                download_count += 1
                continue

            content = download_file(
                repo_info["owner"], repo_info["repo"],
                af["path"], token
            )
            if content:
                with open(filepath, "wb") as f:
                    f.write(content)
                total_downloaded += 1
                download_count += 1
        
        logger.info(f"    Downloaded {download_count} files")
        repos_scanned += 1
        time.sleep(0.5)

    # Step 5: Save catalog
    catalog = {
        "scan_time": datetime.utcnow().isoformat(),
        "repos_found": len(all_repos),
        "repos_scanned": repos_scanned,
        "repos_with_altium_files": len(repo_catalog),
        "total_altium_files": total_altium_files,
        "total_downloaded": total_downloaded,
        "repos": sorted(repo_catalog, key=lambda r: r["altium_file_count"], reverse=True),
    }

    catalog_path = os.path.join(output_dir, "repo_catalog.json")
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    logger.info(f"\n{'=' * 60}")
    logger.info(f"AGGREGATION COMPLETE")
    logger.info(f"  Repos found: {len(all_repos)}")
    logger.info(f"  Repos scanned: {repos_scanned}")
    logger.info(f"  Repos with Altium files: {len(repo_catalog)}")
    logger.info(f"  Total Altium files found: {total_altium_files}")
    logger.info(f"  Total files downloaded: {total_downloaded}")
    logger.info(f" saves dasd: {catalog_path}")
    logger.info(f"{'=' * 60}")

    return {
        "repos_found": len(all_repos),
        "repos_scanned": repos_scanned,
        "repos_with_altium_files": len(repo_catalog),
        "total_altium_files": total_altium_files,
        "total_downloaded": total_downloaded,
    }


def run(config, data_dir):
    """Entry point for update_all.py"""
    token = os.environ.get("GITHUB_TOKEN", "")
    output_dir = os.path.join(data_dir, "external_catalog")
    max_repos = config.get("aggregator", {}).get("max_repos", 30)
    max_files = config.get("aggregator", {}).get("max_files_per_repo", 50)

    stats = aggregate_repos(output_dir, token, max_repos, max_files)
    return {
        "total": stats["total_altium_files"],
        "downloaded": stats["total_downloaded"],
        "repos": stats["repos_with_altium_files"],
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                       format="%(asctime)s [%(levelname)s] %(message)s")
    token = os.environ.get("GITHUB_TOKEN", "")
    aggregate_repos("./data/external_catalog", token)
