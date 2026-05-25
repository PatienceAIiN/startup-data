from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    DATABASE_URL_SYNC: str

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    R2_ACCOUNT_ID: str
    R2_ACCESS_KEY_ID: str
    R2_SECRET_ACCESS_KEY: str
    R2_BUCKET_NAME: str = "nexusintel-exports"
    R2_ENDPOINT_URL: str

    APP_ENV: str = "development"
    FRONTEND_URL: str = "http://localhost:4200"
    BACKEND_URL: str = "http://localhost:8000"
    CORS_ORIGINS: str = '["http://localhost:4200"]'

    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_AUTH: str = "10/minute"
    RATE_LIMIT_SCRAPER: str = "5/hour"

    ZAUBA_BASE_URL: str = "https://www.zaubacorp.com/company-list"
    DATAGOV_API_URL: str = "https://api.data.gov.in/resource/"
    DATAGOV_API_KEY: str = ""
    SCRAPE_MAX_PAGES: int = 50
    SCRAPE_CONCURRENT_LIMIT: int = 3
    MATCH_CONFIDENCE_THRESHOLD: float = 0.75

    @property
    def cors_origins_list(self) -> List[str]:
        try:
            return json.loads(self.CORS_ORIGINS)
        except Exception:
            return [self.FRONTEND_URL]


settings = Settings()
