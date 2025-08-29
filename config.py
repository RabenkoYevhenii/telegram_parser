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
    sessions_folder: Path = Field(
        default=Path("sessions"), description="Sessions storage folder"
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

    # OpenRouter AI settings
    openrouter_api_key: str = Field(
        default="", description="OpenRouter API key"
    )
    ai_model: str = Field(
        default="google/gemini-2.0-flash-exp:free",
        description="AI model to use for validation",
    )
    ai_validation_prompt: str = Field(
        default="""You are an expert in analyzing user data to determine if they are potential customers for payment services and traffic monetization.

Analyze the provided user data including their bio, messages, and activity patterns. Determine if this user is genuinely looking for traffic arbitrage opportunities, affiliate marketing partnerships, or payment processing services for specific geographical markets.

Look for indicators such as:
- Discussion of traffic sources, conversions, or CPA marketing
- Mentions of specific geographical markets (GEOs)
- Interest in payment processing, affiliate networks, or monetization
- Professional communication about business partnerships
- Technical discussions about conversion tracking or analytics

Respond with only a JSON object containing a single boolean field:
{"valid": true} if the user appears to be a legitimate potential customer
{"valid": false} if the user does not meet the criteria

User data to analyze:""",
        description="AI prompt for user validation",
    )

    # Google Sheets settings
    google_auth_method: str = Field(
        default="service_account",
        description="Google authentication method: 'service_account', 'oauth2_file', or 'oauth2_inline'",
    )
    google_credentials_file: str = Field(
        default="credentials.json",
        description="Path to Google service account credentials JSON file (for service_account auth)",
    )
    google_oauth_credentials_file: str = Field(
        default="oauth2_credentials.json",
        description="Path to OAuth 2.0 client credentials JSON file (for oauth2_file auth)",
    )
    google_oauth_client_id: str = Field(
        default="",
        description="OAuth 2.0 Client ID (for oauth2_inline auth)",
    )
    google_oauth_client_secret: str = Field(
        default="",
        description="OAuth 2.0 Client Secret (for oauth2_inline auth)",
    )
    google_token_file: str = Field(
        default="token.json",
        description="Path to store OAuth 2.0 access token (for oauth2 auth)",
    )
    google_spreadsheet_id: str = Field(
        default="",
        description="Default Google Spreadsheet ID to append data to",
    )
    google_worksheet_name: str = Field(
        default="Validated Users",
        description="Worksheet name for validated users",
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

    @field_validator("sessions_folder", mode="before")
    @classmethod
    def validate_sessions_folder(cls, v):
        if isinstance(v, str):
            return Path(v)
        return v

    def ensure_folders(self) -> None:
        """Create data and sessions folders if they don't exist"""
        self.data_folder.mkdir(exist_ok=True)
        self.sessions_folder.mkdir(exist_ok=True)

    # Backward compatibility
    def ensure_data_folder(self) -> None:
        """Create data folder if it doesn't exist (deprecated - use ensure_folders)"""
        self.ensure_folders()


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
        "traf",
        "траф",
        "arbitrage",
        "арбитраж",
        "sportsbook",
        "offers",
        "офферы",
        "офера",
        "manager",
        "менеджер",
        "leads",
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
        "wheel",
        "reel",
        "bizdev",
        "business development",
        "geo",
        "гео",
    ]


# Global settings instance - initialized when imported
try:
    settings = Settings()
except Exception:
    # Settings will be loaded when .env file is available
    settings = None  # type: ignore
