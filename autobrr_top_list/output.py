import json
from typing import List

from .config import ScraperConfig
from .models import ContentItem, DetailedOutput
from .processor import ContentProcessor


class OutputManager:
    def __init__(self, config: ScraperConfig):
        self.config = config

    def save_outputs(self, items: List[ContentItem]) -> None:
        simple_items = ContentProcessor.create_simple_output(items)
        simple_data = [item.model_dump() for item in simple_items]

        with open(self.config.simple_output_file, "w", encoding="utf-8") as f:
            json.dump(simple_data, f, indent=2, ensure_ascii=False)

        detailed_output = DetailedOutput(total_items=len(items), items=items)

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
