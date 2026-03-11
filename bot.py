"""
Discord RSS Alert Bot
=====================
Monitors one or more RSS feeds and posts new items to a Discord channel
via webhook. Tracks already-seen items so you never get duplicates.

Setup:
    1. Copy config.example.json → config.json
    2. Fill in your Discord webhook URL(s) and RSS feed URLs
    3. Run: python bot.py
    4. Optional: schedule with cron (e.g. every 15 minutes)

No Discord bot token needed — uses webhooks only.
"""

import json
import os
import time
import hashlib
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError
import xml.etree.ElementTree as ET


CONFIG_FILE = Path(__file__).parent / "config.json"
SEEN_FILE   = Path(__file__).parent / ".seen_items.json"
HEADERS     = {"User-Agent": "DiscordRSSBot/1.0"}


# ── Config ──────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if not CONFIG_FILE.exists():
        print("[ERROR] config.json not found. Copy config.example.json and fill it in.")
        raise SystemExit(1)
    with open(CONFIG_FILE) as f:
        return json.load(f)


# ── Seen-item tracking ───────────────────────────────────────────────────────

def load_seen() -> set:
    if SEEN_FILE.exists():
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()


def save_seen(seen: set) -> None:
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


def item_id(title: str, link: str) -> str:
    return hashlib.md5(f"{title}{link}".encode()).hexdigest()


# ── RSS Parsing ──────────────────────────────────────────────────────────────

def fetch_feed(url: str) -> list[dict]:
    """Fetch and parse an RSS 2.0 or Atom feed."""
    req = Request(url, headers=HEADERS)
    try:
        with urlopen(req, timeout=15) as resp:
            raw = resp.read()
    except URLError as e:
        print(f"[WARN] Could not fetch {url}: {e}")
        return []

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        print(f"[WARN] Could not parse XML from {url}: {e}")
        return []

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items = []

    # RSS 2.0
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link  = (item.findtext("link")  or "").strip()
        desc  = (item.findtext("description") or "").strip()[:300]
        pub   = (item.findtext("pubDate") or "").strip()
        if title or link:
            items.append({"title": title, "link": link, "description": desc, "published": pub})

    # Atom
    if not items:
        for entry in root.findall("atom:entry", ns):
            title = (entry.findtext("atom:title", namespaces=ns) or "").strip()
            link_el = entry.find("atom:link", ns)
            link  = (link_el.get("href", "") if link_el is not None else "").strip()
            desc  = (entry.findtext("atom:summary", namespaces=ns) or "").strip()[:300]
            pub   = (entry.findtext("atom:updated", namespaces=ns) or "").strip()
            if title or link:
                items.append({"title": title, "link": link, "description": desc, "published": pub})

    return items


# ── Discord Webhook ──────────────────────────────────────────────────────────

def send_to_discord(webhook_url: str, item: dict, feed_name: str) -> bool:
    """Send a single RSS item as a Discord embed."""
    embed = {
        "title":       item["title"][:256],
        "url":         item["link"],
        "description": item["description"] or "No description available.",
        "color":       0x5865F2,  # Discord blurple
        "footer":      {"text": f"{feed_name} • {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"},
    }

    payload = json.dumps({"embeds": [embed]}).encode("utf-8")
    req = Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "DiscordRSSBot/1.0"},
        method="POST",
    )

    try:
        with urlopen(req, timeout=10) as resp:
            return resp.status in (200, 204)
    except URLError as e:
        print(f"[WARN] Webhook failed: {e}")
        return False


# ── Main Loop ────────────────────────────────────────────────────────────────

def run():
    config  = load_config()
    seen    = load_seen()
    feeds   = config.get("feeds", [])
    webhook = config.get("webhook_url", "")
    max_new = config.get("max_new_per_run", 5)

    if not webhook:
        print("[ERROR] No webhook_url in config.json")
        raise SystemExit(1)

    print(f"[*] Checking {len(feeds)} feed(s)... ({datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')})")
    total_sent = 0

    for feed in feeds:
        name = feed.get("name", feed["url"])
        print(f"  → {name}")
        items = fetch_feed(feed["url"])
        sent  = 0

        for item in items:
            if sent >= max_new:
                break
            uid = item_id(item["title"], item["link"])
            if uid in seen:
                continue

            ok = send_to_discord(webhook, item, name)
            if ok:
                seen.add(uid)
                sent += 1
                total_sent += 1
                time.sleep(1)  # respect Discord rate limits

        print(f"     Sent {sent} new item(s)")

    save_seen(seen)
    print(f"[OK] Done. {total_sent} total new item(s) posted.\n")


if __name__ == "__main__":
    run()
