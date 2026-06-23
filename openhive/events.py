"""In-memory event store for tracking alerts and notifications."""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class AlertStatus(Enum):
    UNREAD = "unread"
    READ = "read"
    DISMISSED = "dismissed"


@dataclass
class Alert:
    """A single alert/notification."""

    id: str
    type: str
    title: str
    summary: str
    payload: dict[str, object]
    created_at: str
    status: AlertStatus = AlertStatus.UNREAD

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "summary": self.summary,
            "payload": self.payload,
            "created_at": self.created_at,
            "status": self.status.value,
        }


class EventStore:
    """In-memory store for alerts with subscriber notification."""

    def __init__(self, max_alerts: int = 500) -> None:
        self._alerts: dict[str, Alert] = {}
        self._max_alerts = max_alerts
        self._subscribers: list[asyncio.Queue[Alert]] = []

    def add_alert(
        self,
        alert_type: str,
        title: str,
        summary: str,
        payload: dict[str, object] | None = None,
    ) -> Alert:
        """Create and store a new alert, notifying all subscribers."""
        alert = Alert(
            id=str(uuid.uuid4()),
            type=alert_type,
            title=title,
            summary=summary,
            payload=payload or {},
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        self._alerts[alert.id] = alert
        self._enforce_limit()

        # Notify all SSE subscribers
        for queue in self._subscribers:
            try:
                queue.put_nowait(alert)
            except asyncio.QueueFull:
                logger.warning("Subscriber queue full, dropping alert")

        logger.info("Alert created: [%s] %s", alert_type, title)
        return alert

    def get_alert(self, alert_id: str) -> Alert | None:
        return self._alerts.get(alert_id)

    def list_alerts(
        self, status: AlertStatus | None = None, alert_type: str | None = None
    ) -> list[Alert]:
        """List alerts, optionally filtered by status and/or type."""
        alerts = list(self._alerts.values())
        if status is not None:
            alerts = [a for a in alerts if a.status == status]
        if alert_type is not None:
            alerts = [a for a in alerts if a.type == alert_type]
        alerts.sort(key=lambda a: a.created_at, reverse=True)
        return alerts

    def mark_read(self, alert_id: str) -> bool:
        alert = self._alerts.get(alert_id)
        if alert is None:
            return False
        alert.status = AlertStatus.READ
        return True

    def dismiss(self, alert_id: str) -> bool:
        alert = self._alerts.get(alert_id)
        if alert is None:
            return False
        alert.status = AlertStatus.DISMISSED
        return True

    def subscribe(self) -> asyncio.Queue[Alert]:
        """Create a new subscriber queue for SSE streaming."""
        queue: asyncio.Queue[Alert] = asyncio.Queue(maxsize=100)
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[Alert]) -> None:
        """Remove a subscriber queue."""
        try:
            self._subscribers.remove(queue)
        except ValueError:
            pass

    def _enforce_limit(self) -> None:
        """Remove oldest dismissed/read alerts if over limit."""
        if len(self._alerts) <= self._max_alerts:
            return
        sorted_alerts = sorted(self._alerts.values(), key=lambda a: a.created_at)
        for alert in sorted_alerts:
            if len(self._alerts) <= self._max_alerts:
                break
            if alert.status == AlertStatus.DISMISSED:
                del self._alerts[alert.id]
        for alert in sorted_alerts:
            if len(self._alerts) <= self._max_alerts:
                break
            if alert.status == AlertStatus.READ:
                del self._alerts[alert.id]


# Global event store instance
event_store = EventStore()
