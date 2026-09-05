#!/usr/bin/env python3
"""UserPromptSubmit — classify intent, and route non-trivial work through the spec workflow.

Deterministic by design: this fires on every prompt the user ever types, so it costs no
tokens and no model round-trip. It is advisory only and never blocks.

Silence is the default branch. A trivial prompt must produce no output at all, or the
routing directive degrades into ambient noise the model learns to ignore.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import brain, common  # noqa: E402

LENGTH_THRESHOLD = 240
SHORT_PROMPT = 80

EXPLICIT = re.compile(r"(^|\s)/gentic\b|\bresume\b|\bcontinue where\b|\bpick (this|it) back up\b", re.I)
BARE_QUESTION = re.compile(r"^\s*(what|why|how|where|when|which|who|is|are|does|do|can|could|should)\b", re.I)
IMPERATIVE = re.compile(
    r"\b(add|build|create|implement|fix|refactor|migrate|rewrite|remove|delete|update|"
    r"change|make|write|set up|wire|deploy|ship|rename|split|extract)\b",
    re.I,
)

SIGNALS = {
    "vague requirement": re.compile(
        r"\b(fast(er)?|simple|simpler|robust|clean(er)?|secure|scalable|better|nice|proper(ly)?|proper)\b", re.I
    ),
    "breadth": re.compile(r"\b(all|every|each|across|everywhere|refactor|migrate|rewrite|overhaul)\b", re.I),
    "consequence": re.compile(
        r"\b(auth\w*|password|token|secret|credential|payment|billing|invoice|charge|"
        r"delete|drop|destroy|production|prod|deploy|release|public api|migration|schema)\b",
        re.I,
    ),
    "sequencing": re.compile(r"\b(then|after that|afterwards|first|finally|followed by)\b", re.I),
}


def detect(prompt):
    """Return (is_non_trivial, reason, matched_signal_names)."""
    if not prompt.strip():
        return False, None, []

    if EXPLICIT.search(prompt):
        return True, "explicit workflow request", []

    matched = [name for name, pattern in SIGNALS.items() if pattern.search(prompt)]

    if len(prompt) >= LENGTH_THRESHOLD:
        return True, "long, multi-part request", matched

    if BARE_QUESTION.match(prompt) and not IMPERATIVE.search(prompt):
        return False, None, matched

    if len(prompt) < SHORT_PROMPT and len(matched) < 2:
        return False, None, matched

    if len(matched) >= 2:
        return True, "multiple complexity signals", matched

    return False, None, matched


def unfinished_runs(cwd):
    """Names of gentic runs in this repo with an unchecked phase."""
    root = common.git_root(cwd)
    if not root:
        return []
    found = []
    try:
        for progress in sorted(Path(root).glob("docs/gentic/*/progress.md")):
            try:
                if "- [ ] " in progress.read_text():
                    found.append(progress.parent.name)
            except Exception:
                continue
    except Exception:
        return []
    return found[-3:]


def build_context(prompt, reason, matched, runs):
    lines = [
        "[workflow routing]",
        f"This request looks non-trivial ({reason}"
        + (f"; signals: {', '.join(matched)}" if matched else "")
        + ").",
        "",
        "Before writing any implementation code, invoke the `gentic` skill (Skill tool). It runs",
        "Scout -> Interview -> Masterprompt -> Execute -> Iterate, writing a durable artifact per",
        "phase so the work survives a context loss. Phases may be short; none may be skipped.",
    ]
    if "vague requirement" in matched:
        lines += [
            "",
            "Ambiguity flag: this prompt leans on adjectives that are not yet measurable. Each one",
            "must become a Definition-of-Done item with a number and a command, or an explicit non-goal.",
        ]
    if runs:
        lines += [
            "",
            "Unfinished gentic run(s) in this repo: " + ", ".join(runs) + ".",
            "Read that run's progress.md and resume it rather than starting a new one.",
        ]
    lines += ["", "Skip this only if the request is genuinely a single obvious change or a pure question."]
    return "\n".join(lines)


def main():
    payload = common.read_payload()
    prompt = str(payload.get("prompt") or "")

    # This hook fires exactly once per user prompt, so it owns the turn boundary that the
    # verification gate depends on. Must happen before any early return.
    common.begin_turn(payload)
    brain.session_reset(payload.get("session_id"))

    is_non_trivial, reason, matched = detect(prompt)
    if not is_non_trivial:
        return

    runs = unfinished_runs(payload.get("cwd"))
    common.emit_context(build_context(prompt, reason, matched, runs), event="UserPromptSubmit")


if __name__ == "__main__":
    common.safe_main(main)
