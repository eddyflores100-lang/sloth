"""sloth.tools.inbox — the email chore, read-only by default.

Scans recent INBOX mail, uses the local brain to split newsletters from
human mail, harvests List-Unsubscribe headers, and (opt-in) tags
newsletters with an IMAP label. What it never does: send, delete, or
click unsubscribe links — those are logged in the receipt's Declined
section and left for the human, because they are irreversible.

Privacy: sender domains and counts go in the receipt; subjects of
non-newsletter mail never do. Everything stays on your machine.
"""

from __future__ import annotations

import email
import imaplib
import os
import re
from email.header import decode_header, make_header
from email.utils import parseaddr

from .. import brain, policy

LABEL = "sloth/triaged"
MAX_SCAN = 60


def _clean(s: str) -> str:
    try:
        return str(make_header(decode_header(s or "")))
    except Exception:
        return s or ""


def _domain(addr: str) -> str:
    _, email_addr = parseaddr(addr)
    return email_addr.split("@")[-1].lower() if "@" in email_addr else "unknown"


def _redact(link: str) -> str:
    """Strip tokens: show origin + first path segment only.

    Unsubscribe URLs embed per-user tokens (e.g. GitHub's
    /unsubscribe-auth/<token>); a receipt is a publishable artifact, so
    it must never contain a working one-click opt-out for strangers.
    """
    m = re.match(r"^(https?://[^/]+/[^/?#]*)", link)
    return (m.group(1) + "/\u2026") if m else (link.split("?")[0] + "/\u2026")


def _list_unsub(msg: email.message.Message) -> str | None:
    raw = msg.get("List-Unsubscribe", "") or ""
    if not raw:
        return None
    urls = re.findall(r"<(https?://[^>]+)>", raw)
    return urls[0] if urls else None


def _is_bulk(frm: str, subj: str) -> bool:
    """Envelope-level bulk heuristics. The brain only sees these suspects."""
    low = (frm + " " + subj).lower()
    return any(k in low for k in (
        "noreply", "no-reply", "newsletter", "digest", "unsubscribe",
        "hello@", "notice@", "informer@", "updates@", "news@",
        "weekly", "daily", "marketing", "promo", "@substack", "@beehiiv",
        "list-"))


