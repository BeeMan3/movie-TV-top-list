import json
import re
import time
from typing import Any, List, Optional

from bs4 import BeautifulSoup
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from .config import ScraperConfig
from .models import ContentItem, ContentType, ItemListLD, LdItem, LdListItem


class ScraperError(RuntimeError):
    """Raised when IMDb content cannot be fetched or parsed safely."""


class IMDBScraper:
    def __init__(self, config: ScraperConfig):
        self.config = config

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
        html = self._fetch_rendered_html(url, content_type)

        soup = BeautifulSoup(html, "html.parser")
        if not soup.find("body"):
            raise ScraperError(
                f"IMDb {content_type.value} page did not contain a valid HTML body: {url}"
            )
        if self._is_bot_challenge(soup):
            raise ScraperError(
                f"IMDb {content_type.value} page returned a bot challenge instead of chart HTML; "
                f"the runner IP or request fingerprint is likely blocked: {url}"
            )

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
            raise ScraperError(
                f"IMDb {content_type.value} page layout was not recognized: no known list selectors matched {url}"
            )

        items = self._extract_titles_from_elements(elements, content_type, max_items)
        if not items:
            raise ScraperError(
                f"IMDb {content_type.value} page matched list containers but no titles could be extracted: {url}"
            )
        return items

    def _fetch_rendered_html(self, url: str, content_type: ContentType) -> str:
        last_error: Optional[Exception] = None
        for attempt in range(1, self.config.request_retries + 1):
            try:
                return self._render_page(url)
            except (PlaywrightError, PlaywrightTimeoutError) as exc:
                last_error = exc
                if attempt >= self.config.request_retries:
                    break
                print(
                    f"Browser fetch failed for IMDb {content_type.value} page "
                    f"(attempt {attempt}/{self.config.request_retries}): {exc}. Retrying..."
                )
                time.sleep(self.config.retry_delay)

        raise ScraperError(
            f"Failed to render IMDb {content_type.value} page after {self.config.request_retries} attempts: {url}"
        ) from last_error

    def _render_page(self, url: str) -> str:
        timeout_ms = self.config.request_timeout * 1000
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=self.config.browser_headless)
            context = None
            page = None
            try:
                context = browser.new_context(
                    user_agent=self.config.user_agent,
                    locale="en-US",
                    viewport={"width": 1365, "height": 900},
                )
                page = context.new_page()
                deadline = time.monotonic() + self.config.request_timeout
                response = page.goto(
                    str(url), wait_until="domcontentloaded", timeout=timeout_ms
                )
                if response is not None and response.status >= 400:
                    raise PlaywrightError(
                        f"IMDb returned HTTP {response.status} for {url}"
                    )

                ready_selector = ", ".join(
                    [
                        "#challenge-container",
                        "li.ipc-metadata-list-summary-item",
                        "li.titleColumn",
                        ".cli-title-link",
                        ".ipc-title-link-wrapper",
                    ]
                )
                try:
                    remaining_timeout_ms = max(
                        1, int((deadline - time.monotonic()) * 1000)
                    )
                    page.wait_for_selector(ready_selector, timeout=remaining_timeout_ms)
                except PlaywrightTimeoutError:
                    pass
                return page.content()
            finally:
                if page is not None:
                    page.close()
                if context is not None:
                    context.close()
                browser.close()

    @staticmethod
    def _is_bot_challenge(soup: BeautifulSoup) -> bool:
        page_text = soup.get_text(" ", strip=True).lower()
        return bool(
            soup.select_one("#challenge-container")
            or soup.find("script", src=re.compile(r"token\.awswaf\.com|challenge\.js"))
            or "verify that you're not a robot" in page_text
        )

    def fetch_popular_movies(self) -> List[ContentItem]:
        return self._scrape_imdb_list(
            self.config.imdb_movies_url, ContentType.MOVIE, self.config.max_movies
        )

    def fetch_popular_tv_shows(self) -> List[ContentItem]:
        return self._scrape_imdb_list(
            self.config.imdb_tv_url, ContentType.SERIES, self.config.max_tv_shows
        )
