from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gateway_port: int = 8080
    gateway_internal_secret: str

    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "ai_influencer"
    postgres_user: str = "aiuser"
    postgres_password: str

    discord_bot_token: str = ""

    n8n_wf01_webhook_url: str = "http://n8n:5678/webhook/wf-01-input"
    n8n_wf05_webhook_url: str = "http://n8n:5678/webhook/wf-05-confirm"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
