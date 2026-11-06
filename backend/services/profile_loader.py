"""
profile_loader.py
──────────────────
Responsible for reading, validating, and sanitising data/profile.json.

Key design decisions
─────────────────────
1. The file is read once on first access and cached in memory (_PROFILE_CACHE).
   FastAPI is single-process by default, so a module-level cache is safe.

2. The phone number value is stripped before the profile is ever handed
   to any other module.  The schema tag `"visibility": "restricted"` is
   treated as ground truth – we do NOT rely on the LLM to redact it.

3. `get_sanitized_profile()` returns a deep-copied dict so callers cannot
   accidentally mutate the in-memory cache.

4. `get_profile_json_for_prompt()` serialises the sanitised profile to a
   compact JSON string ready to be embedded verbatim in the LLM system prompt.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from backend.config import PROFILE_JSON_PATH


# ── In-memory cache ────────────────────────────────────────────────────────────
_PROFILE_CACHE: dict[str, Any] | None = None


def _load_raw() -> dict[str, Any]:
    """Read profile.json from disk. Raises FileNotFoundError if missing."""
    path = Path(PROFILE_JSON_PATH)
    if not path.exists():
        raise FileNotFoundError(
            f"profile.json not found at '{path}'. "
            "Ensure the file exists before starting the server."
        )
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _sanitize(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Remove / redact any field whose visibility is 'restricted'.

    Rules applied (in order):
    1. personal_info.phone_number  → replaced with a placeholder string.
       The actual value is NEVER included anywhere in the returned dict.
    2. Any future field with "visibility": "restricted" at the top level
       of personal_info or any other first-level section is dropped.
    """
    profile = copy.deepcopy(raw)

    # ── Rule 1: hard-code phone number redaction ───────────────────────────────
    personal = profile.get("personal_info", {})
    phone = personal.get("phone_number", {})
    if isinstance(phone, dict) and phone.get("visibility") == "restricted":
        # Replace the actual value with a sentinel so downstream code never
        # sees the real number, even if the system prompt is leaked.
        personal["phone_number"] = {
            "value": "[REDACTED – private]",
            "visibility": "restricted",
            "status": phone.get("status", "refuse_to_share"),
        }

    # ── Rule 2: drop any top-level personal_info key marked restricted ─────────
    sanitized_personal: dict[str, Any] = {}
    for key, val in personal.items():
        if isinstance(val, dict) and val.get("visibility") == "restricted":
            # Skip restricted sub-objects (keeps the key but with a placeholder)
            sanitized_personal[key] = {"visibility": "restricted", "status": "refuse_to_share"}
        else:
            sanitized_personal[key] = val
    profile["personal_info"] = sanitized_personal

    # ── Rule 3: filter projects and courses to public-only ─────────────────────
    profile["courses"] = [
        c for c in profile.get("courses", [])
        if c.get("visibility") == "public"
    ]
    profile["projects"] = [
        p for p in profile.get("projects", [])
        if p.get("visibility") == "public"
    ]
    profile["reading_recommendations_catalog"] = [
        r for r in profile.get("reading_recommendations_catalog", [])
        if r.get("visibility") == "public"
    ]

    # Remove the JSON-schema reference (not useful in the LLM prompt)
    profile.pop("$schema", None)

    return profile


def get_sanitized_profile() -> dict[str, Any]:
    """
    Return the sanitised profile as a Python dict.
    The result is a fresh deep copy each time to prevent mutation bugs.
    """
    global _PROFILE_CACHE
    if _PROFILE_CACHE is None:
        _PROFILE_CACHE = _sanitize(_load_raw())
    return copy.deepcopy(_PROFILE_CACHE)


def get_profile_json_for_prompt() -> str:
    """
    Return the sanitised profile as a compact JSON string.
    This string is embedded verbatim inside the LLM system prompt.
    """
    return json.dumps(get_sanitized_profile(), ensure_ascii=False, indent=2)


def get_public_profile_dict() -> dict[str, Any]:
    """
    Return only the fields needed by the PublicProfile Pydantic model
    (used by GET /api/profile).
    """
    p = get_sanitized_profile()
    personal = p.get("personal_info", {})
    return {
        "name":                          personal.get("name", ""),
        "student_number":                personal.get("student_number", ""),
        "role":                          personal.get("role", ""),
        "institution":                   personal.get("institution", ""),
        "location":                      personal.get("location", ""),
        "email":                         personal.get("email", ""),
        "github_username":               personal.get("github_username", ""),
        "courses":                       p.get("courses", []),
        "projects":                      p.get("projects", []),
        "reading_recommendations_catalog": p.get("reading_recommendations_catalog", []),
        "job_fit_profile":               p.get("job_fit_profile", {}),
        "guardrails_and_limits":         p.get("guardrails_and_limits", {}),
    }


def reload_profile() -> None:
    """Force a cache invalidation (useful in tests or hot-reload scenarios)."""
    global _PROFILE_CACHE
    _PROFILE_CACHE = None
