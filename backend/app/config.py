from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://windfarm:windfarm@localhost:21464/windfarm_boarding"
    REDIS_URL: str = "redis://localhost:22464/0"
    APP_PORT: int = 19464
    CORS_ORIGINS: list[str] = ["http://localhost:20464", "http://localhost:18464"]

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
