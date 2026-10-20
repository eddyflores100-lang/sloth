"""sloth.tools.brief — the morning brief chore.

Pulls the Hacker News front page (open API, plain GETs), then lets the
local brain turn each of the top stories into a one-line plain-English
summary. Falls back to raw titles when the brain is asleep.
"""

from __future__ import annotations

import json
import urllib.request

from .. import brain

HN_TOP = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{}.json"


def _get(url: str, timeout: int = 20):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.load(r)
    except Exception:
        return None


def fetch_top(n: int = 10) -> list[dict]:
    ids = _get(HN_TOP)
    if not ids:
        return []
    stories = []
    for iid in ids[:n]:
        item = _get(HN_ITEM.format(iid))
        if item and item.get("title"):
            stories.append({"id": iid, "title": item["title"],
                            "url": item.get("url", ""),
                            "points": item.get("score", 0),
                            "comments": item.get("descendants", 0)})
    return stories


def build(ledger, n: int = 10) -> dict:
    stories = fetch_top(n)
    if not stories:
        ledger.record("brief", "morning brief skipped (HN unreachable)",
                      detail={"stories": 0})
        return {"stories": 0}

    used_brain = False
    for s in stories:
        line = brain.one_liner(s["title"]) if brain.awake() else None
        if line:
            used_brain = True
            s["gist"] = line
        else:
            s["gist"] = None

    ledger.record(
        "brief", f"morning brief ready: {len(stories)} HN stories, "
                 f"{'summarised by local Gemma' if used_brain else 'titles only (brain asleep)'}",
        detail={"stories": len(stories),
                "brain": brain.MODEL_NAME if used_brain else "offline",
                "titles": [s["title"] for s in stories]})
    return {"stories": len(stories), "used_brain": used_brain,
            "items": [{k: s.get(k) for k in ("title", "url", "points", "comments", "gist")}
                      for s in stories]}
