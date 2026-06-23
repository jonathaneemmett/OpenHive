"""MCP tools for managing alerts."""

import json
import logging
from typing import Annotated

from mcp.server import FastMCP
from pydantic import Field

from openhive.events import AlertStatus, event_store

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    """Register alert management tools on the MCP server."""

    @mcp.tool()
    async def list_alerts(
        status: Annotated[
            str | None,
            Field(description="Filter by status: unread, read, or dismissed"),
        ] = None,
        alert_type: Annotated[
            str | None,
            Field(description="Filter by alert type, e.g. dependabot.pr.opened"),
        ] = None,
    ) -> str:
        """List alerts, optionally filtered by status and/or type."""
        filter_status = None
        if status is not None:
            try:
                filter_status = AlertStatus(status)
            except ValueError:
                return f"Invalid status: {status}. Use unread, read, or dismissed."

        alerts = event_store.list_alerts(status=filter_status, alert_type=alert_type)
        if not alerts:
            return "No alerts found."

        return json.dumps([a.to_dict() for a in alerts], indent=2)

    @mcp.tool()
    async def mark_alert_read(
        alert_id: Annotated[str, Field(description="The alert ID to mark as read")],
    ) -> str:
        """Mark an alert as read."""
        if event_store.mark_read(alert_id):
            return f"Alert {alert_id} marked as read."
        return f"Alert {alert_id} not found."

    @mcp.tool()
    async def dismiss_alert(
        alert_id: Annotated[str, Field(description="The alert ID to dismiss")],
    ) -> str:
        """Dismiss an alert so it no longer appears in the unread list."""
        if event_store.dismiss(alert_id):
            return f"Alert {alert_id} dismissed."
        return f"Alert {alert_id} not found."
