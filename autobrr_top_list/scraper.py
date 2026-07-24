import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import ScraperConfig
from .models import ContentItem, ContentType


class TMDbError(RuntimeError):
    """Raised when TMDb content cannot be fetched or validated safely."""


class TMDbClient:
    def __init__(self, config: ScraperConfig):
        self.config = config

    def _fetch_trending(
        self, content_type: ContentType, max_items: int
    ) -> list[ContentItem]:
        if not self.config.tmdb_api_key and not self.config.tmdb_read_access_token:
            raise TMDbError(
                "TMDB_API_KEY or TMDB_READ_ACCESS_TOKEN is required. Create a "
                "non-commercial credential at https://www.themoviedb.org/settings/api."
            )

        items: list[ContentItem] = []
        page_number = 1
        total_pages: int | None = None

        while len(items) < max_items and (
            total_pages is None or page_number <= total_pages
        ):
            payload = self._get_page(content_type, page_number)
            results = payload.get("results")
            if not isinstance(results, list):
                raise TMDbError(
                    f"TMDb {content_type.value} response did not contain a results list"
                )

            for result in results:
                item = self._to_content_item(result, content_type)
                if item is not None:
                    items.append(item)
                    if len(items) >= max_items:
                        return items

            total_pages = payload.get("total_pages")
            if not isinstance(total_pages, int) or total_pages < page_number:
                return items
            page_number += 1
            time.sleep(self.config.request_delay)

        return items

    def _get_page(self, content_type: ContentType, page_number: int) -> dict[str, Any]:
        media_type = "movie" if content_type == ContentType.MOVIE else "tv"
        query_params: dict[str, str | int] = {
            "language": "en-US",
            "page": page_number,
        }
        token = self.config.tmdb_read_access_token
        if token is None and self.config.tmdb_api_key:
            # TMDb Read Access Tokens are JWTs. Preserve compatibility with v3 API keys.
            if self.config.tmdb_api_key.startswith("eyJ"):
                token = self.config.tmdb_api_key
            else:
                query_params["api_key"] = self.config.tmdb_api_key
        query = urlencode(query_params)
        url = (
            f"{self.config.tmdb_base_url}/trending/{media_type}/"
            f"{self.config.tmdb_trending_window}?{query}"
        )
        last_error: Exception | None = None
        request = Request(url, headers={"Authorization": f"Bearer {token}"}) if token else url

        for attempt in range(1, self.config.request_retries + 1):
            try:
                with urlopen(request, timeout=self.config.request_timeout) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                if not isinstance(payload, dict):
                    raise TMDbError(
                        f"TMDb {content_type.value} response was not a JSON object"
                    )
                return payload
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt >= self.config.request_retries:
                    break
                print(
                    f"TMDb {content_type.value} request failed "
                    f"(attempt {attempt}/{self.config.request_retries}): {exc}. Retrying..."
                )
                time.sleep(self.config.retry_delay)

        raise TMDbError(
            f"Failed to fetch TMDb {content_type.value} trending page {page_number} "
            f"after {self.config.request_retries} attempts"
        ) from last_error

    def _to_content_item(
        self, result: Any, content_type: ContentType
    ) -> ContentItem | None:
        if not isinstance(result, dict):
            return None

        title_field = "title" if content_type == ContentType.MOVIE else "name"
        date_field = (
            "release_date" if content_type == ContentType.MOVIE else "first_air_date"
        )
        title = result.get(title_field)
        if not isinstance(title, str) or not title.strip():
            return None

        date = result.get(date_field)
        if not self._matches_year_filter(date):
            return None

        rating = result.get("vote_average")
        if not isinstance(rating, (int, float)) or isinstance(rating, bool):
            return None
        if not self._matches_rating_filter(float(rating)):
            return None

        return ContentItem(
            title=title.strip(), type=content_type, average_rating=float(rating)
        )

    def _matches_year_filter(self, date: Any) -> bool:
        if self.config.min_year is None and self.config.max_year is None:
            return True
        if not isinstance(date, str) or len(date) < 4 or not date[:4].isdigit():
            return False

        year = int(date[:4])
        return (self.config.min_year is None or year >= self.config.min_year) and (
            self.config.max_year is None or year <= self.config.max_year
        )

    def _matches_rating_filter(self, rating: float) -> bool:
        return (
            self.config.min_rating is None or rating >= self.config.min_rating
        ) and (self.config.max_rating is None or rating <= self.config.max_rating)

    def fetch_popular_movies(self) -> list[ContentItem]:
        return self._fetch_trending(ContentType.MOVIE, self.config.max_movies)

    def fetch_popular_tv_shows(self) -> list[ContentItem]:
        return self._fetch_trending(ContentType.SERIES, self.config.max_tv_shows)
