#!/usr/bin/env python3
"""
Fetch top movies and series from IMDB popular lists.
Combines movies and TV shows into a single ranked list.
"""

import json
import re
import time
from datetime import datetime
from enum import Enum
from typing import Any, List, Optional, Union

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict


class ContentType(str, Enum):
    """Content type enumeration."""

    MOVIE = "movie"
    SERIES = "series"


class ContentItem(BaseModel):
    """Represents a movie or TV show item."""

    title: str = Field(..., min_length=1, description="Title of the content")
    type: ContentType = Field(..., description="Type of content")
    average_rating: Optional[float] = Field(
        default=None, description="Average user rating when available"
    )


class SimpleContentItem(BaseModel):
    """Simplified content item with just title."""

    title: str = Field(..., min_length=1, description="Title of the content")


class DetailedOutput(BaseModel):
    """Detailed output format with metadata."""

    last_updated: datetime = Field(default_factory=datetime.now)
    total_items: int = Field(..., ge=0)
    items: List[ContentItem] = Field(default_factory=list)


class AggregateRating(BaseModel):
    """Schema.org AggregateRating subset used by IMDB JSON-LD."""

    model_config = ConfigDict(populate_by_name=True)

    type: Optional[str] = Field(default=None, alias="@type")
    ratingValue: Optional[Union[str, float]] = None

    def rating_value_as_float(self) -> Optional[float]:
        if self.ratingValue is None:
            return None
        try:
            return float(self.ratingValue)
        except (TypeError, ValueError):
            return None


class LdItem(BaseModel):
    """Minimal representation of Movie/TV item in JSON-LD."""

    model_config = ConfigDict(populate_by_name=True)

    type: Optional[str] = Field(default=None, alias="@type")
    name: Optional[str] = None
    alternateName: Optional[str] = None
    headline: Optional[str] = None
    aggregateRating: Optional[AggregateRating] = None


class LdListItem(BaseModel):
    """ItemList element which usually wraps an `item`."""

    model_config = ConfigDict(populate_by_name=True)

    type: Optional[str] = Field(default=None, alias="@type")
    position: Optional[int] = None
    item: Optional[Union[LdItem, dict]] = None


class ItemListLD(BaseModel):
    """JSON-LD ItemList wrapper shipped by IMDB pages."""

    model_config = ConfigDict(populate_by_name=True)

    type: Optional[str] = Field(default=None, alias="@type")
    itemListElement: List[Union[LdListItem, LdItem, dict]] = Field(default_factory=list)


class ScraperConfig(BaseSettings):
    """Configuration for the scraper."""

    model_config = SettingsConfigDict(
        env_prefix="SCRAPER_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        cli_parse_args=True,
    )

    # List size configuration
    max_movies: int = Field(
        default=50, ge=1, le=100, description="Maximum number of movies to fetch"
    )
    max_tv_shows: int = Field(
        default=50, ge=1, le=100, description="Maximum number of TV shows to fetch"
    )
    max_total_items: int = Field(
        default=100, ge=1, le=200, description="Maximum total items in final list"
    )

    # Filter configuration
    min_year: Optional[int] = Field(
        default_factory=lambda: datetime.now().year - 5,
        ge=1900,
        description="Minimum release year filter (None to disable)",
    )
    max_year: Optional[int] = Field(
        default=None,
        ge=1900,
        description="Maximum release year filter (None for current year)",
    )
    min_rating: Optional[float] = Field(
        default=6.0,
        ge=1.0,
        le=10.0,
        description="Minimum user rating filter (None to disable)",
    )
    max_rating: Optional[float] = Field(
        default=None,
        ge=1.0,
        le=10.0,
        description="Maximum user rating filter (None to disable)",
    )

    # Request configuration
    request_timeout: int = Field(
        default=15, ge=5, le=60, description="Request timeout in seconds"
    )
    request_delay: float = Field(
        default=2.0, ge=0.1, le=10.0, description="Delay between requests in seconds"
    )

    # Base URLs (will be modified with filters)
    imdb_movies_base_url: str = Field(
        default="https://www.imdb.com/chart/moviemeter/",
        description="IMDB popular movies base URL",
    )
    imdb_tv_base_url: str = Field(
        default="https://www.imdb.com/chart/tvmeter/",
        description="IMDB popular TV shows base URL",
    )

    # Output configuration
    simple_output_file: str = Field(
        default="top-list.json", description="Simple output filename"
    )
    detailed_output_file: str = Field(
        default="top-list-detailed.json", description="Detailed output filename"
    )

    # User agent for requests
    user_agent: str = Field(
        default="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        description="User agent string for requests",
    )

    def _build_url_with_filters(self, base_url: str) -> str:
        """Build URL with year and rating filters applied."""
        url_parts = [base_url.rstrip("/")]
        query_params = []

        # Add year filter
        if self.min_year is not None or self.max_year is not None:
            year_filter = ""
            if self.min_year is not None:
                year_filter += str(self.min_year)
            year_filter += ","
            if self.max_year is not None:
                year_filter += str(self.max_year)
            query_params.append(f"year={year_filter}")

        # Add rating filter
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
        """Get the movies URL with filters applied."""
        return self._build_url_with_filters(self.imdb_movies_base_url)

    @property
    def imdb_tv_url(self) -> str:
        """Get the TV shows URL with filters applied."""
        return self._build_url_with_filters(self.imdb_tv_base_url)


