"""sloth.tools.tidy — the folder chore.

Sorts a messy directory (hello, ~/Downloads) into type buckets, with a
revert manifest for every move so `sloth undo` can put everything back.
Deterministic by design: the only role of the brain here is writing the
one-line summary for the receipt.
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime

BUCKETS = {
    "Images": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".heic", ".bmp"},
    "Documents": {".pdf", ".doc", ".docx", ".odt", ".txt", ".md", ".rtf", ".epub"},
    "Spreadsheets": {".xls", ".xlsx", ".ods", ".csv"},
    "Installers": {".deb", ".rpm", ".exe", ".msi", ".dmg", ".pkg", ".appimage"},
    "Archives": {".zip", ".tar", ".gz", ".tgz", ".rar", ".7z", ".bz2", ".xz"},
    "Media": {".mp3", ".mp4", ".mkv", ".wav", ".flac", ".webm", ".mov", ".avi"},
    "Code": {".py", ".js", ".ts", ".sh", ".json", ".yml", ".yaml", ".toml", ".html", ".css"},
}

IGNORE_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
MAX_MOVES = 400  # safety valve: a sloth never sprints


def bucket_for(name: str) -> str:
    ext = os.path.splitext(name)[1].lower()
    for bucket, exts in BUCKETS.items():
        if ext in exts:
            return bucket
    return "Other"


def tidy_dir(target: str, ledger, apply: bool = True) -> dict:
    """Sort loose files in `target` into buckets. Returns a receipt detail."""
    target = os.path.expanduser(target)
    if not os.path.isdir(target):
        return {"error": f"not a directory: {target}"}

    loose = [f for f in sorted(os.listdir(target))
             if os.path.isfile(os.path.join(target, f)) and f not in IGNORE_NAMES]
    moves: list[dict] = []
    for name in loose[:MAX_MOVES]:
        bucket = bucket_for(name)
        dst_dir = os.path.join(target, bucket)
        dst = os.path.join(dst_dir, name)
        if apply:
            os.makedirs(dst_dir, exist_ok=True)
            n, final = 1, dst
            while os.path.exists(final):
                root, ext = os.path.splitext(name)
                final = os.path.join(dst_dir, f"{root}-{n}{ext}")
                n += 1
            shutil.move(os.path.join(target, name), final)
            revert = {"file": os.path.basename(final),
                      "from": os.path.join(bucket, os.path.basename(final)),
                      "to": name}
        else:
            revert = None
        moves.append({"file": name, "bucket": bucket})
        ledger.record("tidy", f"moved '{name}' to {bucket}/",
                      detail={"file": name, "bucket": bucket},
                      revert=revert if apply else None)

    by_bucket: dict[str, int] = {}
    for m in moves:
        by_bucket[m["bucket"]] = by_bucket.get(m["bucket"], 0) + 1

    detail = {
        "dir": target,
        "dry_run": not apply,
        "moved": len(moves),
        "by_bucket": by_bucket,
        "skipped_over_limit": max(0, len(loose) - MAX_MOVES),
    }
    ledger.record("tidy", f"tidied {len(moves)} files into {len(by_bucket)} buckets"
                          f"{'' if apply else ' (dry run)'}", detail=detail)
    return detail


def undo_dir(target: str, ledger) -> dict:
    """Best-effort reverse of the last tidy pass, using revert manifests."""
    target = os.path.expanduser(target)
    restored = 0
    for entry in reversed(ledger.entries):
        rev = entry.get("revert") if entry.get("tool") == "tidy" else None
        if not rev:
            continue
        src = os.path.join(target, rev["from"])
        dst = os.path.join(target, rev["to"])
        if os.path.exists(src):
            shutil.move(src, dst)
            restored += 1
    ledger.record("tidy", f"undo: restored {restored} files to their original place",
                  detail={"dir": target, "restored": restored})
    return {"restored": restored}


def make_demo_files(target: str, count: int = 24) -> list[str]:
    """Generate a believable messy downloads folder for demos."""
    from pathlib import Path
    t = Path(target)
    t.mkdir(parents=True, exist_ok=True)
    samples = [
        ("invoice-march.pdf", b"%PDF-1.4 fake invoice"),
        ("screenshot-2026-10-19.png", b"\x89PNG fake"),
        ("vacation.jpg", b"\xff\xd8 fake jpeg"),
        ("setup-vscode.deb", b"fake deb"),
        ("data-export.csv", b"a,b,c\n1,2,3\n"),
        ("cat-video.mp4", b"fake mp4"),
        ("notes.md", b"# notes\n- call bank\n- renew passport\n"),
        ("backup.tar.gz", b"fake tar"),
        ("widget.py", b"print('hi')\n"),
        ("wallpaper.png", b"\x89PNG fake"),
        ("song-demo.mp3", b"fake mp3"),
        ("contract-v2.docx", b"fake docx"),
    ]
    made = []
    stamp = datetime.now().strftime("%Y%m%d")
    for i in range(count):
        name, blob = samples[i % len(samples)]
        stem, ext = os.path.splitext(name)
        fname = f"{stem}-{stamp}-{i:02d}{ext}"
        (t / fname).write_bytes(blob)
        made.append(fname)
    return made
