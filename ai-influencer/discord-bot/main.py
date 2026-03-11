import asyncio
import logging
import uuid
from typing import Optional

import discord
import httpx
from discord.ext import commands
from pydantic_settings import BaseSettings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# 설정
# ─────────────────────────────────────────

class Settings(BaseSettings):
    discord_bot_token: str
    discord_allowed_user_ids: str = ""
    gateway_url: str = "http://messenger-gateway:8080"
    gateway_internal_secret: str

    class Config:
        env_file = ".env"
        case_sensitive = False


config = Settings()
ALLOWED_USER_IDS: set[str] = {
    uid.strip() for uid in config.discord_allowed_user_ids.split(",") if uid.strip()
}


# ─────────────────────────────────────────
# Gateway 클라이언트 헬퍼
# ─────────────────────────────────────────

_gateway_client: Optional[httpx.AsyncClient] = None


def get_gateway_client() -> httpx.AsyncClient:
    global _gateway_client
    if _gateway_client is None:
        _gateway_client = httpx.AsyncClient(
            base_url=config.gateway_url,
            headers={"X-Internal-Secret": config.gateway_internal_secret},
            timeout=15.0,
        )
    return _gateway_client


async def gateway_call(path: str, payload: dict) -> None:
    try:
        resp = await get_gateway_client().post(path, json=payload)
        resp.raise_for_status()
    except Exception as e:
        logger.error("[discord] gateway_call %s failed: %s", path, e)
        raise


# ─────────────────────────────────────────
# 인메모리 수정 대기 상태 (pending_store)
# ─────────────────────────────────────────

revision_pending: dict[str, str] = {}  # user_id -> job_id


# ─────────────────────────────────────────
# Discord Bot
# ─────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready() -> None:
    logger.info("[discord] bot online: %s", bot.user)


@bot.event
async def on_message(message: discord.Message) -> None:
    # 봇 자신의 메시지 무시
    if message.author.bot:
        return

    user_id = str(message.author.id)

    # 허용 사용자 확인
    if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
        logger.info("[discord] unauthorized user_id=%s", user_id)
        return

    # 수정 지시 텍스트 대기 중인 경우
    if user_id in revision_pending:
        job_id = revision_pending.pop(user_id)
        try:
            await gateway_call(
                "/internal/confirm-action",
                {
                    "job_id": job_id,
                    "action": "revision_requested",
                    "revision_note": message.content,
                },
            )
        except Exception:
            pass
        return

    # 일반 콘텐츠 요청 처리
    job_id = str(uuid.uuid4())
    image_url = message.attachments[0].url if message.attachments else None

    try:
        await gateway_call(
            "/internal/message",
            {
                "job_id": job_id,
                "messenger_source": "discord",
                "messenger_user_id": user_id,
                "messenger_channel_id": str(message.channel.id),
                "concept_text": message.content,
                "ref_image_url": image_url,
                "character_id": "default-character",
            },
        )
    except Exception:
        await message.channel.send("요청 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")


@bot.event
async def on_interaction(interaction: discord.Interaction) -> None:
    # 버튼 클릭(컴포넌트 인터랙션)만 처리
    if interaction.type != discord.InteractionType.component:
        return

    custom_id: str = interaction.data.get("custom_id", "")
    if ":" not in custom_id:
        await interaction.response.send_message("잘못된 요청입니다.", ephemeral=True)
        return

    action, job_id = custom_id.split(":", 1)
    user_id = str(interaction.user.id)

    if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
        await interaction.response.send_message("권한이 없습니다.", ephemeral=True)
        return

    # Discord 3초 응답 제한 — 먼저 defer
    await interaction.response.defer()

    if action == "approve":
        try:
            await gateway_call(
                "/internal/confirm-action",
                {"job_id": job_id, "action": "approved"},
            )
        except Exception as e:
            await interaction.channel.send(f"오류가 발생했습니다: {e}")

    elif action == "revise":
        revision_pending[user_id] = job_id
        await interaction.channel.send("✏️ 어떤 점을 수정할까요? 구체적으로 입력해주세요.")


# ─────────────────────────────────────────
# 진입점
# ─────────────────────────────────────────

async def main() -> None:
    try:
        await bot.start(config.discord_bot_token)
    finally:
        if _gateway_client:
            await _gateway_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
