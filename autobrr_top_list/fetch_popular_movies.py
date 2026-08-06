#!/usr/bin/env python3
"""Generate a popular, home-released movie list."""

import sys

from autobrr_top_list import (
    OutputManager,
    ScraperConfig,
    TMDbClient,
)


def main() -> None:
    config = ScraperConfig()

    print("Fetching popular home-released movies...")
    print(
        "Configuration: "
        f"max_movies={config.max_movies}, "
        f"min_year={config.min_year}, "
        f"min_rating={config.min_rating}, "
        "minimum_votes="
        f"{config.popular_min_vote_count}, "
        f"region={config.home_release_region}"
    )

    client = TMDbClient(config)
    movies = client.fetch_discover_popular_movies()

    if not movies:
        raise RuntimeError(
            "TMDb Discover returned zero matching movies"
        )

    OutputManager(config).save_outputs(movies)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            f"Fatal error: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
