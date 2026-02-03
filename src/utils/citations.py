"""Helpers for cleaning and extracting evidence IDs in text."""

from __future__ import annotations

import re
from typing import Iterable, List


EVIDENCE_ID_RE = re.compile(r"ev_[a-f0-9]{8}", re.IGNORECASE)


def _unique_preserve_order(items: Iterable[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def extract_evidence_ids(text: str) -> List[str]:
    """Extract evidence IDs from text, preserving order and uniqueness."""
    if not text:
        return []
    return _unique_preserve_order(EVIDENCE_ID_RE.findall(text))


def normalize_evidence_ids(ids: Iterable[str] | str | None) -> List[str]:
    """Normalize evidence IDs into a clean, unique list."""
    if not ids:
        return []
    if isinstance(ids, str):
        ids_iter: Iterable[str] = [ids]
    else:
        ids_iter = ids

    normalized: List[str] = []
    for value in ids_iter:
        if not isinstance(value, str):
            continue
        match = EVIDENCE_ID_RE.search(value)
        if match:
            normalized.append(match.group(0))
        else:
            cleaned = value.strip()
            if cleaned:
                normalized.append(cleaned)
    return _unique_preserve_order(normalized)


def strip_evidence_markers(text: str) -> str:
    """Remove inline evidence markers like (ev_xxx) or ev_xxx from text."""
    if not text:
        return ""

    cleaned = text
    # Remove parenthetical groups that contain evidence IDs.
    cleaned = re.sub(
        r"\s*\((?:[^)]*ev_[a-f0-9]{8}[^)]*)\)",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    # Remove bracketed groups that contain evidence IDs.
    cleaned = re.sub(
        r"\s*\[(?:[^\]]*ev_[a-f0-9]{8}[^\]]*)\]",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    # Remove any remaining standalone evidence IDs.
    cleaned = re.sub(r"\s*ev_[a-f0-9]{8}", "", cleaned, flags=re.IGNORECASE)
    # Clean up empty parentheses and extra spacing.
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    cleaned = re.sub(r"\s+,", ",", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = cleaned.replace(" ,", ",").replace(" .", ".")
    return cleaned.strip()
