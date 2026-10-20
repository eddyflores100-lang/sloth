"""sloth.report — turn a receipt file into something a human reads at breakfast."""

from __future__ import annotations

import glob
import json
import os
import html as H


def latest_receipt(receipts_dir: str | None = None) -> str | None:
    rdir = receipts_dir or os.path.join(os.path.dirname(__file__), "..", "receipts")
    files = sorted(glob.glob(os.path.join(rdir, "????-??-??.json")))
    return files[-1] if files else None


def render(receipt_path: str, out_path: str) -> str:
    with open(receipt_path, encoding="utf-8") as fh:
        r = json.load(fh)
    sig = r.get("signature", {})
    meta = r.get("meta", {})
    lines = [
        f"# SLOTH MORNING RECEIPT — {r['date']}",
        "",
        f"_Scheme `{r['scheme']}` | brain: {meta.get('brain', '?')} "
        f"| signed at {sig.get('signed_at', '?')}_",
        "",
        "## What the sloth did",
        "",
    ]
    for e in r.get("entries", []):
        lines.append(f"- `{e['ts']}` **{e['tool']}** — {e['action']}")
    if not r.get("entries"):
        lines.append("- (a quiet night — nothing to do)")
    lines += ["", "## What the sloth refused to do", ""]
    for d in r.get("declined", []):
        lines.append(f"- **{d['tool']}** — {d['action']}: {d['reason']}")
    if not r.get("declined"):
        lines.append("- (nothing declined tonight)")
    lines += [
        "",
        "## Proof",
        "",
        f"- entries: **{len(r.get('entries', []))}** | declined: **{len(r.get('declined', []))}**",
        f"- chain head: `{sig.get('head', '?')[:24]}…`",
        f"- Ed25519 public key: `{sig.get('public_key', '?')[:32]}…`",
        f"- signature: `{sig.get('signature', '?')[:32]}…`",
        "",
        "Verify it yourself, offline, no trust in the sloth required:",
        "",
        "```bash",
        f"sloth verify {os.path.basename(receipt_path)}",
        "```",
        "",
    ]
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return out_path


def render_html(receipt_path: str) -> str:
    """Standalone dark-mode receipt page for the dashboard."""
    with open(receipt_path, encoding="utf-8") as fh:
        r = json.load(fh)
    sig = r.get("signature", {})
    meta = r.get("meta", {})
    rows = []
    for e in r.get("entries", []):
        rows.append(
            f"<tr><td class=ts>{H.escape(e['ts'])}</td>"
            f"<td><span class='tool {H.escape(e['tool'])}'>{H.escape(e['tool'])}</span></td>"
            f"<td>{H.escape(e['action'])}</td></tr>")
    dec = []
    for d in r.get("declined", []):
        dec.append(f"<li><b>{H.escape(d['tool'])}</b> — {H.escape(d['action'])}: "
                   f"<span class=why>{H.escape(d['reason'])}</span></li>")
    brief = (meta.get("summary", {}) or {}).get("brief", {}) or {}
    brief_items = ""
    for it in brief.get("items", [])[:10]:
        gist = it.get("gist") or "_(brain asleep — title only)_"
        brief_items += (f"<li><a href='{H.escape(it.get('url') or '#')}'>"
                        f"{H.escape(it.get('title', ''))}</a><br><small>{H.escape(gist)}</small></li>")
    return f"""<!doctype html><html><head><meta charset=utf-8>
<title>SLOTH receipt {H.escape(r['date'])}</title><style>
body{{background:#0d1117;color:#e6edf3;font:16px/1.55 ui-monospace,Menlo,Consolas,monospace;max-width:880px;margin:40px auto;padding:0 20px}}
h1{{font-size:26px}} h1 .z{{color:#7ee787}} a{{color:#58a6ff}}
.badge{{display:inline-block;padding:4px 12px;border-radius:20px;font-size:13px}}
.ok{{background:#123623;color:#7ee787}} .tool{{font-size:12px;padding:2px 8px;border-radius:10px}}
.tidy{{background:#1f3a5f}} .inbox{{background:#3b2f63}} .brief{{background:#5f3a1f}}
table{{border-collapse:collapse;width:100%}} td{{padding:7px 10px;border-bottom:1px solid #21262d;vertical-align:top}}
.ts{{color:#8b949e;white-space:nowrap;font-size:13px}} .why{{color:#ffa657}}
.key,.head{{color:#8b949e;font-size:12px;word-break:break-all}}
small{{color:#8b949e}} footer{{margin-top:34px;color:#8b949e;font-size:13px}}
</style></head><body>
<h1><span class=z>&#129425;</span> SLOTH morning receipt — {H.escape(r['date'])}</h1>
<p>brain: {H.escape(str(meta.get('brain', '?')))} &nbsp;|&nbsp; signed at {H.escape(sig.get('signed_at', '?'))}
&nbsp;|&nbsp; <span class="badge ok">chain {len(r.get('entries', []))} entries &#10003; Ed25519</span></p>
<h2>what the sloth did</h2>
<table>{''.join(rows) or '<tr><td>(a quiet night)</td></tr>'}</table>
<h2>what the sloth refused to do</h2>
<ul>{''.join(dec) or '<li>(nothing declined)</li>'}</ul>
{'<h2>morning brief</h2><ol>' + brief_items + '</ol>' if brief_items else ''}
<h2>proof</h2>
<p class=head>chain head: {H.escape(sig.get('head', '?'))}<br>
public key: {H.escape(sig.get('public_key', '?'))}<br>
signature: {H.escape(sig.get('signature', '?'))}</p>
<p>Verify offline: <code>sloth verify {H.escape(os.path.basename(receipt_path))}</code></p>
<footer>SLOTH — Sleepy Lazy Overnight Task Handler &middot; receipts are hash-chained and signed; irreversible clicks stay human.</footer>
</body></html>"""
