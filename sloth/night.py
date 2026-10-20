"""sloth.night — run the chores, then close the ledger and sign the receipt."""

from __future__ import annotations

import argparse
import os
import sys
import time

from . import brain
from .receipts import Ledger
from .policy import is_allowed
from .tools import tidy, inbox, brief

DEFAULT_DIR = os.environ.get("SLOTH_TARGET_DIR", os.path.expanduser("~/Downloads"))
RECEIPTS_DIR = os.environ.get("SLOTH_RECEIPTS",
                              os.path.join(os.path.dirname(__file__), "..", "receipts"))
KEY_PATH = os.environ.get("SLOTH_KEY",
                          os.path.join(os.path.dirname(__file__), "..", ".sloth_key"))


def nap(seconds: int = 20, why: str = "nap between chores") -> None:
    """A sloth is never in a hurry. Also polite to the CPU."""
    print(f"    [sloth naps {seconds}s — {why}]", flush=True)
    time.sleep(seconds)


def run_chores(ledger: Ledger, target_dir: str = DEFAULT_DIR,
               do_tidy: bool = True, do_inbox: bool = True, do_brief: bool = True,
               apply_labels: bool = False, apply_tidy: bool = True) -> dict:
    """Run every enabled chore in sloth order. Returns a summary dict."""
    print(f"  brain: {brain.MODEL_NAME} | awake: {brain.awake()}", flush=True)
    summary: dict = {}

    if do_tidy:
        if is_allowed("tidy", "sort files")[0]:
            print("  [1/3] tidying", target_dir, flush=True)
            summary["tidy"] = tidy.tidy_dir(target_dir, ledger, apply=apply_tidy)
        else:
            ledger.decline("tidy", "sort files", "policy refused")
        nap(15, "digesting a leaf")

    if do_inbox:
        print("  [2/3] triaging mailbox (read-only{})".format(
            ", labels on" if apply_labels else ""), flush=True)
        summary["inbox"] = inbox.triage(ledger, apply_labels=apply_labels)
        nap(15, "the inbox is a jungle; pace yourself")

    if do_brief:
        print("  [3/3] preparing the morning brief", flush=True)
        summary["brief"] = brief.build(ledger)

    return summary


def night(target_dir: str = DEFAULT_DIR, apply_labels: bool = False,
          apply_tidy: bool = True, until: str | None = None) -> str:
    """Full night: run chores, sign the receipt, render report. Returns path."""
    ledger = Ledger()
    print("SLOTH NIGHT SHIFT — starting. Everything will be on the receipt.", flush=True)
    summary = run_chores(ledger, target_dir=target_dir,
                         apply_labels=apply_labels, apply_tidy=apply_tidy)

    os.makedirs(RECEIPTS_DIR, exist_ok=True)
    rpath = os.path.join(RECEIPTS_DIR, f"{ledger.date}.json")
    sig = ledger.sign(KEY_PATH)
    meta = {
        "brain": brain.MODEL_NAME,
        "brain_url": brain.BASE_URL,
        "summary": {k: v for k, v in summary.items()},
        "target_dir": target_dir,
    }
    ledger.to_file(rpath, KEY_PATH, meta=meta)
    print(f"  receipt signed: {rpath}", flush=True)

    from .report import render
    mpath = os.path.join(RECEIPTS_DIR, f"{ledger.date}.md")
    render(rpath, mpath)
    print(f"  receipt rendered: {mpath}", flush=True)

    ok, problems = __import__("sloth.receipts", fromlist=["verify"]).verify(rpath)
    print(f"  self-verify: {'PASS' if ok else 'FAIL: ' + '; '.join(problems)}", flush=True)
    return rpath


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="sloth",
                                description="Sleepy Lazy Overnight Task Handler")
    sub = p.add_subparsers(dest="cmd", required=True)

    nr = sub.add_parser("night", help="run the full night shift now")
    nr.add_argument("--dir", default=DEFAULT_DIR)
    nr.add_argument("--labels", action="store_true",
                    help="opt-in: tag newsletters with an IMAP label (reversible)")
    nr.add_argument("--dry-tidy", action="store_true", help="tidy without moving")

    rr = sub.add_parser("run", help="run a single chore")
    rr.add_argument("chore", choices=["tidy", "inbox", "brief"])
    rr.add_argument("--dir", default=DEFAULT_DIR)

    sub.add_parser("verify", help="verify a receipt (default: latest)")
    sub.add_parser("undo", help="undo the last tidy pass in --dir")
    p.add_argument("--dir", default=DEFAULT_DIR)

    args = p.parse_args(argv)

    if args.cmd == "night":
        night(args.dir, apply_labels=args.labels, apply_tidy=not args.dry_tidy)
    elif args.cmd == "run":
        ledger = Ledger()
        if args.chore == "tidy":
            print(tidy.tidy_dir(args.dir, ledger, apply=True))
        elif args.chore == "inbox":
            print(inbox.triage(ledger))
        else:
            print(brief.build(ledger))
        os.makedirs(RECEIPTS_DIR, exist_ok=True)
        rpath = os.path.join(RECEIPTS_DIR, f"{ledger.date}-run.json")
        ledger.to_file(rpath, KEY_PATH)
        print("receipt:", rpath)
    elif args.cmd == "verify":
        from .report import latest_receipt
        from .receipts import verify as vfy
        path = latest_receipt()
        ok, problems = vfy(path) if path else (False, ["no receipts yet"])
        print(f"{path}: {'VERIFIED' if ok else 'FAILED'}")
        for prob in problems:
            print("  -", prob)
        sys.exit(0 if ok else 1)
    elif args.cmd == "undo":
        ledger = Ledger()
        print(tidy.undo_dir(args.dir, ledger))


if __name__ == "__main__":
    main()
