# Will only work each 5 mins or so, gotta make scheduler work for that.

from UTILS import *


init_db()
driver = uc.Chrome(headless=True)

try:
    last_link = get_most_recent_link()
    new_rows = scrape_new_items(driver, stop_link=last_link)
    inserted = insert_rows(new_rows)
    print(f"Inserted {inserted} new rows.")
finally:
    driver.quit()