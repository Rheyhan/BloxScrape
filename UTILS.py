# Scrapping and crawling modules
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
import datetime
import os
from typing import *
import sqlite3

DB_PATH = "robloxaccessory.db"
TABLE_NAME = "roblox_accessories"
CATALOG_URL = "https://www.roblox.com/catalog?taxonomy=wNYJso48d1XnhMyFWT3oX3&salesTypeFilter=1&SortType=3&IncludeNotForSale="

def init_db() -> None:
    '''
    Initialize the sqlite database and create table if it doesn't exist
    '''
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,       # Unique ID for each entry
                Name TEXT,
                category TEXT,
                price TEXT,
                Creator TEXT,
                IsVerified INTEGER,
                IsLimited INTEGER,
                Link TEXT,
                ImageURL TEXT,
                timeCollected TEXT
            )
            """
        )

        # Links are unique and it should be unique, if not i'm retarded
        conn.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{TABLE_NAME}_link ON {TABLE_NAME}(Link)"
        )

        conn.commit()

def get_most_recent_link() -> Optional[str]:
    '''
    Get the most recent post link from the database

    Returns
    -------
    - Optional[str]
        The most recent post link or None if the database is empty
    '''

    if not os.path.exists(DB_PATH):
        return None
    
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            f"SELECT Link FROM {TABLE_NAME} ORDER BY id ASC LIMIT 1"
        ).fetchone()

    return row[0] if row else None  # Needs to be indexxed so will return as str

def insert_rows(rows: List[Tuple]) -> int:
    '''
    Insert multiple rows into the database by appending them from the bottom
    
    Parameters
    ----------
    - rows : List[Tuple]
        A list of tuples representing the rows to be inserted
    
    Returns
    -------
    - int
        The number of rows inserted
    '''
    if not rows:
        return 0
    
    # Insert rows into the database
    with sqlite3.connect(DB_PATH) as conn:
        conn.executemany(
            f"""
            INSERT OR IGNORE INTO {TABLE_NAME}
            (Name, category, price, Creator, IsVerified, IsLimited, Link, ImageURL, timeCollected)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            ,
            rows,
        )

        conn.commit()

        return conn.total_changes

def scrape_new_items(driver, stop_link: Optional[str] = None) -> List[Tuple]:
    '''
    Scrape new items from the roblox catalog page

    Parameters
    ----------
    - driver : undetected_chromedriver.Chrome
        The undetected chromedriver instance to use for scraping
    - stop_link : Optional[str]
        The link to stop scraping at (exclusive). If None, scrape all items.

    Returns
    -------
    - List[Tuple]
        A list of tuples representing the scraped items
    '''
    # Variables
    theDict = { "Name": [], "category": [], "price": [], "Creator": [], "IsVerified": [], "IsLimited": [],
                "Link": [], "ImageURL": [], "timeCollected": []}
    count = 0
    reached_all_posts = False
    seen = set()  # Uniqueness to prevent duplicates
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Get to Roblox Catalog Page
    driver.get(CATALOG_URL)
    driver.execute_script("document.body.style.zoom = '25%';")      # Zoom out to load more items
    time.sleep(7)

    # Check page loaded
    _page_loaded = WebDriverWait(driver, 10).until(EC.presence_of_element_located(
        (By.XPATH, "//ul[@class='hlist item-cards-stackable organic-items-wrapper']")))
    if not _page_loaded:
        print("Page did not load properly.")
        return []
    
    # For scrollinng
    while True:
        if reached_all_posts:
            break
        last_height = driver.execute_script("return document.body.scrollHeight")
        # Collect items
        while True:
            items = driver.find_elements(By.XPATH, "//div[@class='catalog-item-container']")
            for item in items[count:]:

                # If the post has no caption, js skip gng
                try:
                    caption_element = item.find_element(By.XPATH, ".//div[@class='item-card-caption']")
                except Exception:
                    count += 1
                    continue

                # If stop link (aka the earliest link from the sql database) has been reached, stop scraping
                link = item.find_element(By.XPATH, ".//a[@class='item-card-link']").get_attribute("href")
                if stop_link and link == stop_link:
                    reached_all_posts = True
                    break

                # Extract details
                name = caption_element.find_element(By.XPATH, ".//div[@class='item-card-name-link']/div").text
                creator = caption_element.find_element(By.XPATH, ".//div[@class='text-overflow item-card-creator']/span/a[@class='creator-name text-link']").text
                ## Is creator verified
                try:
                    item.find_element(By.XPATH, ".//div[@class='text-overflow item-card-creator']/span/img")
                    is_verified = True
                except Exception:
                    is_verified = False
                ## Price
                try:
                    price_text = item.find_element(By.XPATH, ".//div/span[@class='text-robux-tile' or @class='text text-label text-robux-tile']").text
                    if not price_text:
                        price_text = "unavailable"
                    price_value = price_text.strip()
                except Exception:
                    price_value = "unavailable"
                thumbnail_element = item.find_element(By.XPATH, ".//div[@class='item-card-link']")
                img_url = thumbnail_element.find_element(By.TAG_NAME, "img").get_attribute("src")
                ## Is the item limited
                try:
                    thumbnail_element.find_element(
                        By.XPATH, ".//div[@class='restriction-icon icon-limited-unique-label']"
                    )
                    is_limited = True
                except Exception:
                    is_limited = False
                ## Item category
                match = re.search(r"/([^/]+)/Webp", img_url)
                category = match.group(1) if match else None

                # Just in case of duplicates
                row_key = (name, category, price_value, creator, is_verified, is_limited, link, img_url)
                if row_key not in seen:
                    theDict["Name"].append(name)
                    theDict["category"].append(category)
                    theDict["price"].append(price_value)
                    theDict["Creator"].append(creator)
                    theDict["IsVerified"].append(int(is_verified))
                    theDict["IsLimited"].append(int(is_limited))
                    theDict["Link"].append(link)
                    theDict["ImageURL"].append(img_url)
                    theDict["timeCollected"].append(now_str)
                    seen.add(row_key)

            if reached_all_posts:
                break

            # Scroll down to load more items
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(10)
            count = len(items)
            new_height = driver.execute_script("return document.body.scrollHeight")
            items = driver.find_elements(By.XPATH, "//div[@class='catalog-item-container']")

            # If no new items loaded or still the same height, this mfer
            if count == len(items) or new_height == last_height:
                reached_all_posts = True
                break

    # Prepare rows to return
    rows = []
    for i in range(len(theDict["Name"])):
        rows.append(
            (
                theDict["Name"][i],
                theDict["category"][i],
                theDict["price"][i],
                theDict["Creator"][i],
                theDict["IsVerified"][i],
                theDict["IsLimited"][i],
                theDict["Link"][i],
                theDict["ImageURL"][i],
                theDict["timeCollected"][i],
            )
        )
    return rows[::-1]   # Return in chronological order, so earliest will be on the last