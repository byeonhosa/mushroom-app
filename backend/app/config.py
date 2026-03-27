from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Mushroom Farm App API"
    app_version: str = "0.1.0"
    app_env: str = Field(default="development", validation_alias=AliasChoices("APP_ENV", "ENVIRONMENT"))
    database_url: str
    api_host: str = Field(default="0.0.0.0", validation_alias=AliasChoices("API_HOST", "HOST"))
    api_port: int = Field(default=8000, validation_alias=AliasChoices("API_PORT", "PORT"))
    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
