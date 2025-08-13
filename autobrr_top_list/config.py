from datetime import datetime
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ScraperConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SCRAPER_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        cli_parse_args=True,
    )

    max_movies: int = Field(default=50, ge=1, le=100)
    max_tv_shows: int = Field(default=50, ge=1, le=100)
    max_total_items: int = Field(default=100, ge=1, le=200)

    min_year: Optional[int] = Field(
        default_factory=lambda: datetime.now().year - 5, ge=1900
    )
    max_year: Optional[int] = Field(default=None, ge=1900)
    min_rating: Optional[float] = Field(default=6.0, ge=1.0, le=10.0)
    max_rating: Optional[float] = Field(default=None, ge=1.0, le=10.0)

    request_timeout: int = Field(default=15, ge=5, le=60)
    request_delay: float = Field(default=2.0, ge=0.1, le=10.0)

    imdb_movies_base_url: str = Field(default="https://www.imdb.com/chart/moviemeter/")
    imdb_tv_base_url: str = Field(default="https://www.imdb.com/chart/tvmeter/")

    simple_output_file: str = Field(default="top-list.json")
    detailed_output_file: str = Field(default="top-list-detailed.json")

    user_agent: str = Field(
        default="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    def _build_url_with_filters(self, base_url: str) -> str:
        url_parts = [base_url.rstrip("/")]
        query_params = []

        if self.min_year is not None or self.max_year is not None:
            year_filter = ""
            if self.min_year is not None:
                year_filter += str(self.min_year)
            year_filter += ","
            if self.max_year is not None:
                year_filter += str(self.max_year)
            query_params.append(f"year={year_filter}")

        if self.min_rating is not None or self.max_rating is not None:
            rating_filter = ""
            if self.min_rating is not None:
                rating_filter += str(self.min_rating)
            rating_filter += ","
            if self.max_rating is not None:
                rating_filter += str(self.max_rating)
            query_params.append(f"user_rating={rating_filter}")

        if query_params:
            return f"{url_parts[0]}/?{'&'.join(query_params)}"
        return base_url

    @property
    def imdb_movies_url(self) -> str:
        return self._build_url_with_filters(self.imdb_movies_base_url)

    @property
    def imdb_tv_url(self) -> str:
        return self._build_url_with_filters(self.imdb_tv_base_url)
