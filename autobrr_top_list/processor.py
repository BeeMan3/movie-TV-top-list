from typing import List

from .models import ContentItem, SimpleContentItem


class ContentProcessor:
    @staticmethod
    def combine_and_rank_lists(
        movies: List[ContentItem], tv_shows: List[ContentItem], max_items: int
    ) -> List[ContentItem]:
        combined: List[ContentItem] = []
        max_length = max(len(movies), len(tv_shows))

        for i in range(max_length):
            if i < len(movies):
                combined.append(movies[i])
            if i < len(tv_shows):
                combined.append(tv_shows[i])
            if len(combined) >= max_items:
                break

        return combined[:max_items]

    @staticmethod
    def create_simple_output(items: List[ContentItem]) -> List[SimpleContentItem]:
        return [SimpleContentItem(title=item.title) for item in items]
