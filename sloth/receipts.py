"""sloth.receipts — the append-only ledger behind the signed morning receipt.

Every action the sloth takes becomes one entry in a SHA-256 hash chain:

    entry_i = {
      "i": index,
      "ts": iso8601,
      "tool": "tidy" | "inbox" | "brief",
      "action": short verb phrase,
      "detail": small JSON-able dict (never contains private subjects),
      "revert": small JSON-able dict enabling `sloth undo`, or null,
      "prev": hash of previous entry (genesis: 64 zeros),
      "hash": sha256(canonical_json(entry without "hash"))
    }

At dawn the chain is closed: the head hash is signed with an Ed25519 key
and stored next to the entries in a receipt file. Anyone can run
`sloth verify receipts/<date>.json` with nothing but the file itself —
the receipt embeds the public key it must be checked against.

Design note: this scheme follows the spirit of ATC/1.0 credentials from
the Universal Trust Adapter project (https://github.com/alicelabs-llc/
universal-trust-adapter) — Ed25519 signatures over canonical JSON, with
the verification path deliberately simple enough to audit by hand.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

GENESIS = "0" * 64


def canonical(obj) -> str:
    """Stable JSON canonicalisation (sorted keys, no whitespace)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hash_entry(entry: dict) -> str:
    body = {k: v for k, v in entry.items() if k != "hash"}
    return hashlib.sha256(canonical(body).encode("utf-8")).hexdigest()


class Ledger:
    """Append-only action ledger for a single night."""

    def __init__(self, date: str | None = None):
        self.date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.entries: list[dict] = []
        self.declined: list[dict] = []
        self.prev = GENESIS

    def record(self, tool: str, action: str, detail: dict | None = None,
               revert: dict | None = None) -> dict:
        entry = {
            "i": len(self.entries),
            "ts": now_iso(),
            "tool": tool,
            "action": action,
            "detail": detail or {},
            "revert": revert,
            "prev": self.prev,
        }
        entry["hash"] = _hash_entry(entry)
        self.entries.append(entry)
        self.prev = entry["hash"]
        return entry

    def decline(self, tool: str, action: str, reason: str) -> dict:
        """Log something the sloth refused to do. Reversibility is a promise."""
        rec = {"tool": tool, "action": action, "reason": reason, "ts": now_iso()}
        self.declined.append(rec)
        return rec

    @property
    def head(self) -> str:
        return self.prev

    def sign(self, private_key_path: str | None = None) -> dict:
        """Close the night: sign the head hash with Ed25519."""
        if private_key_path and os.path.exists(private_key_path):
            raw = open(private_key_path, "rb").read()
            key = serialization.load_pem_private_key(raw, password=None)
        else:
            key = Ed25519PrivateKey.generate()
            pem = key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
            if private_key_path:
                os.makedirs(os.path.dirname(private_key_path) or ".", exist_ok=True)
                with open(private_key_path, "wb") as fh:
                    fh.write(pem)
                os.chmod(private_key_path, 0o600)
        pub = key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        ).hex()
        payload = {
            "scheme": "SLOTH-RECEIPT-1",
            "date": self.date,
            "head": self.head,
            "entries": len(self.entries),
            "declined": len(self.declined),
            "signed_at": now_iso(),
        }
        sig = key.sign(canonical(payload).encode("utf-8")).hex()
        payload["signature"] = sig
        payload["public_key"] = pub
        return payload

    def to_file(self, path: str, private_key_path: str | None = None,
                meta: dict | None = None) -> str:
        receipt = {
            "scheme": "SLOTH-RECEIPT-1",
            "date": self.date,
            "meta": meta or {},
            "entries": self.entries,
            "declined": self.declined,
            "signature": self.sign(private_key_path),
        }
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(receipt, fh, indent=1, ensure_ascii=False)
        return path


def verify(path: str) -> tuple[bool, list[str]]:
    """Recompute the whole chain and check the Ed25519 signature. Offline."""
    problems: list[str] = []
    with open(path, encoding="utf-8") as fh:
        receipt = json.load(fh)

    prev = GENESIS
    for n, entry in enumerate(receipt.get("entries", [])):
        body = {k: v for k, v in entry.items() if k != "hash"}
        if entry.get("prev") != prev:
            problems.append(f"entry {n}: prev-hash mismatch (chain broken)")
        if _hash_entry(body) != entry.get("hash"):
            problems.append(f"entry {n}: hash mismatch (entry was tampered)")
        prev = entry.get("hash", "?")

    sig = receipt.get("signature", {})
    if sig.get("head") != prev:
        problems.append("signature: head hash does not match chain")
    if sig.get("entries") != len(receipt.get("entries", [])):
        problems.append("signature: entry count mismatch")

    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(sig["public_key"]))
        payload = {k: sig[k] for k in
                   ("scheme", "date", "head", "entries", "declined", "signed_at")}
        pub.verify(bytes.fromhex(sig["signature"]), canonical(payload).encode())
    except KeyError as exc:
        problems.append(f"signature: missing field {exc}")
    except Exception:
        problems.append("signature: Ed25519 verification FAILED")
    return (not problems), problems
