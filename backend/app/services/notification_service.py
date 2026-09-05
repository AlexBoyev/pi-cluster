import logging
import smtplib
from email.message import EmailMessage

import httpx
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.notification_channel import NotificationChannel
from app.repositories.notification_repository import NotificationRepository

logger = logging.getLogger(__name__)


def _send_email_sync(to_address: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.brevo_alert_from_email
    msg["To"] = to_address
    msg.set_content(body)
    with smtplib.SMTP(settings.brevo_smtp_host, settings.brevo_smtp_port, timeout=8) as smtp:
        smtp.starttls()
        smtp.login(settings.brevo_smtp_username, settings.brevo_smtp_password)
        smtp.send_message(msg)


async def _send_to_channel(
    client: httpx.AsyncClient, ch: NotificationChannel, webhook_payload: dict, subject: str, body: str
) -> None:
    if ch.channel_type == "email":
        if not ch.email_address:
            logger.warning("Notification channel %s is type=email with no address set", ch.name)
            return
        await run_in_threadpool(_send_email_sync, ch.email_address, subject, body)
    else:
        if not ch.url:
            logger.warning("Notification channel %s is type=webhook with no url set", ch.name)
            return
        await client.post(ch.url, json=webhook_payload)
    logger.info("Notification sent to %s (%s)", ch.name, ch.channel_type)


async def _dispatch(webhook_payload: dict, subject: str, body: str, channels: list[NotificationChannel]) -> None:
    if not channels:
        return
    async with httpx.AsyncClient(timeout=5.0) as client:
        for ch in channels:
            try:
                await _send_to_channel(client, ch, webhook_payload, subject, body)
            except Exception as e:
                logger.warning("Notification failed for %s: %s", ch.name, e)


async def dispatch_alert_notification(
    alert_name: str,
    severity: str,
    summary: str | None,
    node_name: str | None,
) -> None:
    """Prometheus/AlertManager firings (NodeDown, HighCPU, PodCrashLooping,
    etc.) - most of these are routine noise (only NodeDown is severity
    "critical", everything else is "warning": prometheus/alerts.yml).
    Email is reserved for critical infra alerts only, so an inbox isn't
    spammed with every CPU blip - webhook channels (Slack etc.) still get
    everything, unchanged, since a channel muted per-service is easy to
    manage there and volume isn't a personal-inbox problem."""
    async with AsyncSessionLocal() as db:
        channels = await NotificationRepository(db).list_enabled()
    if severity != "critical":
        channels = [c for c in channels if c.channel_type != "email"]

    payload = {
        "event": "alert_firing",
        "alert": alert_name,
        "severity": severity,
        "summary": summary or "",
        "node": node_name or "cluster",
    }
    subject = f"[pi-cluster] {severity.upper()} alert: {alert_name}"
    body = f"{summary or alert_name}\nNode: {node_name or 'cluster'}"
    await _dispatch(payload, subject, body, channels)


async def dispatch_security_alert(event: str, message: str) -> None:
    """Separate from dispatch_alert_notification (Prometheus/AlertManager
    firings) - this is for application-level security events (new-IP
    logins etc., see docs/decisions.md). Always goes to every enabled
    channel, email included and never filtered - these are exactly the
    "someone's hacking my account" cases email should never be muted for,
    unlike the routine infra alerts above."""
    async with AsyncSessionLocal() as db:
        channels = await NotificationRepository(db).list_enabled()

    payload = {"event": event, "message": message}
    subject = f"[pi-cluster] Security alert: {event}"
    await _dispatch(payload, subject, message, channels)


async def test_channel(ch: NotificationChannel) -> bool:
    try:
        if ch.channel_type == "email":
            if not ch.email_address:
                return False
            await run_in_threadpool(
                _send_email_sync,
                ch.email_address,
                "[pi-cluster] Test notification",
                "This is a test notification from your pi-cluster admin panel.",
            )
            return True
        if not ch.url:
            return False
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                ch.url, json={"event": "test", "message": "Pi Cluster notification test"}
            )
            return resp.status_code < 400
    except Exception:
        return False
