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
    # The zone in which "today" is worked out for run codes and reports.
    farm_timezone: str = "America/New_York"

    # --- Sign-in (SRS 4.14) ---
    session_cookie_name: str = "mfa_session"
    # A session ends after this many days without use, and in any case this
    # many days after sign-in.
    session_idle_days: int = 14
    session_max_days: int = 30
    # bcrypt work factor. Tests lower it; production keeps the default.
    password_hash_rounds: int = 12
    # Failed sign-ins allowed inside the window before further attempts are refused.
    login_max_failures_per_email: int = 5
    login_max_failures_per_ip: int = 20
    login_window_minutes: int = 15
    # The public hostname, when one is configured (APP_HOSTNAME). Requests whose
    # Origin is https://<hostname> are accepted as coming from the app itself.
    app_hostname: str = ""
    # First administrator, created when no user exists (see app.manage).
    bootstrap_admin_email: str = ""
    bootstrap_admin_password: str = ""
    # Shown in the menu and beside each event. The person can change it.
    bootstrap_admin_name: str = "Owner"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def trusted_origins(self) -> set[str]:
        """Origins a state-changing request may come from, besides the request's own host."""
        origins = {origin.rstrip("/") for origin in self.cors_origin_list}
        if self.app_hostname.strip():
            origins.add(f"https://{self.app_hostname.strip()}")
        return origins

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


settings = Settings()
