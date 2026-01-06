from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    BOT_TOKEN: str
    REDIS_URL: str
    AUTH_SERVICE_URL: str
    MAIN_MODULE_URL: str
    WEB_LOGIN_URL: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()