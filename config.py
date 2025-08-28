"""
Configuration module for Telegram Scraper
Manages environment variables and constants using Pydantic
"""

import os
from pathlib import Path
from typing import List
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable management"""

    # Telegram API credentials
    api_id: int = Field(default=0, description="Telegram API ID")
    api_hash: str = Field(default="", description="Telegram API Hash")
    phone: str = Field(default="", description="Phone number for Telegram")

    # Application settings
    data_folder: Path = Field(
        default=Path("data"), description="Data storage folder"
    )
    session_file_prefix: str = Field(
        default="telegram_session", description="Session file prefix"
    )

    # Processing settings
    fast_mode_delay: float = Field(
        default=0.1, description="Delay in fast mode (seconds)"
    )
    detailed_mode_delay: float = Field(
        default=0.5, description="Delay in detailed mode (seconds)"
    )
    api_delay: float = Field(
        default=0.2, description="API call delay (seconds)"
    )

    # Display settings
    max_common_groups: int = Field(
        default=5, description="Maximum common groups to display"
    )
    max_cache_groups: int = Field(
        default=10, description="Maximum groups to cache"
    )
    progress_update_frequency: int = Field(
        default=25, description="How often to update progress"
    )

    # CSV export settings
    csv_encoding: str = Field(default="UTF-8", description="CSV file encoding")
    csv_delimiter: str = Field(default=",", description="CSV delimiter")
    csv_line_terminator: str = Field(
        default="\n", description="CSV line terminator"
    )

    model_config = {"env_file": ".env", "case_sensitive": False}

    @field_validator("api_id", mode="before")
    @classmethod
    def validate_api_id(cls, v):
        if isinstance(v, str):
            try:
                return int(v)
            except ValueError:
                raise ValueError("API_ID must be a valid integer")
        return v

    @field_validator("data_folder", mode="before")
    @classmethod
    def validate_data_folder(cls, v):
        if isinstance(v, str):
            return Path(v)
        return v

    def ensure_data_folder(self) -> None:
        """Create data folder if it doesn't exist"""
        self.data_folder.mkdir(exist_ok=True)


class GamingKeywords:
    """Gaming and affiliate marketing keywords for detection"""

    KEYWORDS: List[str] = [
        # Core gaming terms
        "igaming",
        "casino",
        "bet",
        "betting",
        "poker",
        "slots",
        "gambling",
        "game",
        "games",
        "jackpot",
        "lottery",
        "roulette",
        "payments",
        "payment",
        # Cryptocurrency and trading
        "crypto",
        "bitcoin",
        "trading",
        "forex",
        # Affiliate marketing
        "affiliate",
        "партнер",
        # Russian gaming terms
        "казино",
        "ставки",
        "игры",
        "азарт",
        "криптовалюта",
        "трейдинг",
        "партнёрка",
        "реферал",
        "гемблинг",
        "букмекер",
        # English gaming terms
        "bookmaker",
        "спорт",
        "sport",
        "прогноз",
        "прогнозы",
        "капер",
        "capper",
        "tipster",
        "бинанс",
        "binance",
        "сигнал",
        # Brand and platform names
        "spin",
        "spinz",
        "vegas",
        "roll",
        "highroll",
        "betwin",
        "betwinner",
        "melbet",
        "1xbet",
        "1xcasino",
        # Business terms
        "cpa",
        "revshare",
        "traffic",
        "трафик",
        "arbitrage",
        "арбитраж",
        "sportsbook",
        "offers",
        "офферы",
        "офера",
        "manager",
        "менеджер",
        "leads",
        "леадс",
        "конверт",
        "conversion",
        "mediabuy",
        "медиабай",
        "webmaster",
        "вебмастер",
        "network",
        "сеть",
        "hybrid",
        "гибрид",
        "landing",
        "лендинг",
        "campaign",
        "кампании",
        "media",
        "медиа",
        "brand",
        "бренд",
        "investment",
        "инвест",
        "live",
        "deposit",
        "депозит",
        "bingo",
        "dice",
        "кости",
        "cards",
        "карты",
        "table",
        "столы",
        "wheel",
        "reel",
        "bizdev",
        "business development",
        "partners",
        "партнёры",
        "geo",
        "гео",
        "spend",
        "roi",
        "cpi",
        "cpl",
        "crg",
        "tier",
        "тир",
        "quality",
        "качество",
        "volume",
        "объем",
        "stable",
        "стабильный",
        "exclusive",
        "эксклюзив",
        "direct",
        "прямой",
        "advertiser",
        "рекламодатель",
        "performance",
        "перформанс",
        "profitable",
        "прибыльный",
        "scale",
        "масштаб",
        "budgets",
        "бюджеты",
    ]


# Global settings instance - initialized when imported
try:
    settings = Settings()
except Exception:
    # Settings will be loaded when .env file is available
    settings = None  # type: ignore
