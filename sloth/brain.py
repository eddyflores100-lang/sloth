"""sloth.brain — the 1B-parameter brain, asleep on your own CPU.

Gemma 3 1B-it (open weights, Q4_K_M GGUF) served by llama.cpp
`llama-server` with an OpenAI-compatible API on 127.0.0.1:8750.

Ground rules:
  * The brain is ADVISORY. It classifies, summarises and drafts.
  * It never touches the filesystem, your mailbox or the network.
  * If the server is down, every chore degrades to its deterministic
    path and the receipt says so. A sloth never falls off the branch.
"""

from __future__ import annotations

import json
import os
import time
import re
import urllib.request

BASE_URL = os.environ.get("SLOTH_BRAIN_URL", "http://127.0.0.1:8750")
MODEL_NAME = "gemma-3-1b-it (local, llama.cpp)"

SYSTEM = (
    "You are SLOTH, a careful overnight helper. You classify, summarise and "
    "draft. You never ask to perform actions, never invent facts, and you "
    "always answer in the exact format requested. Be brief."
)


def _post(path: str, payload: dict, timeout: int = 120) -> dict | None:
    try:
        req = urllib.request.Request(
            BASE_URL + path,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except Exception:
        return None


def awake() -> bool:
    """Health probe — cheap, no tokens spent."""
    try:
        with urllib.request.urlopen(BASE_URL + "/health", timeout=5) as r:
            return json.load(r).get("status") == "ok"
    except Exception:
        return False


def chat(prompt: str, max_tokens: int = 220, temperature: float = 0.1) -> str | None:
    """One completion. Returns None when the brain is unreachable."""
    data = _post("/v1/chat/completions", {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    })
    if not data or "choices" not in data:
        return None
    return data["choices"][0]["message"]["content"].strip()


_PLURAL_FIX = {"newsletters": "newsletter", "notifications": "notification",
               "humans": "human", "personal": "human", "people": "human",
               "conversation": "human", "real": "human"}


def _parse_labels(out: str, labels: list[str]) -> dict[str, str]:
    """Tolerant parse of `<id>: <label>` lines (1B models drift a lot)."""
    labset = set(labels)
    result: dict[str, str] = {}
    for line in out.splitlines():
        m = re.search(r"([A-Za-z0-9_\-]+)\s*[:\-–]\s*([A-Za-z]+)", line)
        if not m:
            continue
        iid, lab = m.group(1).strip().lstrip("-"), m.group(2).strip().lower()
        lab = _PLURAL_FIX.get(lab, lab)
        if iid and lab in labset:
            result[iid] = lab
    return result


def classify_batch(items: list[tuple[str, str]], labels: list[str],
                   chunk: int = 8) -> dict[str, str] | None:
    """Classify (id, short_text) pairs into one of `labels`.

    Chunked so a 1B brain on 2 CPU cores can finish each chunk well
    inside the HTTP timeout. Returns {id: label}; items the brain could
    not confidently classify are simply absent (fail-closed: callers
    count them as 'unclassified', never as 'human').
    """
    if not items:
        return {}
    merged: dict[str, str] = {}
    ok_chunks = 0
    few_shot = (
        "You are labeling emails. Labels allowed: newsletter, notification, human.\n"
        "newsletter = bulk mail nobody personally wrote (marketing, digests, job boards)\n"
        "notification = automated alerts from a system the user follows\n"
        "human = written by a real person for this user\n\n"
        "Example:\n"
        "- ex1: from:shop.com subject:50% OFF everything\n"
        "- ex2: from:ci-bot@corp.com subject:Build #402 failed\n"
        "- ex3: from:mom@gmail.com subject:call me later\n"
        "Answers:\n"
        "- ex1: newsletter\n"
        "- ex2: notification\n"
        "- ex3: human\n\n"
        "Now answer these the same way:\n"
    )
    for start in range(0, len(items), chunk):
        part = items[start:start + chunk]
        listing = "\n".join(f"- {iid}: {txt[:140]}" for iid, txt in part)
        prompt = few_shot + listing
        out = chat(prompt, max_tokens=12 * len(part) + 40)
        if out is None:  # one retry: a 1B brain on a busy CPU does stall
            time.sleep(3)
            out = chat(prompt, max_tokens=12 * len(part) + 40)
        if out is None:
            continue
        parsed = _parse_labels(out, labels)
        if parsed:
            ok_chunks += 1
            merged.update(parsed)
    return merged if ok_chunks else None


def summarise(text: str, max_tokens: int = 180) -> str | None:
    return chat(f"Summarise in 2 short sentences:\n\n{text}", max_tokens=max_tokens)


def one_liner(text: str, max_tokens: int = 60) -> str | None:
    return chat(
        "Rewrite this headline as one plain-English sentence (max 22 words). "
        "Do NOT invent details that are not in the headline. If you are not "
        "sure what it refers to, just simplify the headline literally.\n\n"
        f"Headline: {text}",
        max_tokens=max_tokens)
