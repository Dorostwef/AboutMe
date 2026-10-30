"""
config.py
─────────
Centralised configuration loaded from environment variables / .env file.
All other modules import from here — never call os.getenv() directly elsewhere.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (two levels up from this file)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# ── Proxy normalization ────────────────────────────────────────────────────────
# If environment sets socks:// (common with v2ray/xray), normalize to socks5://
# so httpx and httpx2 recognize the scheme without raising ValueError.
for _proxy_var in ("all_proxy", "ALL_PROXY", "http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY"):
    _val = os.environ.get(_proxy_var)
    if _val and _val.startswith("socks://"):
        os.environ[_proxy_var] = "socks5://" + _val[len("socks://"):]


# ── LLM ───────────────────────────────────────────────────────────────────────
# Supports either OPENAI_API_KEY or GROQ_API_KEY
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY", "")
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL") or (
    "https://api.groq.com/openai/v1" if os.getenv("GROQ_API_KEY") else "https://api.openai.com/v1"
)
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "openai/gpt-oss-20b")

# ── GitHub ─────────────────────────────────────────────────────────────────────
GITHUB_TOKEN: str | None = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER: str = "Dorostwef"
# Canonical mapping from profile project id → GitHub repo name
GITHUB_REPOS: dict[str, str] = {
    "compiler":      "compiler-opt",
    "raft_kv":       "raft-kv",
    "neural_search": "neural-search",
    "dedit":         "Dedit",
    "hisyar":        "HisYar",
    "ap_git":        "ap-git-handson",
}

# ── Paths ──────────────────────────────────────────────────────────────────────
PROFILE_JSON_PATH: Path = _PROJECT_ROOT / "data" / "profile.json"

# ── Server ─────────────────────────────────────────────────────────────────────
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8000"))
