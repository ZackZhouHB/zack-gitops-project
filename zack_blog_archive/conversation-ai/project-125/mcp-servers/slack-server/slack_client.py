"""
Slack Web API Client — Project 125

Thin wrapper around Slack Web API.
No framework dependencies — just requests.
"""

import logging
import time

import requests

logger = logging.getLogger("slack-client")

SLACK_API_BASE = "https://slack.com/api"


class SlackClient:
    """Slack Web API client for bot operations."""

    def __init__(self, bot_token: str, default_channel: str = "#platform-alerts"):
        self.bot_token = bot_token
        self.default_channel = default_channel
        self._headers = {
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    def _resolve_channel(self, channel: str) -> str:
        """Resolve channel name to ID if needed.

        Slack API accepts both channel names and IDs,
        but IDs are more reliable. This method caches lookups.
        """
        if channel.startswith("C") and not channel.startswith("#"):
            return channel  # Already an ID

        # Strip # prefix for lookup
        name = channel.lstrip("#")
        channels = self._list_channels_raw()
        for ch in channels:
            if ch["name"] == name:
                return ch["id"]

        return channel  # Return as-is, let API handle the error

    def _list_channels_raw(self) -> list[dict]:
        """Raw channel listing from API."""
        resp = requests.get(
            f"{SLACK_API_BASE}/conversations.list",
            headers=self._headers,
            params={"types": "public_channel", "limit": 200},
            timeout=15,
        )
        data = resp.json()
        if data.get("ok"):
            return data.get("channels", [])
        return []

    def post_message(
        self,
        channel: str,
        text: str,
        thread_ts: str | None = None,
        blocks: list[dict] | None = None,
    ) -> dict:
        """Post a message to a channel, optionally in a thread."""
        channel_id = self._resolve_channel(channel)
        payload = {"channel": channel_id, "text": text}
        if thread_ts:
            payload["thread_ts"] = thread_ts
        if blocks:
            payload["blocks"] = blocks

        resp = requests.post(
            f"{SLACK_API_BASE}/chat.postMessage",
            headers=self._headers,
            json=payload,
            timeout=15,
        )
        data = resp.json()

        if data.get("ok"):
            return {
                "success": True,
                "channel": data["channel"],
                "ts": data["ts"],
            }
        else:
            error = data.get("error", "unknown_error")
            message = self._friendly_error(error)
            return {"success": False, "error": error, "message": message}

    def post_rich_message(
        self,
        channel: str,
        title: str,
        fields: dict,
        context_text: str = "",
        jira_url: str = "",
    ) -> dict:
        """Post a Block Kit formatted message."""
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": title},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*{k}:*\n{v}"}
                    for k, v in fields.items()
                ],
            },
        ]

        if context_text:
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": context_text},
            })

        if jira_url:
            blocks.append({
                "type": "actions",
                "elements": [{
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View in Jira"},
                    "url": jira_url,
                }],
            })

        blocks.append({
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": f"_Created by Platform Health Agent • {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}_",
            }],
        })

        return self.post_message(
            channel=channel,
            text=title,  # Fallback for notifications
            blocks=blocks,
        )

    def list_channels(self) -> dict:
        """List channels the bot can access."""
        channels = self._list_channels_raw()
        return {
            "channels": [
                {
                    "id": ch["id"],
                    "name": f"#{ch['name']}",
                    "is_member": ch.get("is_member", False),
                    "num_members": ch.get("num_members", 0),
                }
                for ch in channels
            ]
        }

    @staticmethod
    def _friendly_error(error: str) -> str:
        """Map Slack error codes to human-readable messages."""
        errors = {
            "not_in_channel": "Bot is not a member of this channel. Add it via channel settings → Integrations → Add apps.",
            "channel_not_found": "Channel does not exist. Check the channel name.",
            "invalid_auth": "Bot token is invalid or expired. Regenerate in Slack app settings.",
            "missing_scope": "Bot lacks required permissions. Add the needed OAuth scope in app settings.",
            "ratelimited": "Too many requests. Wait and retry.",
            "account_inactive": "The bot has been deactivated.",
        }
        return errors.get(error, f"Slack API error: {error}")
