# Will only work each 5 mins or so, gotta make a scheduler on cloud function later

from UTILS import init_db, get_most_recent_link, insert_rows, scrape_new_items, send_email
import undetected_chromedriver as uc
import json

with open("creds.json", "r") as f:
    credentials = json.load(f)

init_db()
driver = uc.Chrome(browser_executable_path=credentials["chrome_executable_path"], driver_executable_path=credentials["driver_executable_path"], headless=True)
try:
    last_link = get_most_recent_link()
    new_rows = scrape_new_items(driver, stop_link=last_link)
    inserted = insert_rows(new_rows)
    print(f"Inserted {inserted} new rows.")

except Exception as e:
    send_email(f"An error occurred during scraping: {e}")

finally:
    driver.quit()