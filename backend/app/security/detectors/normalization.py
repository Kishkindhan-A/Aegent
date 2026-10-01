from __future__ import annotations

import re
import unicodedata

ZERO_WIDTH_CHARACTERS = ''.join([
    '\u200b',
    '\u200c',
    '\u200d',
    '\ufeff',
    '\u2060',
])


def normalize_security_text(content: str) -> str:
    """Normalize transient content before rule-based detection.

    The original text is kept untouched; only a normalized copy is inspected.
    This helps avoid false positives caused by zero-width code points and mixed
    whitespace while preserving the original user content outside the detection
    boundary.

    Offsets returned from this detector refer to the normalized content because
    normalization intentionally removes zero-width characters and collapses
    whitespace before rule evaluation.
    """
    normalized = unicodedata.normalize('NFKC', content)
    for char in ZERO_WIDTH_CHARACTERS:
        normalized = normalized.replace(char, '')
    normalized = normalized.replace('\u00a0', ' ')
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized.strip()
