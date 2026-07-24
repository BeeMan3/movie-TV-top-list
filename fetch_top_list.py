#!/usr/bin/env python3
"""CLI entrypoint for Autobrr Top List updater."""

import sys
import time

from autobrr_top_list import (
    ContentProcessor,
    OutputManager,
    ScraperConfig,
    TMDbClient,
)


def main() -> None:
    config = ScraperConfig()

    print("Starting content fetching process...")
    print(
        f"Configuration: max_movies={config.max_movies}, max_tv_shows={config.max_tv_shows}, max_total={config.max_total_items}"
    )

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
        print(f"Source: TMDb {config.tmdb_trending_window} trending lists")
    else:
        print("No filters applied - fetching all popular content")

    client = TMDbClient(config)
    processor = ContentProcessor()
    output_manager = OutputManager(config)

    movies = client.fetch_popular_movies()
    time.sleep(config.request_delay)
    tv_shows = client.fetch_popular_tv_shows()
    print(f"Found {len(movies)} movies and {len(tv_shows)} TV shows")

    if not movies:
        raise RuntimeError("TMDb movie trending list returned zero matching items")
    if not tv_shows:
        raise RuntimeError("TMDb TV trending list returned zero matching items")

    combined_list = processor.combine_and_rank_lists(
        movies, tv_shows, config.max_total_items
    )
    if not combined_list:
        raise RuntimeError("Combined output is empty; refusing to overwrite outputs")

    output_manager.save_outputs(combined_list)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        raise SystemExit(1) from e
