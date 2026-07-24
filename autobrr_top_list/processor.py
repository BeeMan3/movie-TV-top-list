from .models import ContentItem, SimpleContentItem


class ContentProcessor:
    @staticmethod
    def combine_and_rank_lists(
        movies: list[ContentItem], tv_shows: list[ContentItem], max_items: int
    ) -> list[ContentItem]:
        combined: list[ContentItem] = []
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
    def create_simple_output(items: list[ContentItem]) -> list[SimpleContentItem]:
        return [SimpleContentItem(title=item.title) for item in items]
