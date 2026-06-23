"""GitHub webhook receiver for processing PR events."""

import hashlib
import hmac
import json
import logging
import os

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from openhive.events import event_store

logger = logging.getLogger(__name__)


def _verify_signature(payload: bytes, signature: str | None) -> bool:
    """Verify GitHub webhook signature if a secret is configured."""
    secret = os.environ.get("GITHUB_WEBHOOK_SECRET")
    if not secret:
        # No secret configured, skip verification
        return True
    if not signature:
        return False

    expected = "sha256=" + hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def handle_github_webhook(request: Request) -> Response:
    """Process incoming GitHub webhook events."""
    body = await request.body()
    signature = request.headers.get("x-hub-signature-256")

    if not _verify_signature(body, signature):
        return JSONResponse({"error": "Invalid signature"}, status_code=401)

    event_type = request.headers.get("x-github-event", "")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    if event_type == "pull_request":
        _handle_pull_request(payload)
    elif event_type == "check_suite":
        _handle_check_suite(payload)
    elif event_type == "ping":
        logger.info("Received GitHub webhook ping")
    else:
        logger.debug("Ignoring event type: %s", event_type)

    return JSONResponse({"ok": True})


def _is_dependabot(payload: dict) -> bool:
    """Check if the PR author is dependabot."""
    user = payload.get("pull_request", {}).get("user", {})
    return user.get("login") == "dependabot[bot]"


def _handle_pull_request(payload: dict) -> None:
    """Handle pull_request webhook events."""
    action = payload.get("action", "")
    pr = payload.get("pull_request", {})

    if not _is_dependabot(payload):
        return

    repo = payload.get("repository", {}).get("full_name", "unknown")
    pr_number = pr.get("number", 0)
    title = pr.get("title", "")
    url = pr.get("html_url", "")

    if action == "opened":
        event_store.add_alert(
            alert_type="dependabot.pr.opened",
            title=f"New Dependabot PR in {repo}",
            summary=f"#{pr_number}: {title}",
            payload={
                "repo": repo,
                "pr_number": pr_number,
                "title": title,
                "url": url,
                "action": action,
            },
        )
    elif action == "closed" and pr.get("merged"):
        event_store.add_alert(
            alert_type="dependabot.pr.merged",
            title=f"Dependabot PR merged in {repo}",
            summary=f"#{pr_number}: {title}",
            payload={
                "repo": repo,
                "pr_number": pr_number,
                "title": title,
                "url": url,
                "action": "merged",
            },
        )


def _handle_check_suite(payload: dict) -> None:
    """Handle check_suite webhook events — notify when checks complete on dependabot PRs."""
    action = payload.get("action", "")
    if action != "completed":
        return

    check_suite = payload.get("check_suite", {})
    conclusion = check_suite.get("conclusion", "")
    prs = check_suite.get("pull_requests", [])
    repo = payload.get("repository", {}).get("full_name", "unknown")

    for pr in prs:
        pr_number = pr.get("number", 0)
        # We can't easily check if it's dependabot from check_suite,
        # so we create an alert for all check completions on PRs.
        # The frontend can filter by type.
        if conclusion == "success":
            event_store.add_alert(
                alert_type="pr.checks.passed",
                title=f"Checks passed in {repo}",
                summary=f"PR #{pr_number} — all checks passed, ready to merge",
                payload={
                    "repo": repo,
                    "pr_number": pr_number,
                    "conclusion": conclusion,
                },
            )
        elif conclusion == "failure":
            event_store.add_alert(
                alert_type="pr.checks.failed",
                title=f"Checks failed in {repo}",
                summary=f"PR #{pr_number} — checks failed",
                payload={
                    "repo": repo,
                    "pr_number": pr_number,
                    "conclusion": conclusion,
                },
            )


webhook_routes = [
    Route("/webhooks/github", handle_github_webhook, methods=["POST"]),
]
