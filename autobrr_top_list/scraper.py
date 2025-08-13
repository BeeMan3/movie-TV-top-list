import json
import re
from typing import Any, List, Optional

import requests
from bs4 import BeautifulSoup

from .config import ScraperConfig
from .models import ContentItem, ContentType, ItemListLD, LdItem, LdListItem


class IMDBScraper:
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
        items: List[ContentItem] = []

        def is_movie_type(value: Optional[str]) -> bool:
            return bool(value) and value.lower() in {
                "movie",
                "videoobject",
                "creativework",
            }

        def is_series_type(value: Optional[str]) -> bool:
            return bool(value) and value.lower() in {
                "tvseries",
                "tvepisode",
                "tvseason",
                "tvshow",
            }

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
                if not isinstance(block, dict) or block.get("@type") != "ItemList":
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

                    if not ld_item or not type_matches(content_type, ld_item.type):
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
        items: List[ContentItem] = []
        title_selectors = [
            "h3.ipc-title__text",
            ".ipc-title__text",
            ".cli-title",
            "a",
        ]

        for element in elements[: max_items * 2]:
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
        return items

    def _scrape_imdb_list(
        self, url: str, content_type: ContentType, max_items: int
    ) -> List[ContentItem]:
        response = self.session.get(str(url), timeout=self.config.request_timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        ld_items = self._extract_from_ld_json(soup, content_type, max_items)
        if ld_items:
            return ld_items

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
                break

        if not elements:
            return []

        return self._extract_titles_from_elements(elements, content_type, max_items)

    def fetch_popular_movies(self) -> List[ContentItem]:
        return self._scrape_imdb_list(
            self.config.imdb_movies_url, ContentType.MOVIE, self.config.max_movies
        )

    def fetch_popular_tv_shows(self) -> List[ContentItem]:
        return self._scrape_imdb_list(
            self.config.imdb_tv_url, ContentType.SERIES, self.config.max_tv_shows
        )
