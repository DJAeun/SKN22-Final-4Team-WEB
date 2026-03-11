import logging
from typing import Optional

import httpx

from .base import MessengerAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://discord.com/api/v10"


class DiscordAdapter(MessengerAdapter):

    def __init__(self, token: str, http_client: httpx.AsyncClient) -> None:
        self._headers = {
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
        }
        self._client = http_client

    async def send_confirm_message(
        self,
        channel_id: str,
        user_id: str,
        job_id: str,
        title: str,
        script_summary: str,
        preview_url: Optional[str],
    ) -> str:
        content = (
            "🎬 **콘텐츠 제작이 완료되었습니다!**\n\n"
            f"📌 제목: {title}\n"
            f"📝 요약: {script_summary}\n\n"
            "승인하시면 각 SNS에 자동 업로드됩니다."
        )
        payload = {
            "content": content,
            "components": [
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 2,
                            "label": "✅ 승인하기",
                            "style": 3,
                            "custom_id": f"approve:{job_id}",
                        },
                        {
                            "type": 2,
                            "label": "✏️ 수정 지시",
                            "style": 2,
                            "custom_id": f"revise:{job_id}",
                        },
                    ],
                }
            ],
        }
        resp = await self._client.post(
            f"{BASE_URL}/channels/{channel_id}/messages",
            json=payload,
            headers=self._headers,
        )
        resp.raise_for_status()
        data = resp.json()
        message_id = str(data["id"])
        logger.info("[discord] send_confirm_message job=%s message_id=%s", job_id, message_id)
        return message_id

    async def send_text_message(self, channel_id: str, text: str) -> None:
        payload = {"content": text}
        resp = await self._client.post(
            f"{BASE_URL}/channels/{channel_id}/messages",
            json=payload,
            headers=self._headers,
        )
        resp.raise_for_status()
        logger.info("[discord] send_text_message channel=%s", channel_id)

    async def remove_buttons(
        self,
        channel_id: str,
        message_id: str,
        replacement_text: str,
    ) -> None:
        # 버튼 제거 (컴포넌트를 빈 배열로 PATCH)
        try:
            resp = await self._client.patch(
                f"{BASE_URL}/channels/{channel_id}/messages/{message_id}",
                json={"components": []},
                headers=self._headers,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.warning("[discord] remove_buttons patch failed: %s", e)

        await self.send_text_message(channel_id, replacement_text)
        logger.info("[discord] remove_buttons channel=%s message_id=%s", channel_id, message_id)
