from datetime import datetime, timezone
from typing import Any

import httpx

from src.notifications.config import notifications_settings


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fmt_actor(user: dict | None) -> str:
    user = user or {}
    email = user.get("email")
    name = user.get("name")
    subject = user.get("sub")
    if email and name:
        return f"{name} <{email}>"
    if email:
        return str(email)
    if name:
        return str(name)
    return str(subject or "unknown")


def _extract_channel_values(item: dict[str, Any] | None) -> tuple[str, str, list[str]]:
    if not item:
        return "Unknown", "Unknown", []
    service = str(item.get("Service") or "Unknown")
    channel_code = str(item.get("ChannelCode") or "Unknown")
    urls = item.get("URLs") or []
    if isinstance(urls, str):
        urls = [urls]
    if not isinstance(urls, list):
        urls = []
    return service, channel_code, [str(u) for u in urls]


def _diff_lines(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    keys = ["Client", "TVorRadio", "Label", "Project", "Service", "URLs"]
    for key in keys:
        old_value = before.get(key)
        new_value = after.get(key)
        if old_value != new_value:
            lines.append(f"{key} changed:")
            lines.append(f"  ❌ Old: {old_value}")
            lines.append(f"  ✅ New: {new_value}")
    return lines


def _build_message(
    *,
    action: str,
    source_table: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    user: dict | None,
    occurred_at: str,
) -> str:
    action_upper = action.upper()

    if action_upper == "CREATE":
        service, channel_code, urls = _extract_channel_values(after)
        lines = [
            f"🆕 New item added to {source_table}",
            f"👉 Service: {service}",
            f"👉 Channel Code: {channel_code}",
            f"👉 Actor: {_fmt_actor(user)}",
            f"👉 Occurred At (UTC): {occurred_at}",
            "URLs:",
        ]
        lines.extend([f"  • {u}" for u in urls] or ["  • (none)"])
        return "\n".join(lines)

    if action_upper == "DELETE":
        service, channel_code, urls = _extract_channel_values(before)
        lines = [
            f"🗑️ Item deleted from {source_table}",
            f"👉 Service: {service}",
            f"👉 Channel Code: {channel_code}",
            f"👉 Actor: {_fmt_actor(user)}",
            f"👉 Occurred At (UTC): {occurred_at}",
            "URLs:",
        ]
        lines.extend([f"  • {u}" for u in urls] or ["  • (none)"])
        return "\n".join(lines)

    service, channel_code, _ = _extract_channel_values(after or before)
    lines = [
        f"✏️ Item modified in {source_table}",
        f"👉 Service: {service}",
        f"👉 Channel Code: {channel_code}",
        f"👉 Actor: {_fmt_actor(user)}",
        f"👉 Occurred At (UTC): {occurred_at}",
        "",
    ]
    diff = _diff_lines(before or {}, after or {})
    if not diff:
        diff = ["No field-level changes detected."]
    lines.extend(diff)
    return "\n".join(lines)


def notify_channel_change(
    *,
    action: str,
    source_table: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    user: dict | None,
    occurred_at: str | None = None,
) -> bool:
    """Send a best-effort Google Chat notification for channel mutations."""
    webhook_url = notifications_settings.GCHAT_WEBHOOK_URL
    if not webhook_url:
        return False

    timestamp = occurred_at or _iso_now()
    message = _build_message(
        action=action,
        source_table=source_table,
        before=before,
        after=after,
        user=user,
        occurred_at=timestamp,
    )

    try:
        response = httpx.post(webhook_url, json={"text": message}, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"[notification] Failed to send GChat message: {e}")
        return False
