import json
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class TelegramClient:
    """Low-level Telegram Bot HTTP API wrapper with a shared AsyncClient."""

    def __init__(self):
        self.bot_token: str = settings.TELEGRAM_BOT_TOKEN
        self.base_url: str = f"{settings.TELEGRAM_API_URL}{self.bot_token}"
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        """Lazy-initialize and return a shared AsyncClient."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def send_message(self, chat_id: int, text: str) -> int | None:
        """POST sendMessage and return the message_id, or None on failure."""
        try:
            client = self._get_client()
            data = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
            response = await client.post(f"{self.base_url}/sendMessage", data=data)
            response.raise_for_status()
            msg_id = response.json().get("result", {}).get("message_id")
            logger.debug(f"[TG] Message sent (chat_id={chat_id}, message_id={msg_id})")
            return msg_id
        except Exception as e:
            logger.error(f"[TG] Failed to send message: {e}")
            return None

    async def delete_message(self, chat_id: int, message_id: int) -> None:
        """POST deleteMessage. Errors are swallowed and logged."""
        try:
            client = self._get_client()
            data = {"chat_id": chat_id, "message_id": message_id}
            response = await client.post(f"{self.base_url}/deleteMessage", data=data)
            response.raise_for_status()
            logger.debug(f"[TG] Message deleted (chat_id={chat_id}, message_id={message_id})")
        except Exception as e:
            logger.debug(f"[TG] Failed to delete message (ignored): {e}")

    async def send_inline_keyboard(
        self, chat_id: int, text: str, buttons: list[list[dict]]
    ) -> int | None:
        """POST sendMessage with an InlineKeyboardMarkup reply_markup."""
        try:
            client = self._get_client()
            data = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "reply_markup": json.dumps({"inline_keyboard": buttons}),
            }
            response = await client.post(f"{self.base_url}/sendMessage", data=data)
            response.raise_for_status()
            msg_id = response.json().get("result", {}).get("message_id")
            logger.debug(f"[TG] Inline keyboard message sent (chat_id={chat_id})")
            return msg_id
        except Exception as e:
            logger.error(f"[TG] Failed to send inline keyboard message: {e}")
            return None

    async def answer_callback_query(self, callback_query_id: str) -> None:
        """POST answerCallbackQuery. Errors are swallowed and logged."""
        try:
            client = self._get_client()
            await client.post(
                f"{self.base_url}/answerCallbackQuery",
                data={"callback_query_id": callback_query_id},
            )
            logger.debug(f"[TG] Answered callback query (id={callback_query_id})")
        except Exception as e:
            logger.debug(f"[TG] Failed to answer callback query (ignored): {e}")

    async def download_file(self, file_id: str) -> bytes:
        """Download a file from Telegram by file_id. Raises on error."""
        client = self._get_client()
        path_resp = await client.get(f"{self.base_url}/getFile", params={"file_id": file_id})
        path_resp.raise_for_status()
        file_path = path_resp.json()["result"]["file_path"]

        download_url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
        img_resp = await client.get(download_url)
        img_resp.raise_for_status()
        logger.debug(f"[TG] File downloaded (file_id={file_id}, size={len(img_resp.content)} bytes)")
        return img_resp.content

    async def close(self) -> None:
        """Close the underlying AsyncClient if open."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.debug("[TG] HTTP client closed")
