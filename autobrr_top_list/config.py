from datetime import datetime

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ScraperConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SCRAPER_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_parse_none_str="None",
        case_sensitive=False,
        cli_parse_args=True,
        populate_by_name=True,
    )

    max_movies: int = Field(default=50, ge=1, le=1000)
    max_tv_shows: int = Field(default=50, ge=1, le=200)
    max_total_items: int = Field(default=100, ge=1, le=400)

    min_year: int | None = Field(
        default_factory=lambda: datetime.now().year - 5, ge=1900
    )
    max_year: int | None = Field(default=None, ge=1900)
    min_rating: float | None = Field(default=6.0, ge=1.0, le=10.0)
    max_rating: float | None = Field(default=None, ge=1.0, le=10.0)
    require_home_release: bool = Field(default=False)
    home_release_region: str = Field(default="US", pattern=r"^[A-Z]{2}$")
    popular_min_vote_count: int = Field(default=300, ge=0)

    request_timeout: int = Field(default=15, ge=5, le=60)
    request_delay: float = Field(default=2.0, ge=0.1, le=10.0)
    request_retries: int = Field(default=3, ge=1, le=10)
    retry_delay: float = Field(default=2.0, ge=0.1, le=30.0)
    tmdb_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("TMDB_API_KEY", "SCRAPER_TMDB_API_KEY"),
    )
    tmdb_read_access_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "TMDB_READ_ACCESS_TOKEN", "SCRAPER_TMDB_READ_ACCESS_TOKEN"
        ),
    )
    tmdb_base_url: str = Field(default="https://api.themoviedb.org/3")
    tmdb_trending_window: str = Field(default="week", pattern="^(day|week)$")

    simple_output_file: str = Field(default="top-list.json")
    detailed_output_file: str = Field(default="top-list-detailed.json")
