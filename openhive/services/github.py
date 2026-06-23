import json
import logging
import os
import time
from pathlib import Path

import httpx
import jwt

logger = logging.getLogger(__name__)

GITHUB_API_URL = "https://api.github.com"
CONFIG_PATH = Path.home() / ".openhive" / "config.json"

# Cached installation token and its expiry
_cached_token: str | None = None
_token_expires_at: float = 0.0


def _load_config() -> dict[str, object]:
    """Load config from ~/.openhive/config.json."""
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {}


def _get_app_id() -> str:
    """Load GitHub App ID from env var or config."""
    app_id = os.environ.get("GITHUB_APP_ID")
    if app_id:
        return app_id

    config = _load_config()
    app_id = config.get("github_app_id")
    if isinstance(app_id, (str, int)) and app_id:
        return str(app_id)

    raise ValueError(
        "No GitHub App ID found. Set GITHUB_APP_ID env var "
        f"or add 'github_app_id' to {CONFIG_PATH}"
    )


def _get_private_key() -> str:
    """Load GitHub App private key from env var or config."""
    key = os.environ.get("GITHUB_APP_PRIVATE_KEY")
    if key:
        return key

    config = _load_config()
    key = config.get("github_app_private_key")
    if isinstance(key, str) and key:
        return key

    raise ValueError(
        "No GitHub App private key found. Set GITHUB_APP_PRIVATE_KEY env var "
        f"or add 'github_app_private_key' to {CONFIG_PATH}"
    )


def _get_installation_id() -> str:
    """Load GitHub App installation ID from env var or config."""
    inst_id = os.environ.get("GITHUB_APP_INSTALLATION_ID")
    if inst_id:
        return inst_id

    config = _load_config()
    inst_id = config.get("github_app_installation_id")
    if isinstance(inst_id, (str, int)) and inst_id:
        return str(inst_id)

    raise ValueError(
        "No GitHub App installation ID found. Set GITHUB_APP_INSTALLATION_ID env var "
        f"or add 'github_app_installation_id' to {CONFIG_PATH}"
    )


def _generate_jwt() -> str:
    """Generate a short-lived JWT signed with the App's private key."""
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + (10 * 60),
        "iss": _get_app_id(),
    }
    private_key = _get_private_key()
    return jwt.encode(payload, private_key, algorithm="RS256")


async def _get_installation_token() -> str:
    """Get a cached installation token, refreshing if expired."""
    global _cached_token, _token_expires_at

    if _cached_token and time.time() < _token_expires_at:
        return _cached_token

    app_jwt = _generate_jwt()
    installation_id = _get_installation_id()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GITHUB_API_URL}/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

    _cached_token = data["token"]
    # Tokens expire in 1 hour; refresh 5 minutes early
    _token_expires_at = time.time() + 3300
    logger.info("Refreshed GitHub App installation token")
    return _cached_token


async def _headers() -> dict[str, str]:
    token = await _get_installation_token()
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def list_pulls(
    repo: str, author: str = "app/dependabot"
) -> list[dict[str, object]]:
    """List open PRs by a given author."""
    headers = await _headers()
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GITHUB_API_URL}/repos/{repo}/pulls",
            headers=headers,
            params={"state": "open", "per_page": 100},
            timeout=30.0,
        )
        response.raise_for_status()
        pulls: list[dict[str, object]] = response.json()
        return [
            p for p in pulls
            if p.get("user", {}).get("login") == "dependabot[bot]"
        ]


async def get_check_status(repo: str, sha: str) -> str:
    """Get combined check status for a commit: success, failure, or pending."""
    headers = await _headers()
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GITHUB_API_URL}/repos/{repo}/commits/{sha}/status",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        data: dict[str, str] = response.json()
        return data.get("state", "unknown")


async def approve_pr(repo: str, pr_number: int) -> None:
    """Submit an approval review on a PR."""
    headers = await _headers()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GITHUB_API_URL}/repos/{repo}/pulls/{pr_number}/reviews",
            headers=headers,
            json={"event": "APPROVE"},
            timeout=30.0,
        )
        response.raise_for_status()


async def merge_pr(
    repo: str, pr_number: int, method: str = "squash"
) -> dict[str, object]:
    """Merge a PR. Method can be 'merge', 'squash', or 'rebase'."""
    headers = await _headers()
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{GITHUB_API_URL}/repos/{repo}/pulls/{pr_number}/merge",
            headers=headers,
            json={"merge_method": method},
            timeout=30.0,
        )
        response.raise_for_status()
        result: dict[str, object] = response.json()
        return result
