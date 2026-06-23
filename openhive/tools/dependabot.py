import json
import logging
from typing import Annotated

from mcp.server import FastMCP
from pydantic import Field

from openhive.services import github

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    """Register dependabot tools on the MCP server."""

    @mcp.tool()
    async def list_dependabot_prs(
        repo: Annotated[str, Field(description="GitHub repo in owner/repo format")],
    ) -> str:
        """List open Dependabot PRs with their CI status."""
        try:
            pulls = await github.list_pulls(repo)
        except Exception as e:
            return f"Error fetching PRs: {e}"

        if not pulls:
            return f"No open Dependabot PRs in {repo}."

        results = []
        for pr in pulls:
            sha = pr.get("head", {}).get("sha", "")
            status = "unknown"
            if sha:
                try:
                    status = await github.get_check_status(repo, sha)
                except Exception:
                    status = "error"

            results.append({
                "number": pr["number"],
                "title": pr["title"],
                "url": pr["html_url"],
                "ci_status": status,
            })

        return json.dumps(results, indent=2)

    @mcp.tool()
    async def merge_dependabot_pr(
        repo: Annotated[str, Field(description="GitHub repo in owner/repo format")],
        pr_number: Annotated[int, Field(description="PR number to merge")],
        method: Annotated[
            str,
            Field(description="Merge method: squash, merge, or rebase"),
        ] = "squash",
    ) -> str:
        """Approve and merge a single Dependabot PR."""
        try:
            await github.approve_pr(repo, pr_number)
            result = await github.merge_pr(repo, pr_number, method)
            return f"PR #{pr_number} merged: {result.get('message', 'success')}"
        except Exception as e:
            return f"Error merging PR #{pr_number}: {e}"

    @mcp.tool()
    async def merge_all_dependabot_prs(
        repo: Annotated[str, Field(description="GitHub repo in owner/repo format")],
        method: Annotated[
            str,
            Field(description="Merge method: squash, merge, or rebase"),
        ] = "squash",
    ) -> str:
        """Approve and merge all Dependabot PRs that have passing CI."""
        try:
            pulls = await github.list_pulls(repo)
        except Exception as e:
            return f"Error fetching PRs: {e}"

        if not pulls:
            return f"No open Dependabot PRs in {repo}."

        merged = []
        skipped = []

        for pr in pulls:
            number = pr["number"]
            title = pr["title"]
            sha = pr.get("head", {}).get("sha", "")

            status = "unknown"
            if sha:
                try:
                    status = await github.get_check_status(repo, sha)
                except Exception:
                    status = "error"

            if status != "success":
                skipped.append(f"#{number} ({title}) - CI: {status}")
                continue

            try:
                await github.approve_pr(repo, number)
                await github.merge_pr(repo, number, method)
                merged.append(f"#{number} ({title})")
            except Exception as e:
                skipped.append(f"#{number} ({title}) - Error: {e}")

        lines = []
        if merged:
            lines.append(f"Merged {len(merged)} PR(s):")
            lines.extend(f"  - {m}" for m in merged)
        if skipped:
            lines.append(f"Skipped {len(skipped)} PR(s):")
            lines.extend(f"  - {s}" for s in skipped)

        return "\n".join(lines)
