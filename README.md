# Autobrr Top List

An automated system that fetches and maintains a list of the top 50 recent movies and series, updated daily via GitHub Actions.

## Overview

This project automatically scrapes IMDB's "Most Popular Movies" and "Most Popular TV Shows" lists to create a combined ranking of the top 50 entertainment titles.
The list's primary purpose is to be used for autobrr filter automation.
The list updates daily at 6:15 AM UTC using GitHub Actions.

## Features

-   **Daily Updates**: Automatically runs every day at 6:15 AM UTC
-   **No API Keys Required**: Uses web scraping from public IMDB pages
-   **Combined List**: Merges movies and TV shows into a single ranked list
-   **Content Filtering**: Filter by release year and user rating for fresh, high-quality content
-   **Private Tracker Optimized**: Default filters target recent, well-rated content ideal for autobrr
-   **Simple Output Format**: Clean JSON format with just titles
-   **Configurable**: Fully configurable via environment variables or .env file
-   **Type Safe**: Built with Pydantic models and full type annotations
-   **Modular Architecture**: Clean separation of concerns with dedicated classes
-   **GitHub Pages Deployment**: Public URLs accessible via simple HTTP GET requests
-   **Robust Error Handling**: Graceful failure with empty output on scraping errors

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

A detailed version `top-list-detailed.json` includes additional metadata:

```json
{
    "last_updated": "2025-01-08T15:30:00.000Z",
    "total_items": 50,
    "items": [
        {
            "title": "Superman",
            "type": "movie",
            "average_rating": 7.8
        }
    ]
}
```

## Setup Instructions

1. **Fork this repository** to your GitHub account

2. **Enable GitHub Actions** in your repository:

    - Go to the "Actions" tab in your repository
    - If prompted, click "I understand my workflows, go ahead and enable them"

3. **Configure repository permissions**:

    - Go to Settings → Actions → General
    - Under "Workflow permissions", select "Read and write permissions"
    - Check "Allow GitHub Actions to create and approve pull requests"
    - Click "Save"

4. **Enable GitHub Pages**:

    - Go to Settings → Pages
    - Under "Source", select "Deploy from a branch"
    - Choose "gh-pages" branch and "/ (root)" folder
    - Click "Save"

5. **Manual trigger** (optional):
    - Go to the "Actions" tab
    - Click on "Update Top Movies and Series List"
    - Click "Run workflow" to test the setup

## Accessing the Data

The generated JSON files are automatically deployed to **GitHub Pages** and accessible via direct URLs:

### Public URLs

Once you've set up the repository, the data will be available at:

-   **Simple List**: `https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/top-list.json`
-   **Detailed List**: `https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/top-list-detailed.json`
-   **Web Interface**: `https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/`

### Direct API Access

You can fetch the data directly with any HTTP client:

```bash
# Get the simple list
curl https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/top-list.json

# Get the detailed list
curl https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/top-list-detailed.json
```

### Example Usage

```javascript
// Fetch in JavaScript
fetch("https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/top-list.json")
    .then((response) => response.json())
    .then((data) => console.log(data));
```

```python
# Fetch in Python
import requests
response = requests.get('https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/top-list.json')
data = response.json()
```

**The URLs always point to the latest data** - no authentication, downloading, or unpacking required!

## Configuration

The scraper is fully configurable via environment variables. Create a `.env` file in the root directory to customize settings:

```bash
# Copy the example configuration
cp .env.example .env
```

### Available Configuration Options

