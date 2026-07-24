# Autobrr Top List

A daily-updated list of recent trending movies and TV shows, built from the [TMDb API](https://developer.themoviedb.org/) and published to GitHub Pages.

It's designed as a data source for [autobrr](https://autobrr.com) filter automation: point a filter at the published JSON and it stays current with recently released, well-rated titles.

## How it works

A GitHub Actions workflow runs every day at 06:15 UTC and:

1. Fetches TMDb's trending movie and TV lists (weekly window by default).
2. Filters entries by release year and user rating.
3. Interleaves movies and shows into a single ranked list.
4. Writes both a simple and a detailed JSON file.
5. Deploys the files to GitHub Pages.

## Output Format

The main output file `top-list.json` contains a simple array of objects:

```json
[
    { "title": "Superman" },
    { "title": "Squid Game" },
    { "title": "Wicked" },
    { "title": "Wednesday" },
    { "title": "Moana 2" }
]
```

The detailed file `top-list-detailed.json` includes metadata and a timestamp:

```json
{
    "last_updated": "2025-01-08T15:30:00.000000",
    "total_items": 100,
    "items": [
        {
            "title": "Superman",
            "type": "movie",
            "average_rating": 7.8
        },
        {
            "title": "Squid Game",
            "type": "series",
            "average_rating": 7.9
        }
    ]
}
```

## Setup

You'll need a TMDb credential. Create a free non-commercial one at <https://www.themoviedb.org/settings/api> and copy the **API Read Access Token** (v4). A legacy v3 API key also works.

### Run it yourself on GitHub

1. **Fork this repository.**
2. **Add the TMDb token.** Settings → Secrets and variables → Actions → New repository secret, named `TMDB_READ_ACCESS_TOKEN`.
3. **Grant workflow permissions.** Settings → Actions → General → Workflow permissions → "Read and write permissions", then save.
4. **Enable GitHub Pages.** Settings → Pages → Source: "Deploy from a branch", branch `gh-pages`, folder `/ (root)`. The workflow creates the `gh-pages` branch on its first run.
5. **Trigger a run** (optional). Actions tab → "Update Top Movies and Series List" → "Run workflow".

Optionally override `SCRAPER_MAX_MOVIES`, `SCRAPER_MAX_TV_SHOWS`, and `SCRAPER_MAX_TOTAL_ITEMS` as Actions repository variables. See [Configuration](#configuration) for the full list.

### Run it locally

```bash
pip install -r requirements.txt
TMDB_READ_ACCESS_TOKEN=your-token python fetch_top_list.py
```

This writes `top-list.json` and `top-list-detailed.json` to the current directory.

## Accessing the Data

The JSON files are deployed to GitHub Pages and always reflect the latest run — no authentication or downloading required. After setup they're available at:

- Simple list: `https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/top-list.json`
- Detailed list: `https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/top-list-detailed.json`
- Web interface: `https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/`

Fetch them with any HTTP client:

```bash
curl https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/top-list.json
```

## Configuration

Everything is configured through environment variables, which can also be set in a `.env` file. Copy the example to get started:

```bash
cp .env.example .env
```

Provide exactly one TMDb credential. `TMDB_READ_ACCESS_TOKEN` (v4) is sent as an `Authorization: Bearer` header and is preferred; `TMDB_API_KEY` (legacy v3) is sent as an `api_key` query parameter.

| Variable                       | Default                | Description                                             |
| ------------------------------ | ---------------------- | ------------------------------------------------------- |
| `SCRAPER_MAX_MOVIES`           | 50                     | Maximum number of movies to fetch (1-100)               |
| `SCRAPER_MAX_TV_SHOWS`         | 50                     | Maximum number of TV shows to fetch (1-100)             |
| `SCRAPER_MAX_TOTAL_ITEMS`      | 100                    | Maximum total items in final list (1-200)               |
| `SCRAPER_MIN_YEAR`             | last 5 years           | Minimum release year filter (None to disable)           |
| `SCRAPER_MAX_YEAR`             | None                   | Maximum release year filter (None to disable)           |
| `SCRAPER_MIN_RATING`           | 6.0                    | Minimum user rating filter (None to disable)            |
| `SCRAPER_MAX_RATING`           | None                   | Maximum user rating filter (None to disable)            |
| `SCRAPER_REQUEST_TIMEOUT`      | 15                     | Request timeout in seconds (5-60)                       |
| `SCRAPER_REQUEST_DELAY`        | 2.0                    | Delay between TMDb pages (0.1-10.0)                     |
| `SCRAPER_REQUEST_RETRIES`      | 3                      | Number of API request attempts before failing (1-10)    |
| `SCRAPER_RETRY_DELAY`          | 2.0                    | Delay between failed API attempts in seconds (0.1-30.0) |
| `TMDB_READ_ACCESS_TOKEN`       | required               | TMDb API Read Access Token (v4), preferred credential   |
| `TMDB_API_KEY`                 | required               | Legacy TMDb v3 API key (alternative to the token)       |
| `SCRAPER_TMDB_TRENDING_WINDOW` | week                   | TMDb trending window: `day` or `week`                   |
| `SCRAPER_SIMPLE_OUTPUT_FILE`   | top-list.json          | Simple output filename                                  |
| `SCRAPER_DETAILED_OUTPUT_FILE` | top-list-detailed.json | Detailed output filename                                |

### Content filtering

Results are filtered by release year and user rating, so the list stays focused on recent, well-rated titles. Each filter can be disabled by setting it to `None`.

```env
# Only very recent content (last 2 years)
SCRAPER_MIN_YEAR=2023
SCRAPER_MAX_YEAR=None

# High-quality content only
SCRAPER_MIN_RATING=7.5
SCRAPER_MAX_RATING=None

# Specific year range
SCRAPER_MIN_YEAR=2022
SCRAPER_MAX_YEAR=2024

# Rating range
SCRAPER_MIN_RATING=6.5
SCRAPER_MAX_RATING=8.0

# Disable all filters (all trending content)
SCRAPER_MIN_YEAR=None
SCRAPER_MAX_YEAR=None
SCRAPER_MIN_RATING=None
SCRAPER_MAX_RATING=None
```

### Example configuration

```env
# Fetch more content
SCRAPER_MAX_MOVIES=40
SCRAPER_MAX_TV_SHOWS=40
SCRAPER_MAX_TOTAL_ITEMS=75

# TMDb trending window; weekly is the default for sustained release interest
SCRAPER_TMDB_TRENDING_WINDOW=week

# Slower API pagination
SCRAPER_REQUEST_TIMEOUT=20
SCRAPER_REQUEST_DELAY=3.0

# Custom output files
SCRAPER_SIMPLE_OUTPUT_FILE=my-top-list.json
SCRAPER_DETAILED_OUTPUT_FILE=my-detailed-list.json
```

## Data source

The list is built from two TMDb endpoints:

- [Trending Movies](https://developer.themoviedb.org/reference/trending-movies)
- [Trending TV](https://developer.themoviedb.org/reference/trending-tv)

This product uses the TMDb API but is not endorsed or certified by TMDb. The free credential is for non-commercial use; review TMDb's terms, attribution requirements, and licensing at <https://developer.themoviedb.org/docs/faq>.

## Troubleshooting

### No data fetched

If a fetch fails, the updater exits non-zero and leaves the existing output files untouched rather than overwriting them with empty arrays. Check the Actions logs for the error — usually a missing or invalid credential, an HTTP error, or a temporary TMDb outage (see the [status page](https://status.themoviedb.org/)). Transient failures are retried per `SCRAPER_REQUEST_RETRIES` and `SCRAPER_RETRY_DELAY`.

### Workflow not running

1. Ensure GitHub Actions are enabled in your repository.
2. Check that workflow permissions are set to "Read and write".
3. Verify the repository is public (or you have GitHub Pro for private Pages).

### Permission denied (403)

If the workflow can't push to `gh-pages`:

1. Confirm workflow permissions are set to "Read and write" (Settings → Actions → General).
2. Confirm Pages is set to "Deploy from a branch" with the `gh-pages` branch (Settings → Pages). The workflow creates the branch on its first run.
3. Confirm you have write access to the repository, and that Actions are enabled if you forked it.

## Contributing

Issues and pull requests are welcome. Licensed under the MIT License.
