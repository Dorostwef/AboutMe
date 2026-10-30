"""
github_service.py
──────────────────
Async HTTP client that calls the GitHub REST API v3 to fetch live repository
statistics and latest commit information for Joe King (GitHub: Dorostwef).

Design principles
─────────────────
• All network I/O is async (httpx.AsyncClient) so FastAPI's event loop is
  never blocked.
• Every function returns a typed dict; on any error (network failure,
  rate-limit, private/missing repo) it returns a "status: unavailable"
  sentinel instead of raising an exception.  The LLM engine can then
  transparently inform the visitor that live stats were unavailable.
• The service name is embedded in every returned dict so the LLM trace can
  record "external_service_used": "GitHub REST API v3" with confidence.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.config import GITHUB_OWNER, GITHUB_REPOS, GITHUB_TOKEN

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
_BASE_URL = "https://api.github.com"
_SERVICE_NAME = "GitHub REST API v3"
_TIMEOUT = 8.0  # seconds


def _build_headers() -> dict[str, str]:
    """Build request headers, adding authentication if GITHUB_TOKEN is set."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AboutMe-AI-Agent/1.0",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def _unavailable_sentinel(repo_id: str, reason: str) -> dict[str, Any]:
    """Return a clean failure dict that downstream code can detect and relay."""
    return {
        "service": _SERVICE_NAME,
        "repo_id": repo_id,
        "status": "unavailable",
        "reason": reason,
        "repo_meta": None,
        "latest_commit": None,
    }


async def fetch_repo_data(repo_id: str) -> dict[str, Any]:
    """
    Fetch repository metadata and the latest commit for *repo_id*.

    Parameters
    ──────────
    repo_id : str
        One of the keys in GITHUB_REPOS (e.g. "compiler", "raft_kv", "neural_search").

    Returns
    ───────
    dict with keys:
        service         – always "GitHub REST API v3"
        repo_id         – the repo_id argument
        status          – "ok" | "unavailable"
        reason          – human-readable error description (only when status == "unavailable")
        repo_meta       – dict with stars, forks, language, open_issues, updated_at
        latest_commit   – dict with sha, message, author, date  (or None)
    """
    repo_name = GITHUB_REPOS.get(repo_id)
    if not repo_name:
        return _unavailable_sentinel(repo_id, f"Unknown repo_id '{repo_id}' – not in GITHUB_REPOS config.")

    repo_url = f"{_BASE_URL}/repos/{GITHUB_OWNER}/{repo_name}"
    commits_url = f"{repo_url}/commits?per_page=1"
    headers = _build_headers()

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            # ── 1. Repository metadata ──────────────────────────────────────────
            repo_resp = await client.get(repo_url, headers=headers)

            if repo_resp.status_code == 404:
                return _unavailable_sentinel(
                    repo_id,
                    f"Repository '{GITHUB_OWNER}/{repo_name}' not found (404). "
                    "It may be private or not yet created.",
                )
            if repo_resp.status_code == 403:
                return _unavailable_sentinel(
                    repo_id,
                    "GitHub API rate limit exceeded or token permissions insufficient (403).",
                )
            repo_resp.raise_for_status()
            repo_json: dict[str, Any] = repo_resp.json()

            repo_meta: dict[str, Any] = {
                "full_name":    repo_json.get("full_name"),
                "description":  repo_json.get("description"),
                "stars":        repo_json.get("stargazers_count", 0),
                "forks":        repo_json.get("forks_count", 0),
                "language":     repo_json.get("language"),
                "open_issues":  repo_json.get("open_issues_count", 0),
                "updated_at":   repo_json.get("updated_at"),
                "html_url":     repo_json.get("html_url"),
            }

            # ── 2. Latest commit ────────────────────────────────────────────────
            commits_resp = await client.get(commits_url, headers=headers)
            latest_commit: dict[str, Any] | None = None

            if commits_resp.status_code == 200:
                commits_data = commits_resp.json()
                if commits_data:
                    raw = commits_data[0]
                    commit_info = raw.get("commit", {})
                    committer = commit_info.get("committer", {})
                    author = commit_info.get("author", {})
                    latest_commit = {
                        "sha":     raw.get("sha", "")[:7],   # short SHA
                        "message": commit_info.get("message", "").split("\n")[0],  # first line only
                        "author":  author.get("name") or committer.get("name"),
                        "date":    committer.get("date") or author.get("date"),
                        "url":     raw.get("html_url"),
                    }

    except httpx.TimeoutException:
        return _unavailable_sentinel(repo_id, "GitHub API request timed out.")
    except httpx.RequestError as exc:
        logger.warning("GitHub API network error for repo '%s': %s", repo_id, exc)
        return _unavailable_sentinel(repo_id, f"Network error: {exc}")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error fetching GitHub data for repo '%s'", repo_id)
        return _unavailable_sentinel(repo_id, f"Unexpected error: {exc}")

    return {
        "service":       _SERVICE_NAME,
        "repo_id":       repo_id,
        "status":        "ok",
        "reason":        None,
        "repo_meta":     repo_meta,
        "latest_commit": latest_commit,
    }


async def fetch_all_repos() -> dict[str, dict[str, Any]]:
    """
    Fetch data for every repo in GITHUB_REPOS concurrently.

    Returns a dict keyed by repo_id, e.g.:
        {
            "compiler":     { ... },
            "raft_kv":      { ... },
            "neural_search":{ ... },
        }
    """
    import asyncio
    results = await asyncio.gather(
        *[fetch_repo_data(repo_id) for repo_id in GITHUB_REPOS],
        return_exceptions=False,
    )
    return dict(zip(GITHUB_REPOS.keys(), results))


def format_for_prompt(github_data: dict[str, Any]) -> str:
    """
    Convert a single fetch_repo_data() result into a compact human-readable
    block to be embedded in the LLM system prompt alongside profile.json.

    Example output:
        ## GitHub Live Data: compiler (Dorostwef/compiler-opt)
        Stars: 12 | Forks: 3 | Primary Language: Rust | Open Issues: 1
        Last updated: 2026-10-28T14:22:00Z
        Latest commit [a3f91c2]: "fix register allocation spill logic" by Joe King on 2026-10-27T09:15:00Z
    """
    if github_data.get("status") == "unavailable":
        return (
            f"## GitHub Live Data: {github_data['repo_id']}\n"
            f"Status: unavailable – {github_data.get('reason', 'unknown reason')}\n"
        )

    meta = github_data.get("repo_meta") or {}
    commit = github_data.get("latest_commit")
    lines = [
        f"## GitHub Live Data: {github_data['repo_id']} ({meta.get('full_name', '')})",
        (
            f"Stars: {meta.get('stars', 'N/A')} | "
            f"Forks: {meta.get('forks', 'N/A')} | "
            f"Primary Language: {meta.get('language', 'N/A')} | "
            f"Open Issues: {meta.get('open_issues', 'N/A')}"
        ),
        f"Last updated: {meta.get('updated_at', 'N/A')}",
    ]
    if commit:
        lines.append(
            f"Latest commit [{commit['sha']}]: \"{commit['message']}\" "
            f"by {commit.get('author', 'unknown')} on {commit.get('date', 'N/A')}"
        )
    return "\n".join(lines)