| Variable                       | Default                | Description                                   |
| ------------------------------ | ---------------------- | --------------------------------------------- |
| `SCRAPER_MAX_MOVIES`           | 50                     | Maximum number of movies to fetch (1-100)     |
| `SCRAPER_MAX_TV_SHOWS`         | 50                     | Maximum number of TV shows to fetch (1-100)   |
| `SCRAPER_MAX_TOTAL_ITEMS`      | 100                    | Maximum total items in final list (1-200)     |
| `SCRAPER_MIN_YEAR`             | last 5 years           | Minimum release year filter (None to disable) |
| `SCRAPER_MAX_YEAR`             | None                   | Maximum release year filter (None to disable) |
| `SCRAPER_MIN_RATING`           | 6.0                    | Minimum user rating filter (None to disable)  |
| `SCRAPER_MAX_RATING`           | None                   | Maximum user rating filter (None to disable)  |
| `SCRAPER_REQUEST_TIMEOUT`      | 15                     | Request timeout in seconds (5-60)             |
| `SCRAPER_REQUEST_DELAY`        | 2.0                    | Delay between requests in seconds (0.1-10.0)  |
| `SCRAPER_SIMPLE_OUTPUT_FILE`   | top-list.json          | Simple output filename                        |
| `SCRAPER_DETAILED_OUTPUT_FILE` | top-list-detailed.json | Detailed output filename                      |

### Content Filtering

The scraper supports filtering content by release year and user rating to ensure only fresh, high-quality content is included - perfect for private tracker optimization:

**Filter Examples:**

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

# Disable all filters (get all popular content)
SCRAPER_MIN_YEAR=None
SCRAPER_MAX_YEAR=None
SCRAPER_MIN_RATING=None
SCRAPER_MAX_RATING=None
```

### Example Configuration

```env
# Fetch more content
SCRAPER_MAX_MOVIES=40
SCRAPER_MAX_TV_SHOWS=40
SCRAPER_MAX_TOTAL_ITEMS=75

# Slower, more respectful scraping
SCRAPER_REQUEST_TIMEOUT=20
SCRAPER_REQUEST_DELAY=3.0

# Custom output files
SCRAPER_SIMPLE_OUTPUT_FILE=my-top-list.json
SCRAPER_DETAILED_OUTPUT_FILE=my-detailed-list.json
```

## How It Works

1. **Scraping**: The script fetches data from IMDB's popular movies and TV shows charts
2. **Processing**: Removes ranking numbers, extracts clean titles
3. **Combining**: Interleaves movies and TV shows for variety
4. **Output**: Generates both simple and detailed JSON files
5. **Automation**: GitHub Actions deploys the files to GitHub Pages daily

## Data Sources

-   **IMDB Most Popular Movies**: https://www.imdb.com/chart/moviemeter/
-   **IMDB Most Popular TV Shows**: https://www.imdb.com/chart/tvmeter/

These lists are updated by IMDB based on user activity and page views, providing a good indicator of current popularity.

## Troubleshooting

### No Data Fetched

If scraping fails, the script will output empty arrays to ensure the files are always valid JSON. Check the GitHub Actions logs for error details.

### Workflow Not Running

1. Ensure GitHub Actions are enabled in your repository
2. Check that workflow permissions are set to "Read and write"
3. Verify the repository is not private (or you have GitHub Pro for private repos)

### Permission Denied Error (403)

If you get a "Permission denied" error when the workflow tries to push to gh-pages:

1. **Check Repository Settings**:

    - Go to Settings → Actions → General
    - Under "Workflow permissions", select "Read and write permissions"
    - Save the settings

2. **Verify GitHub Pages Configuration**:

    - Go to Settings → Pages
    - Ensure "Deploy from a branch" is selected
    - Choose "gh-pages" as the source branch
    - The workflow will create this branch automatically on first run

3. **Repository Ownership**:
    - Make sure you have admin/write access to the repository
    - If it's a forked repository, you may need to enable Actions in your fork

### Rate Limiting

The script includes delays between requests to be respectful to IMDB's servers. If you encounter rate limiting, you can increase the `SCRAPER_REQUEST_DELAY` setting.

## Legal Considerations

This project scrapes publicly available data from IMDB for personal/educational use. Please ensure compliance with:

-   IMDB's terms of service
-   Rate limiting (built into the script)
-   Fair use principles

## Contributing

Feel free to submit issues or pull requests to improve the project. Some ideas:

-   Add more data sources
-   Improve error handling
-   Add filtering options
-   Include additional metadata

## License

This project is open source and available under the MIT License.
