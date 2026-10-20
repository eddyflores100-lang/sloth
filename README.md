# 🦥 SLOTH — Sleepy Lazy Overnight Task Handler

**The agent that does your chores while you sleep — and signs its own timesheet.**

SLOTH is an overnight chore agent with a **1-billion-parameter open-weight brain**
(Gemma 3 1B-it, quantized, served by llama.cpp **on your own CPU**) that spends
the night on the boring stuff — sorting your downloads folder, triaging your
mailbox, writing your morning brief — and leaves a **cryptographically signed
receipt** on the kitchen table.

```bash
$ sloth night
SLOTH NIGHT SHIFT — starting. Everything will be on the receipt.
  brain: gemma-3-1b-it (local, llama.cpp) | awake: True
  [1/3] tidying ~/Downloads            → 26 files moved, 7 buckets, revert manifest kept
  [2/3] triaging mailbox (read-only)   → 60 mails, 7 newsletters, 42 notifications
                                         7 unsubscribe links harvested (NOT clicked)
  [3/3] preparing the morning brief    → 10 HN stories, summarised on-device
  receipt signed: receipts/2026-10-20.json
  self-verify: PASS
```

## Why a receipt?

Because "trust me, it's fine" is not a security model for autonomous agents.

Every action SLOTH takes becomes one entry in a **SHA-256 hash chain**. At dawn
the chain head is signed with an **Ed25519 key**, and the receipt file embeds
the public key needed to check it. Anyone can verify a night's work offline,
in milliseconds, with zero trust in the sloth:

```bash
$ sloth verify receipts/2026-10-20.json
receipts/2026-10-20.json: VERIFIED
```

Edit one byte of one entry and the chain breaks. Delete an entry and the
signature stops matching the head. The receipt is the agent's *timesheet* —
the sloth cannot quietly change its story after the fact.

And because an honest agent is defined by what it *won't* do, every receipt
has a **"what the sloth refused to do"** section. Unsubscribe links are
harvested and listed for you — never clicked. Nothing is sent, deleted, or
bought. **Irreversible clicks stay human.**

```
## What the sloth refused to do
- inbox — click unsubscribe link: irreversible; link harvested for quora.com
  (open it yourself: https://www.quora.com/...)
- inbox — click unsubscribe link: irreversible; link harvested for medium.com
  (open it yourself: https://medium.com/me/settings/email/...)
```

## The three chores

| Chore | What it does | Brain's role |
|---|---|---|
| **tidy** | sorts `~/Downloads` into 8 buckets, keeps a revert manifest for `sloth undo` | writes the summary; never touches files |
| **inbox** | triages recent mail (envelope headers only), tags newsletters (opt-in, reversible IMAP label) | judges the genuinely ambiguous 15%; obvious machine mail is handled by deterministic rules |
| **brief** | pulls the HN front page, writes your 10-line morning brief | summarises every headline on-device |

## Architecture: the brain proposes, hands dispose, the ledger remembers

```
        ┌────────────┐   propose    ┌──────────────────────┐
        │ Gemma 3 1B │ ───────────▶ │ deterministic tools  │
        │  (llama.cpp│              │ tidy / inbox / brief │
        │  127.0.0.1)│ ◀─────────── │ + policy allowlist   │
        └────────────┘   classify   └──────────┬───────────┘
             open weights, on-CPU              │ every action
                                               ▼
                                    ┌──────────────────────┐
                                    │  SHA-256 hash chain  │
                                    │  → Ed25519 signature │
                                    │  → morning receipt   │
                                    └──────────────────────┘
```

Design rules, enforced in code (not in a prompt):

1. **The brain is advisory.** It classifies, summarises and drafts. It never
   touches the filesystem, your mailbox or the network.
2. **Fail-closed.** If the brain is asleep or answers nonsense, ambiguous
   mail is left untouched — never mislabeled. The receipt says so, honestly.
3. **Privacy by construction.** The inbox chore fetches *envelope headers
   only* — the sloth reads envelopes, not letters. Personal subjects never
   enter the ledger.
4. **Reversible by default.** Moves come with revert manifests; labels are
   plain IMAP labels `sloth undo` can remove.
5. **Slow on purpose.** 1B parameters, 2 CPU cores, all night. It's a sloth.

## Why open (weights) matters here

An agent that runs unsupervised in your home, on your files, on your mailbox,
should not require you to trust a remote company with the contents of either.
With Gemma 3 served locally by llama.cpp, the mail headers, file names and
summaries **never leave the machine** — there is no API key to leak, no
provider to subpoena, no silent model swap behind your back, and the whole
behavioural surface of the "AI" is a single 769 MB GGUF file you can
inspect, swap, or delete. Open weights turn the agent from a black box with
a privacy policy into a process you own — and the signed receipt turns
"you own it" into "you can *prove* what it did". The two belong together.

The receipt scheme follows the spirit of [ATC/1.0 credentials](https://github.com/alicelabs-llc/universal-trust-adapter)
(MIT / CC-BY-4.0) from the Universal Trust Adapter project — Ed25519
signatures over canonical JSON, with a verification path simple enough to
audit by hand.

## Run it

```bash
# 1. the brain — any OpenAI-compatible local server works
huggingface-cli download ggml-org/gemma-3-1b-it-GGUF gemma-3-1b-it-Q4_K_M.gguf
llama-server -m gemma-3-1b-it-Q4_K_M.gguf -c 4096 --port 8750 --threads 2

# 2. the sloth
pip install cryptography
export SLOTH_IMAP_CREDS="you@gmail.com:app-password"   # optional chore
python bin/sloth night --dir ~/Downloads --labels      # --labels is opt-in
python bin/sloth verify receipts/$(date +%F).json
python bin/sloth undo --dir ~/Downloads                # regret is supported

# 3. the breakfast dashboard
python web/app.py                                      # http://localhost:8080
```

Only dependency: `cryptography`. Everything else is stdlib — on purpose,
because an agent you can't read is an agent you can't trust.

| Env var | Default | Meaning |
|---|---|---|
| `SLOTH_BRAIN_URL` | `http://127.0.0.1:8750` | llama-server (OpenAI-compatible) |
| `SLOTH_TARGET_DIR` | `~/Downloads` | what gets tidied |
| `SLOTH_IMAP_CREDS` | – | `user:app-password` for the inbox chore |
| `SLOTH_RECEIPTS` | `./receipts` | where signed receipts land |
| `SLOTH_KEY` | `./.sloth_key` | Ed25519 key (generated, chmod 600) |

## The breakfast dashboard

A live signed receipt (chain verification happens server-side on every
`/verify` hit): **https://sloth.utalabs.tech**

## Crediting prior work

- [Gemma 3](https://developers.googleblog.com/en/introducing-gemma3/) (open weights) + [llama.cpp](https://github.com/ggml-org/llama.cpp) (MIT) — the brain.
- [Universal Trust Adapter / ATC/1.0](https://github.com/alicelabs-llc/universal-trust-adapter) — the Ed25519-over-canonical-JSON receipt scheme this project borrows from (our own prior project, credited as required).
- Hacker News Firebase API for the morning brief.

## License

MIT
