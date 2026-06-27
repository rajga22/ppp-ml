# imports
import requests
from bs4 import BeautifulSoup
import pandas as pd
from selenium import webdriver
from selenium.webdriver import Keys, ActionChains
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.mouse_button import MouseButton
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoAlertPresentException
import time
from datetime import datetime
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin



# 12/18/2025
import tls_client
from rich import print
import os

# Gap
url = "https://www.gap.com"

# Get the current date and time
current_datetime = datetime.now()

print(f"\n--- Current time: {current_datetime} ---")


# 12/18/2025
# Use a set to store visited URLs to avoid infinite loops and duplicate scraping
visited_urls = set()
# Set to store all extracted data (e.g., titles for this example)
scraped_data = set()
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1"
}

session = tls_client.Session(client_identifier="chrome_128", random_tls_extension_order = True)
resp = session.get(url, headers=headers, proxy = os.getenv("proxy"),)
print(resp)
if resp.status_code == 403:
    print(f"Error: Received 403 Forbidden. Response content: {resp.text}")
else:
    print(f"Success: Status code {resp.status_code} {resp.text}")
    print(resp.content)


    soup = BeautifulSoup(resp.content, 'lxml')
    
    # Extract data (example: page title and all headings)
    title = soup.title.string if soup.title else 'No title'
    headings = [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3'])]
    scraped_data.add(f"URL: {url} | Title: {title} | Headings count: {len(headings)}")

    # Find all links on the page and recursively scrape them
    for link in soup.find_all('a', href=True):
        absolute_url = urljoin(url, link['href'])
        # Only follow links that are part of the target domain
        if urlparse(absolute_url).netloc == url:
            scrape_website(absolute_url, session)





# Create a Firefox profile and disable geolocation
firefox_profile = webdriver.chrome.options.Options() #ChromeProfile()
#firefox_profile.set_preference("geo.enabled", False)  # Disable geolocation
#firefox_profile.set_preference("geo.provider.use_corelocation", False)  # Also disable core location provider
##firefox_profile.set_preference("geo.prompt.testing", False)  # Disable prompt testing
##firefox_profile.set_preference("geo.prompt.testing.allow", False) # Ensure testing allows isn't enabled
prefs = {"profile.default_content_settings.geolocation": 2}
firefox_profile.add_experimental_option("prefs", prefs)


options = webdriver.ChromeOptions()
#options.add_argument("-headless") 
options.profile = firefox_profile

browser = webdriver.Chrome(options=options)  
browser.get(url) 
time.sleep(5)
print(browser)

# Find search bar
#clickable = browser.find_element(By.XPATH, "//form[@id='gnav-search']") # Etsy
clickable = browser.find_element(By.XPATH, "//form[@data-testid='search-form']") # Gap

print(clickable)
time.sleep(5)

ActionChains(browser).click_and_hold(clickable).perform()

print("Clicked into 'Search bar'")
time.sleep(5)

# Search for item
search_term = "dresses" #"women's jeans" # Etsy: silver rings

ActionChains(browser)\
        .send_keys(search_term)\
        .perform()
time.sleep(5)

ActionChains(browser).key_down(Keys.ENTER).key_up(Keys.ENTER).perform()
print(f"Clicked 'Enter' to search for {search_term}...")

time.sleep(5)

# Escape pop-up
ActionChains(browser).key_down(Keys.ESCAPE).key_up(Keys.ESCAPE).perform()
print("Clicked 'Escape'")

time.sleep(5)



# Find product cards for each item
products = browser.find_elements(By.CLASS_NAME, "plp_product-card")
print("number of products:", len(products))

clickable2 = browser.find_element(By.ID, "sitewide-app")

time.sleep(5)

for idx, u in enumerate(products):
    print("-" * 5 + str(idx) + "-" * 5)
    try:
        # Find item information (item name, price, sale)
        elements2 = u.find_elements(By.TAG_NAME, "a")
        if elements2 != []:
            for e in elements2:
                print(e.text)

        # Scroll to next items
        scroll_origin = ScrollOrigin.from_element(e)
        ActionChains(browser)\
            .scroll_from_origin(scroll_origin, 0, 3)\
            .perform()


        time.sleep(1)

        # Escape pop-up
        ActionChains(browser).key_down(Keys.ESCAPE).key_up(Keys.ESCAPE).perform()
        print("Clicked 'Escape'")

    except (RuntimeError, ValueError, ZeroDivisionError) as error:
        print("Error:", error)

print("-"*20 + "\n\n\n")




# Etsy
'''
# Find items and print out all attributes of items
time.sleep(5)


ul = browser.find_elements(By.TAG_NAME, "ul")
print(ul)
for u in ul:
    try:
        print("u text:",u.text)
        l = u.find_elements(By.TAG_NAME, "li")
        print("li text:", l.text)
    except:
        print("Could not find li for", u)

print("-"*20 + "\n\n\n")

li = browser.find_elements(By.TAG_NAME, "li")
print(len(li))

for i in li:
    if i.text != "":
        print(i)
        print(i.text)
        CLASS = i.get_attribute("class")
        print(CLASS)
        

        print("-"*10)

'''