def triage(ledger, server: str = "imap.gmail.com", since_days: int = 21,
           apply_labels: bool = False, creds: tuple[str, str] | None = None,
           max_scan: int = MAX_SCAN) -> dict:
    if creds is None:
        cpath = os.environ.get("SLOTH_IMAP_CREDS")
        if cpath and os.path.exists(cpath):
            user, _, pw = open(cpath).read().strip().partition(":")
            creds = (user, pw)
    if not creds:
        ledger.decline("inbox", "scan mailbox", "no IMAP credentials provided")
        return {"error": "no creds"}

    user, pw = creds
    result: dict = {"scanned": 0, "newsletters": [], "human": 0, "notify": 0,
                    "unclassified": 0, "labeled": 0, "unsub_links": 0,
                    "brain": brain.MODEL_NAME}
    try:
        M = imaplib.IMAP4_SSL(server)
        M.login(user, pw)
        M.select("INBOX", readonly=True)
        # IMAP SINCE takes a date, not datetime — good enough for a chore
        from datetime import date, timedelta
        since = (date.today() - timedelta(days=since_days)).strftime("%d-%b-%Y")
        typ, data = M.search(None, "SINCE", since)
        ids = data[0].split()[-max_scan:]
        # Envelope-only fetch: FROM, SUBJECT, LIST-UNSUBSCRIBE. The sloth
        # reads envelopes, not letters — privacy by construction.
        HDRS = "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT LIST-UNSUBSCRIBE)])"
        rows: list[tuple[str, str, str, email.message.Message]] = []
        for i in ids:
            typ, d = M.fetch(i, HDRS)
            msg = email.message_from_bytes(d[0][1])
            frm = _clean(msg.get("From", ""))
            subj = " ".join(_clean(msg.get("Subject", "")).split())  # unfold headers
            rows.append((i.decode(), frm, subj, msg))

        # ---- three-way split: deterministic first, brain for the rest ------
        # 1) Obvious machine-thread mail: deterministic "notification".
        #    The brain never sees it — no tokens, no mistakes.
        # 2) Ambiguous bulk-looking mail: the brain's judgement call.
        # 3) Everything else: human, and the brain never sees it either.
        result["scanned"] = len(rows)
        ambiguous: list[tuple[str, str]] = []
        det_notification = 0
        for idx, (uid, frm, subj, msg) in enumerate(rows):
            dom = _domain(frm)
            if (dom.endswith("github.com") or dom.endswith("gitlab.com")
                    or subj.startswith("Re:") or re.match(r"^\[[^\]]+\]", subj)):
                det_notification += 1
                continue
            if _is_bulk(frm, subj) or _list_unsub(msg):
                ambiguous.append((f"s{idx}", f"from:{dom} subject:{subj[:90]}"))
        result["deterministic_notifications"] = det_notification

        classified: dict[str, str] = {}
        if ambiguous and brain.awake():
            classified = brain.classify_batch(
                ambiguous, ["newsletter", "notification", "human"]) or {}
        result["ambiguous"] = len(ambiguous)
        result["brain_classified"] = len(classified)
        result["brain_used"] = bool(classified)
        if ambiguous and not classified:
            ledger.record("inbox", "brain hiccup: ambiguous mail left untouched "
                                   "(fail-closed, nothing mislabeled)",
                          detail={"ambiguous": len(ambiguous)})

        by_uid = {f"s{idx}": (uid, frm, subj, msg)
                  for idx, (uid, frm, subj, msg) in enumerate(rows)}
        newsletter_uids: list[str] = []
        for key, (uid, frm, subj, msg) in by_uid.items():
            label = classified.get(key)
            if label is None:
                continue
            if label == "newsletter":
                dom = _domain(frm)
                link = _list_unsub(msg)
                if link:
                    # double gate: brain verdict AND a machine-readable exit
                    newsletter_uids.append(uid)
                    result["unsub_links"] += 1
                    # harvested for the human — the sloth does NOT click
                    ledger.decline(
                        "inbox", "click unsubscribe link",
                        f"irreversible; link harvested for {dom} "
                        f"(open it yourself from the original mail's "
                        f"List-Unsubscribe header: {_redact(link)})")
                    result["newsletters"].append({"domain": dom, "uid": uid})
                else:
                    result["skipped_no_unsub"] = result.get("skipped_no_unsub", 0) + 1
            elif label == "notification":
                result["notify"] += 1
            else:
                result["human"] += 1
        result["notify"] += det_notification

        if apply_labels and newsletter_uids:
            M.select("INBOX")  # read-write for labels only
            M.create(LABEL)
            row_from = {u: f for u, f, s, m in rows}
            for uid in newsletter_uids:
                st, _ = M.store(uid, "+X-GM-LABELS", LABEL)
                if st == "OK":
                    result["labeled"] += 1
                    ledger.record("inbox",
                                  f"labeled newsletter from {_domain(row_from[uid])}",
                                  detail={"uid": uid, "label": LABEL},
                                  revert={"imap": "remove label",
                                          "uid": uid, "label": LABEL})
        M.logout()
    except Exception as exc:  # never let one mailbox ruin the night
        ledger.record("inbox", "inbox scan failed; degraded gracefully",
                      detail={"error": str(exc)[:160]})
        result["error"] = str(exc)[:160]

    result["newsletters"] = result["newsletters"][:40]
    n = len(newsletter_uids) if newsletter_uids else len(result["newsletters"])
    ledger.record("inbox",
                  f"triaged {result['scanned']} mails: {n} newsletters, "
                  f"{result['human']} human, {result['notify']} notifications"
                  + (f", labeled {result['labeled']}" if apply_labels else ""),
                  detail={"scanned": result["scanned"], "newsletters": n,
                          "human": result["human"], "notify": result["notify"],
                          "deterministic_notifications": result.get("deterministic_notifications", 0),
                          "ambiguous_for_brain": result.get("ambiguous", 0),
                          "brain_classified": result.get("brain_classified", 0),
                          "unsub_links": result["unsub_links"],
                          "labeled": result["labeled"],
                          "privacy": "envelope headers only; personal subjects never leave the machine",
                          "domains": sorted({x["domain"] for x in result["newsletters"]})[:25]})
    return result
