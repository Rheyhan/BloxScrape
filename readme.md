
# BloxScrape

Lightweight scraper + ETL for Roblox accessories, storing results in SQLite and exposing a small FastAPI read-only API.

**Contents**
- `UTILS.py` - core scraping and DB helpers (init, scrape_new_items, insert_rows, get_most_recent_link, send_email)
- `ETL.py` - one-shot ETL runner that scrapes new items and inserts into the DB
- `fastAPI.py` - small read-only API to query the scraped data
- `creds.json` - (not checked in) credentials and local chrome/driver paths
- `example.db` - SQLite databases example (created at runtime)

**Overview**

This repo scrapes the Roblox accessories catalog periodically (ETL job) and persists each item to a local SQLite database. The API serves the stored rows for simple queries, pagination and basic stats.

Database schema (sqlite):

- Table: `roblox_accessories`
	- `id` INTEGER PRIMARY KEY AUTOINCREMENT
	- `Name` TEXT
	- `category` TEXT
	- `price` TEXT  -- kept as TEXT to support values like `Free` / `unavailable`
	- `Creator` TEXT
	- `IsVerified` INTEGER (0/1)
	- `IsLimited` INTEGER (0/1)
	- `Link` TEXT (unique index)
	- `ImageURL` TEXT
	- `timeCollected` TEXT (ISO datetime string)

Prerequisites
- Python 3.10+ (project tested on CPython 3.10+)
- Chrome and compatible chromedriver installed locally
- `creds.json` with at least the following keys (example):

```json
{
	"chrome_executable_path": "Path to your chrome.exe",
	"driver_executable_path": "Path to your chromedriver.exe",
	"email": "you@example.com",
	"password": "app-password-or-smtp-pass",
	"send_to_email": "notify@example.com"
}
```

Install dependencies

```bash
python -m pip install -r requirements.txt
```

Run the ETL (one-shot)

```bash
python ETL.py
```

ETL behavior
- `ETL.py` calls `get_most_recent_link()` to find the last stored `Link` and scrapes newer items until it reaches that link (stop is exclusive). New rows are then inserted with `INSERT OR IGNORE` to avoid duplicates.
- The scraper stores `price` as TEXT so it supports `Free`, `unavailable`, or numeric strings.

Run the API (development)

```bash
uvicorn fastAPI:app --reload --port 8000
```

API highlights
- `GET /items` — list items with `limit`, `offset`, and filters: `creator`, `category`, `verified`, `limited`
- `GET /items/{item_id}` — retrieve single item by `id`
- `GET /stats` — database statistics
- `GET /recent` — most recent items by `timeCollected`

Notes and troubleshooting
- Make sure the paths in `creds.json` are correct and Chrome/Chromedriver versions are compatible.
- If scraping fails frequently, enable a visible browser (set `headless=False`) to debug page loads and XPaths.
- The repository uses `undetected_chromedriver` to reduce bot detection, but behavior may still change if Roblox updates their markup.

Security
- Do not commit `creds.json` or any secrets to source control.