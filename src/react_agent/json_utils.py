"""JSON extraction and canonicalization helpers shared by data tools."""

from __future__ import annotations

import json
from typing import Tuple


def extract_first_json(text: str) -> str | None:
    start = None
    depth = 0
    in_str = False
    escape = False
    for i, ch in enumerate(text):
        if start is None:
            if ch == "{":
                start = i
                depth = 1
            continue
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == "\"":
                in_str = False
            continue
        if ch == "\"":
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : i + 1]
                try:
                    json.loads(candidate)
                    return candidate
                except Exception:
                    return None
    return None


def canonicalize_response(text: str) -> Tuple[str, bool]:
    candidate = extract_first_json(text)
    if not candidate:
        return text, False
    try:
        obj = json.loads(candidate)
    except Exception:
        return text, False
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")), True
