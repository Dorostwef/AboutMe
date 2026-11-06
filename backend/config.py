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


# ── LLM Configuration (Generic / Global) ───────────────────────────────────────
# Primary global configuration variables: API_KEY, URL, MODEL
# Designed to work with ANY OpenAI-compatible endpoint URL (OpenRouter, Groq, OpenAI, Ollama, custom proxies).

API_KEY: str = (
    os.getenv("API_KEY")
    or os.getenv("OPENROUTER_API_KEY")
    or os.getenv("GROQ_API_KEY")
    or os.getenv("OPENAI_API_KEY", "")
)

# Determine sensible default URL if not explicitly provided
_default_url = "https://openrouter.ai/api/v1"
if API_KEY.startswith("gsk_"):
    _default_url = "https://api.groq.com/openai/v1"
elif API_KEY.startswith("sk-or-"):
    _default_url = "https://openrouter.ai/api/v1"
elif API_KEY.startswith("sk-"):
    _default_url = "https://api.openai.com/v1"

# URL accepts any link provided via environment variable
_raw_url = (
    os.getenv("URL")
    or os.getenv("BASE_URL")
    or os.getenv("OPENAI_BASE_URL")
    or _default_url
).strip()

# Strip /chat/completions if the user pasted the complete curl endpoint URL
if _raw_url.endswith("/chat/completions/"):
    _raw_url = _raw_url[:-len("/chat/completions/")]
elif _raw_url.endswith("/chat/completions"):
    _raw_url = _raw_url[:-len("/chat/completions")]

URL: str = _raw_url.rstrip("/")

# Determine default model based on the URL target if MODEL not explicitly set
_default_model = "meta-llama/llama-3.3-70b-instruct"
if "cloudflare.com" in URL:
    _default_model = "@cf/zai-org/glm-4.7-flash"
elif "groq.com" in URL:
    _default_model = "openai/gpt-oss-20b"
elif "openai.com" in URL:
    _default_model = "gpt-4o-mini"
elif "openrouter.ai" in URL:
    _default_model = "meta-llama/llama-3.3-70b-instruct"

MODEL: str = (
    os.getenv("MODEL")
    or os.getenv("OPENAI_MODEL")
    or _default_model
)

# Backward-compatibility aliases
OPENAI_API_KEY: str = API_KEY
OPENAI_BASE_URL: str = URL
OPENAI_MODEL: str = MODEL
OPENROUTER_API_KEY: str = API_KEY

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
