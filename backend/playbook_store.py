"""
Parses data/playbook/vendor_playbook.md into a {clause_slug: {default,
fallback, escalate, rationale}} dict, once, and caches it. The markdown
file is the human-edited source of truth (easy to read/diff); tools
shouldn't re-parse it on every call, so this module does it once at
first use and holds the result in memory.

If the playbook is edited while the process is running, call
reload_playbook() to pick up the change.
"""

import os
import re

from backend.clause_types import CLAUSE_TYPES

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAYBOOK_PATH = os.path.join(PROJECT_ROOT, "data", "playbook", "vendor_playbook.md")

_DISPLAY_NAME_TO_SLUG = {c["display_name"].lower(): c["slug"] for c in CLAUSE_TYPES}

_cache = None  # populated lazily by load_playbook()


def _clean(text):
    """Collapse a wrapped markdown paragraph (line breaks + indentation)
    into a single readable line."""
    return " ".join(text.split())


def _parse_section(header, body):
    """body is everything between one '## Header' and the next (or EOF)."""
    default = _extract_field(body, "Default", "Fallback")
    fallback = _extract_field(body, "Fallback", "Escalate")
    escalate = _extract_field(body, "Escalate", None)
    rationale = _extract_rationale(body)
    return {
        "default": default,
        "fallback": fallback,
        "escalate": escalate,
        "rationale": rationale,
    }


def _extract_field(body, label, next_label):
    if next_label:
        pattern = rf"\*\*{label}:\*\*\s*(.*?)\n-\s*\*\*{next_label}:\*\*"
    else:
        # Escalate is the last bullet -- ends at the blank line before
        # the "**Rationale:**" paragraph.
        pattern = rf"\*\*{label}:\*\*\s*(.*?)\n\n"
    match = re.search(pattern, body, re.DOTALL)
    if not match:
        raise ValueError(f"Could not find '{label}:' field in playbook section")
    return _clean(match.group(1))


def _extract_rationale(body):
    # No trailing "---" after the last section in the file, so accept
    # either a section break or end-of-string as the terminator.
    match = re.search(r"\*\*Rationale:\*\*\s*(.*?)(?:\n\n---|\s*\Z)", body, re.DOTALL)
    if not match:
        raise ValueError("Could not find '**Rationale:**' paragraph in playbook section")
    return _clean(match.group(1))


def load_playbook(force_reload=False):
    global _cache
    if _cache is not None and not force_reload:
        return _cache

    if not os.path.exists(PLAYBOOK_PATH):
        raise FileNotFoundError(
            f"Playbook not found at {PLAYBOOK_PATH}. "
            "Expected data/playbook/vendor_playbook.md to exist."
        )

    with open(PLAYBOOK_PATH, encoding="utf-8") as f:
        text = f.read()

    # Split on level-2 headers ("## Clause Name"); the first chunk (index
    # 0) is the doc's intro before the first header, so skip it.
    sections = re.split(r"\n## ", text)[1:]

    parsed = {}
    for section in sections:
        header_line, _, body = section.partition("\n")
        header = header_line.strip()
        slug = _DISPLAY_NAME_TO_SLUG.get(header.lower())
        if slug is None:
            # A section in the markdown doesn't match any known clause
            # type -- fail loudly rather than silently dropping it, since
            # that likely means the playbook and CLAUSE_TYPES have drifted.
            raise ValueError(
                f"Playbook section '{header}' doesn't match any clause "
                f"type in backend/clause_types.py"
            )
        parsed[slug] = _parse_section(header, body)

    missing = set(_DISPLAY_NAME_TO_SLUG.values()) - set(parsed.keys())
    if missing:
        raise ValueError(f"Playbook is missing sections for: {sorted(missing)}")

    _cache = parsed
    return _cache


def reload_playbook():
    return load_playbook(force_reload=True)


def get_policy(clause_slug):
    """Returns {default, fallback, escalate, rationale} for one clause
    type, or None if clause_slug isn't a known clause type."""
    playbook = load_playbook()
    return playbook.get(clause_slug)
