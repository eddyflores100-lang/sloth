"""sloth.policy — what the sloth may never do.

An autonomous agent running while you sleep needs a short, blunt rulebook.
These rules are enforced in code, not in a prompt: the brain only ever
*proposes*; every mutating action is a deterministic code path that
checks this module first.
"""

from __future__ import annotations

# Tools the ledger knows about. Anything else is refused at dispatch.
ALLOWED_TOOLS = {"tidy", "inbox", "brief", "core"}

# Hard denials. If an action string matches one of these prefixes it is
# routed to the "Declined" section of the receipt instead of executed.
DENIED = (
    "send email",        # the sloth never sends, only drafts/harvests
    "delete permanently",
    "purge",
    "empty trash",
    "purchase",
    "pay",
    "click",             # irreversible clicks stay human (e.g. unsubscribe)
    "accept",
    "install",
    "run shell",
)

# Fetches are fine; state-changing HTTP verbs are not.
ALLOWED_HTTP_METHODS = {"GET"}


def is_allowed(tool: str, action: str) -> tuple[bool, str]:
    if tool not in ALLOWED_TOOLS:
        return False, f"tool '{tool}' is not in the allowlist"
    low = action.strip().lower()
    for bad in DENIED:
        if low.startswith(bad):
            return False, f"'{action}' matches hard denial '{bad}'"
    return True, ""
