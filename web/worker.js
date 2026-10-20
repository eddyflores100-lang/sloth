// SLOTH breakfast dashboard — Cloudflare Worker.
// Serves the latest signed receipt, and verifies it INDEPENDENTLY of the
// Python that produced it: canonical JSON + SHA-256 chain + Ed25519 via
// WebCrypto. A different implementation agreeing is worth more than one.

const HTML = `
<!doctype html><html><head><meta charset=utf-8>
<title>SLOTH — signed receipts</title><style>
body{background:#0d1117;color:#e6edf3;font:16px/1.55 ui-monospace,Menlo,Consolas,monospace;max-width:880px;margin:40px auto;padding:0 20px}
h1{font-size:26px} h1 .z{color:#7ee787} a{color:#58a6ff}
.badge{display:inline-block;padding:4px 12px;border-radius:20px;font-size:13px}
.ok{background:#123623;color:#7ee787}.bad{background:#3d1418;color:#ff7b72}
.tool{font-size:12px;padding:2px 8px;border-radius:10px}
.tidy{background:#1f3a5f}.inbox{background:#3b2f63}.brief{background:#5f3a1f}
table{border-collapse:collapse;width:100%}td{padding:7px 10px;border-bottom:1px solid #21262d;vertical-align:top}
.ts{color:#8b949e;white-space:nowrap;font-size:13px}.why{color:#ffa657}
small,footer{color:#8b949e}footer{margin-top:34px;font-size:13px}
.key,.head{color:#8b949e;font-size:12px;word-break:break-all}
</style></head><body>
<h1><span class=z>🦥</span> SLOTH — breakfast dashboard</h1>
<p>the overnight agent's signed receipt &nbsp;|&nbsp; <a href="/receipt/latest.json">raw JSON</a>
&nbsp;|&nbsp; <a href="/verify">/verify</a></p>
<div id=v>…</div><div id=r></div>
<footer>SLOTH — Sleepy Lazy Overnight Task Handler · chain verified in this Worker with WebCrypto,
independent of the Python that wrote it · irreversible clicks stay human.</footer>
<script>
async function main(){
  const v = document.getElementById('v');
  try{
    const res = await fetch('/verify'); const d = await res.json();
    v.innerHTML = d.verified
      ? '<span class="badge ok">chain verified ✓ '+d.entries+' entries · Ed25519 ✓</span>'
      : '<span class="badge bad">VERIFICATION FAILED: '+d.problems.join('; ')+'</span>';
  }catch(e){ v.innerHTML='<span class="badge bad">verify error</span>'; }
  const r = document.getElementById('r');
  const d = await (await fetch('/receipt/latest.json')).json();
  const esc = s => String(s).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
  let h = '<h2>what the sloth did — '+esc(d.date)+'</h2><table>';
  for(const e of d.entries)
    h += '<tr><td class=ts>'+esc(e.ts)+'</td><td><span class="tool '+esc(e.tool)+'">'+esc(e.tool)+'</span></td><td>'+esc(e.action)+'</td></tr>';
  h += '</table><h2>what the sloth refused to do</h2><ul>';
  for(const x of d.declined) h += '<li><b>'+esc(x.tool)+'</b> — '+esc(x.action)+': <span class=why>'+esc(x.reason)+'</span></li>';
  if(!d.declined) h += '<li>(nothing declined)</li>';
  h += '</ul><h2>proof</h2><p class=head>head: '+esc(d.signature.head)+'<br>pubkey: '+esc(d.signature.public_key)+
       '<br>signed_at: '+esc(d.signature.signed_at)+'</p>';
  r.innerHTML = h;
}
main();
</script></body></html>`;

// canonical JSON identical to Python: json.dumps(sort_keys=True, separators=(",",":"), ensure_ascii=False)
function canonical(obj) {
  if (obj === null || typeof obj !== "object") return JSON.stringify(obj);
  if (Array.isArray(obj)) return "[" + obj.map(canonical).join(",") + "]";
  const keys = Object.keys(obj).sort();
  return "{" + keys.map(k => JSON.stringify(k) + ":" + canonical(obj[k])).join(",") + "}";
}
async function sha256hex(s) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
}

async function verifyReceipt(receipt) {
  const problems = [];
  let prev = "0".repeat(64);
  for (let n = 0; n < receipt.entries.length; n++) {
    const e = receipt.entries[n];
    const body = { ...e }; delete body.hash;
    if (e.prev !== prev) problems.push(`entry ${n}: prev-hash mismatch`);
    const h = await sha256hex(canonical(body));
    if (h !== e.hash) problems.push(`entry ${n}: hash mismatch`);
    prev = e.hash;
  }
  const sig = receipt.signature || {};
  if (sig.head !== prev) problems.push("signature: head mismatch");
  if (sig.entries !== receipt.entries.length) problems.push("signature: count mismatch");
  try {
    const payload = canonical({ scheme: sig.scheme, date: sig.date, head: sig.head,
      entries: sig.entries, declined: sig.declined, signed_at: sig.signed_at });
    const pubRaw = hexBytes(sig.public_key);
    const key = await crypto.subtle.importKey("raw", pubRaw, { name: "Ed25519" }, false, ["verify"]);
    const ok = await crypto.subtle.verify({ name: "Ed25519" }, key,
      hexBytes(sig.signature), new TextEncoder().encode(payload));
    if (!ok) problems.push("signature: Ed25519 verify FAILED");
  } catch (e) { problems.push("signature: " + e.message); }
  return problems;
}
function hexBytes(hex) {
  const a = new Uint8Array(hex.length / 2);
  for (let i = 0; i < a.length; i++) a[i] = parseInt(hex.substr(i * 2, 2), 16);
  return a;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "PUT" && url.pathname === "/api/receipt") {
      if (url.searchParams.get("token") !== env.UPLOAD_TOKEN)
        return new Response("forbidden", { status: 403 });
      const body = await request.json();
      await env.RECEIPTS.put("latest.json", JSON.stringify(body.json));
      await env.RECEIPTS.put("latest.html", body.html || "");
      return Response.json({ ok: true, date: body.json && body.json.date });
    }
    if (url.pathname === "/receipt/latest.json") {
      const j = await env.RECEIPTS.get("latest.json");
      return new Response(j || '{"error":"no receipts yet"}',
        { headers: { "content-type": "application/json", "access-control-allow-origin": "*" } });
    }
    if (url.pathname === "/verify") {
      const j = await env.RECEIPTS.get("latest.json");
      if (!j) return Response.json({ verified: false, problems: ["no receipts"] });
      const problems = await verifyReceipt(JSON.parse(j));
      const r = JSON.parse(j);
      return Response.json({ verified: problems.length === 0, problems,
        entries: r.entries.length, date: r.date });
    }
    const html = (await env.RECEIPTS.get("latest.html")) || HTML;
    return new Response(html, { headers: { "content-type": "text/html; charset=utf-8" } });
  }
};
