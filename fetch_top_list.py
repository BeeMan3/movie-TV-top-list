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
from typing import List, Optional

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class ContentType(str, Enum):
    """Content type enumeration."""

    MOVIE = "movie"
    SERIES = "series"


class ContentItem(BaseModel):
    """Represents a movie or TV show item."""

    title: str = Field(..., min_length=1, description="Title of the content")
    year: Optional[str] = Field(None, description="Release year")
    type: ContentType = Field(..., description="Type of content")


class SimpleContentItem(BaseModel):
    """Simplified content item with just title."""

    title: str = Field(..., min_length=1, description="Title of the content")


class DetailedOutput(BaseModel):
    """Detailed output format with metadata."""

    last_updated: datetime = Field(default_factory=datetime.now)
    total_items: int = Field(..., ge=0)
    items: List[ContentItem] = Field(default_factory=list)


class ScraperConfig(BaseSettings):
    """Configuration for the scraper."""

    model_config = SettingsConfigDict(
        env_prefix="SCRAPER_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # List size configuration
    max_movies: int = Field(
        default=25, ge=1, le=100, description="Maximum number of movies to fetch"
    )
    max_tv_shows: int = Field(
        default=25, ge=1, le=100, description="Maximum number of TV shows to fetch"
    )
    max_total_items: int = Field(
        default=50, ge=1, le=200, description="Maximum total items in final list"
    )

    # Request configuration
    request_timeout: int = Field(
        default=15, ge=5, le=60, description="Request timeout in seconds"
    )
    request_delay: float = Field(
        default=2.0, ge=0.1, le=10.0, description="Delay between requests in seconds"
    )

    # URLs
    imdb_movies_url: HttpUrl = Field(
        default="https://www.imdb.com/chart/moviemeter/",
        description="IMDB popular movies URL",
    )
    imdb_tv_url: HttpUrl = Field(
        default="https://www.imdb.com/chart/tvmeter/",
        description="IMDB popular TV shows URL",
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
                    items.append(ContentItem(title=title, year="", type=content_type))

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

            # Try multiple selectors for robustness
            selectors = [
                "li.ipc-metadata-list-summary-item",
                "li.titleColumn",
                ".cli-title-link",
                ".ipc-title-link-wrapper",
            ]

            elements = []
            for selector in selectors:
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