class IMDBScraper:
    """IMDB scraper for fetching popular content."""

    def __init__(self, config: ScraperConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": config.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )

    def _extract_from_ld_json(
        self, soup: BeautifulSoup, content_type: ContentType, max_items: int
    ) -> List[ContentItem]:
        """Extract items from JSON-LD ItemList with Pydantic validation."""
        items: List[ContentItem] = []

        def is_movie_type(value: Optional[str]) -> bool:
            if not value:
                return False
            return value.lower() in {"movie", "videoobject", "creativework"}

        def is_series_type(value: Optional[str]) -> bool:
            if not value:
                return False
            return value.lower() in {"tvseries", "tvepisode", "tvseason", "tvshow"}

        def type_matches(requested: ContentType, candidate_type: Optional[str]) -> bool:
            if candidate_type is None:
                return True
            return (
                is_movie_type(candidate_type)
                if requested == ContentType.MOVIE
                else is_series_type(candidate_type)
            )

        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            raw_text = script.get_text() or ""
            if not raw_text.strip():
                continue
            try:
                parsed = json.loads(raw_text)
            except json.JSONDecodeError:
                continue

            blocks: List[Any] = parsed if isinstance(parsed, list) else [parsed]
            for block in blocks:
                if not isinstance(block, dict):
                    continue
                if block.get("@type") != "ItemList":
                    continue
                try:
                    item_list = ItemListLD.model_validate(block)
                except Exception:
                    continue

                for element in item_list.itemListElement:
                    ld_item: Optional[LdItem] = None
                    if isinstance(element, LdListItem):
                        if isinstance(element.item, LdItem):
                            ld_item = element.item
                        elif isinstance(element.item, dict):
                            try:
                                ld_item = LdItem.model_validate(element.item)
                            except Exception:
                                ld_item = None
                    elif isinstance(element, LdItem):
                        ld_item = element
                    elif isinstance(element, dict):
                        try:
                            ld_item = LdItem.model_validate(element)
                        except Exception:
                            ld_item = None

                    if not ld_item:
                        continue

                    if not type_matches(content_type, ld_item.type):
                        continue

                    title = ld_item.name or ld_item.alternateName or ld_item.headline
                    if not title:
                        continue
                    cleaned_title = re.sub(r"^\d+\.\s*", "", str(title).strip())

                    rating = (
                        ld_item.aggregateRating.rating_value_as_float()
                        if ld_item.aggregateRating is not None
                        else None
                    )

                    items.append(
                        ContentItem(
                            title=cleaned_title,
                            type=content_type,
                            average_rating=rating,
                        )
                    )
                    if len(items) >= max_items:
                        return items

        return items

    def _extract_titles_from_elements(
        self, elements: List, content_type: ContentType, max_items: int
    ) -> List[ContentItem]:
        """Extract titles from BeautifulSoup elements."""
        items = []

        title_selectors = [
            "h3.ipc-title__text",
            ".ipc-title__text",
            ".cli-title",
            "a",
        ]

        for i, element in enumerate(
            elements[: max_items * 2]
        ):  # Get extra to account for filtering
            try:
                title = None

                for title_sel in title_selectors:
                    title_elem = element.select_one(title_sel)
                    if title_elem:
                        title_text = title_elem.get_text(strip=True)
                        title = re.sub(r"^\d+\.\s*", "", title_text)
                        break

                if title and len(title) > 1:
                    items.append(
                        ContentItem(title=title, type=content_type, average_rating=None)
                    )

                    if len(items) >= max_items:
                        break

            except Exception as e:
                print(f"Error processing {content_type.value} element {i}: {e}")
                continue

        return items

    def _scrape_imdb_list(
        self, url: str, content_type: ContentType, max_items: int
    ) -> List[ContentItem]:
        """Scrape an IMDB list for content."""
        try:
            print(f"Fetching IMDB {content_type.value}s from {url}...")

            response = self.session.get(str(url), timeout=self.config.request_timeout)
            response.raise_for_status()

            print(f"Response status: {response.status_code}")
            soup = BeautifulSoup(response.content, "html.parser")

            # First try to parse the embedded JSON-LD which contains the full list
            ld_items = self._extract_from_ld_json(soup, content_type, max_items)
            if ld_items:
                print(f"Found {len(ld_items)} {content_type.value}s using JSON-LD")
                return ld_items

            # Try multiple selectors for robustness
            selectors = [
                "li.ipc-metadata-list-summary-item",
                "li.titleColumn",
                ".cli-title-link",
                ".ipc-title-link-wrapper",
            ]

            elements = []
            for selector in selectors:
                # Do not limit here; we will cap after extraction
                elements = soup.select(selector)
                if elements:
                    print(
                        f"Found {len(elements)} {content_type.value}s using selector: {selector}"
                    )
                    break

            if not elements:
                print(f"No {content_type.value} elements found with any selector")
                return []

            items = self._extract_titles_from_elements(
                elements, content_type, max_items
            )
            print(f"Successfully extracted {len(items)} {content_type.value}s")
            return items

        except Exception as e:
            print(f"Error fetching {content_type.value}s: {e}")
            return []

    def fetch_popular_movies(self) -> List[ContentItem]:
        """Fetch popular movies from IMDB."""
        return self._scrape_imdb_list(
            self.config.imdb_movies_url, ContentType.MOVIE, self.config.max_movies
        )

    def fetch_popular_tv_shows(self) -> List[ContentItem]:
        """Fetch popular TV shows from IMDB."""
        return self._scrape_imdb_list(
            self.config.imdb_tv_url, ContentType.SERIES, self.config.max_tv_shows
        )


class ContentProcessor:
    """Process and combine content lists."""

    @staticmethod
    def combine_and_rank_lists(
        movies: List[ContentItem], tv_shows: List[ContentItem], max_items: int
    ) -> List[ContentItem]:
        """Combine movies and TV shows, interleaving them for variety."""
        combined = []
        max_length = max(len(movies), len(tv_shows))

        for i in range(max_length):
            # Alternate between movies and TV shows
            if i < len(movies):
                combined.append(movies[i])
            if i < len(tv_shows):
                combined.append(tv_shows[i])

            if len(combined) >= max_items:
                break

        return combined[:max_items]

    @staticmethod
    def create_simple_output(items: List[ContentItem]) -> List[SimpleContentItem]:
        """Create simplified output with just titles."""
        return [SimpleContentItem(title=item.title) for item in items]


class OutputManager:
    """Manage output file creation."""

    def __init__(self, config: ScraperConfig):
        self.config = config

    def save_outputs(self, items: List[ContentItem]) -> None:
        """Save both simple and detailed output files."""
        # Create simple output format
        simple_items = ContentProcessor.create_simple_output(items)
        simple_data = [item.model_dump() for item in simple_items]

        # Save simple format
        with open(self.config.simple_output_file, "w", encoding="utf-8") as f:
            json.dump(simple_data, f, indent=2, ensure_ascii=False)

        # Create detailed output format
        detailed_output = DetailedOutput(total_items=len(items), items=items)

        # Save detailed format
        with open(self.config.detailed_output_file, "w", encoding="utf-8") as f:
            json.dump(
                detailed_output.model_dump(mode="json"),
                f,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

        print(f"Successfully created list with {len(items)} items")
        print("Files created:")
        print(f"- {self.config.simple_output_file} (simple format)")
        print(f"- {self.config.detailed_output_file} (with metadata)")


def main() -> None:
    """Main function to orchestrate the scraping process."""
    # Load configuration
    config = ScraperConfig()

    print("Starting content fetching process...")
    print(
        f"Configuration: max_movies={config.max_movies}, max_tv_shows={config.max_tv_shows}, max_total={config.max_total_items}"
    )

    # Display filter configuration
    filters_applied = []
    if config.min_year is not None:
        filters_applied.append(f"min_year={config.min_year}")
    if config.max_year is not None:
        filters_applied.append(f"max_year={config.max_year}")
    if config.min_rating is not None:
        filters_applied.append(f"min_rating={config.min_rating}")
    if config.max_rating is not None:
        filters_applied.append(f"max_rating={config.max_rating}")

    if filters_applied:
        print(f"Active filters: {', '.join(filters_applied)}")
        print(f"Movies URL: {config.imdb_movies_url}")
        print(f"TV Shows URL: {config.imdb_tv_url}")
    else:
        print("No filters applied - fetching all popular content")

    # Initialize components
    scraper = IMDBScraper(config)
    processor = ContentProcessor()
    output_manager = OutputManager(config)

    try:
        # Fetch content
        movies = scraper.fetch_popular_movies()

        # Add delay between requests to be respectful
        time.sleep(config.request_delay)

        tv_shows = scraper.fetch_popular_tv_shows()

        print(f"Found {len(movies)} movies and {len(tv_shows)} TV shows")

        # Combine and process
        combined_list = processor.combine_and_rank_lists(
            movies, tv_shows, config.max_total_items
        )

        # Save outputs
        output_manager.save_outputs(combined_list)

    except Exception as e:
        print(f"Error during execution: {e}")
        # Save empty output on failure
        output_manager.save_outputs([])


if __name__ == "__main__":
    main()
