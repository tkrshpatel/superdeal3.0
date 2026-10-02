"""Telegram MTProto user-account reader for external/public channels."""
from __future__ import annotations
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from .telegram import TelegramMessage
PUBLIC_URL_RE = re.compile(r"^https?://(?:t\.me|telegram\.me)/(?:s/)?([^/?#]+)", re.I)
class TelegramUserReaderError(RuntimeError): pass
def normalize_user_channel(value: str) -> str:
    value=value.strip()
    if not value: return value
    match=PUBLIC_URL_RE.match(value)
    if match: value=match.group(1)
    if value.startswith("@"): value=value[1:]
    if value.startswith("+"): raise ValueError("Invite-link tokens are not supported; use a public channel URL, username, or chat ID")
    return value.strip()
class TelegramUserSource:
    def __init__(self, api_id: int | str, api_hash: str, *, session: str="data/telegram_user", client: Any|None=None) -> None:
        if not str(api_id).strip(): raise ValueError("TELEGRAM_API_ID is required")
        if not api_hash.strip(): raise ValueError("TELEGRAM_API_HASH is required")
        try: from telethon.sync import TelegramClient
        except ImportError as exc: raise TelegramUserReaderError("Telethon is not installed. Install the project dependencies with: pip install -e .") from exc
        self.api_id=int(api_id); self.api_hash=api_hash.strip(); self.session=session.strip() or "data/telegram_user"
        Path(self.session).parent.mkdir(parents=True, exist_ok=True)
        self.client=client or TelegramClient(self.session,self.api_id,self.api_hash,receive_updates=False)
        if not self.client.is_connected(): self.client.connect()
        if not self.client.is_user_authorized():
            self.client.disconnect(); raise TelegramUserReaderError("Telegram user session is not authorized. Run python -m superdeal.telegram_login once.")
        self._last_message_ids: dict[str,int]={}
    def close(self) -> None:
        if self.client.is_connected(): self.client.disconnect()
    def _resolve_entity(self, configured: str) -> Any:
        target=normalize_user_channel(configured)
        try: return self.client.get_entity(target)
        except (ValueError,TypeError) as exc: raise TelegramUserReaderError(f"Could not resolve Telegram channel {configured!r}. Use a public @username/URL, a known chat ID, or a channel already visible to the account.") from exc
    @staticmethod
    def _canonical_channel(entity: Any, configured: str) -> str:
        username=getattr(entity,"username",None)
        if username: return f"@{username}"
        title=" ".join(str(getattr(entity,"title","")).split())
        return title or configured.strip()
    def fetch_messages(self, channel: str, *, limit: int=100) -> list[TelegramMessage]:
        return self.fetch_messages_for_channels((channel,),limit=limit).get(channel,[])
    def fetch_messages_for_channels(self, channels: Iterable[str], *, limit: int=100) -> dict[str,list[TelegramMessage]]:
        if limit<1: return {channel:[] for channel in channels}
        configured=tuple(channels); result={channel:[] for channel in configured}
        for channel in configured:
            entity=self._resolve_entity(channel); canonical=self._canonical_channel(entity,channel); last_id=self._last_message_ids.get(canonical,0)
            messages=list(self.client.iter_messages(entity,limit=limit)); fresh=[]
            for message in reversed(messages):
                message_id=int(getattr(message,"id",0) or 0)
                if message_id<=last_id: continue
                text=getattr(message,"raw_text",None) or getattr(message,"text",None) or ""
                if not str(text).strip(): continue
                observed_at=getattr(message,"date",None) or datetime.now(timezone.utc)
                if observed_at.tzinfo is None: observed_at=observed_at.replace(tzinfo=timezone.utc)
                fresh.append(TelegramMessage(channel=canonical,message_id=str(message_id),text=str(text),observed_at=observed_at.astimezone(timezone.utc).isoformat()))
            if messages:
                newest_id=max(int(getattr(message,"id",0) or 0) for message in messages); self._last_message_ids[canonical]=max(last_id,newest_id)
            result[channel].extend(fresh)
        return result
