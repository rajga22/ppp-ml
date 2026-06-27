import csv
import re
import time
import random
from pathlib import Path
from playwright.sync_api import sync_playwright
import playwright_stealth
import requests
from datetime import datetime
#from playwright_stealth import stealth_sync

# --- REGEX & CONFIG ---
USD_RE = re.compile(r"\$\s*([0-9]+(?:\.[0-9]{2})?)")
INR_RE = re.compile(r"₹\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)")
PCT_RE = re.compile(r"(-?\s*\d{1,3})\s*%")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"


def get_live_fx_rate(base="USD", target="INR"):
    """Fetches the latest real-time exchange rate."""
    try:
        # Using Frankfurter (Free, No API Key needed)
        url = f"https://api.frankfurter.app/latest?from={base}&to={target}"
        response = requests.get(url, timeout=10)
        data = response.json()
        rate = data['rates'][target]
        print(f"🌍 Live FX Rate Loaded: 1 {base} = {rate} {target}")
        return rate
    except Exception as e:
        # Fallback rate if the internet/API is down
        fallback = 94.01 
        print(f"⚠️ Could not fetch live rate ({e}). Using fallback: {fallback}")
        return fallback

def safe_float(x):
    try:
        return float(str(x).replace(",", ""))
    except:
        return None

def get_product_category(page):
    """Refined for 2026 layout: Extracts Department (WOMAN/MAN/KIDS)."""
    try:
        # Targets the active header or primary breadcrumb
        selectors = [
            ".layout-header__main-menu-item--active", 
            ".breadcrumb-list__item", 
            "h1.product-detail-info__header-name"
        ]
        for sel in selectors:
            element = page.query_selector(sel)
            if element:
                text = element.inner_text().upper()
                if "WOMAN" in text: return "WOMAN"
                if "MAN" in text: return "MAN"
                if "KID" in text: return "KIDS"
        return "GENERAL"
    except:
        return "N/A"

def get_product_id(url):
    match = re.search(r"-p([0-9]+)\.html", url)
    return match.group(1) if match else url

def parse_colour_from_title(title):
    if not title: return None
    left = title.split("|")[0]
    return left.rsplit(" - ", 1)[-1].strip() if " - " in left else None

def extract_materials_and_origin(page):
    for sel in ["text=COMPOSITION", "button:has-text('Composition')"]:
        try:
            el = page.query_selector(sel)
            if el:
                el.click()
                page.wait_for_timeout(100)
                break
        except: pass
    body = page.inner_text("body")
    made_in = re.search(r"Made in\s+([A-Za-z ]+)", body)
    materials = []
    for line in body.splitlines():
        if "%" in line and any(m in line.lower() for m in ["cotton", "wool", "silk", "linen", "polyester"]):
            materials.append(line.strip())
    return " | ".join(dict.fromkeys(materials)), (made_in.group(1).strip() if made_in else None)

def main():
    now = datetime.now()
    CURRENT_DATE = now.strftime("%Y-%m-%d")
    CURRENT_TIME = now.strftime("%H:%M:%S")
    FX_INR_PER_USD = get_live_fx_rate() #94.01 #83.0
    

    zara_categories = [
    #"https://www.zara.com/us/en/woman-dresses-l1066.html",
    "https://www.zara.com/us/en/woman-tops-l1322.html",
    #"https://www.zara.com/us/en/woman-blazers-l758.html",
    "https://www.zara.com/us/en/woman-skirts-l1299.html",
    "https://www.zara.com/us/en/woman-trousers-l1335.html",
    "https://www.zara.com/us/en/woman-jeans-l1055.html",
    "https://www.zara.com/us/en/woman-knitwear-l1152.html",
    "https://www.zara.com/us/en/woman-outerwear-l1184.html",
    "https://www.zara.com/us/en/woman-shoes-l1251.html",
    "https://www.zara.com/us/en/woman-bags-l1024.html"
    ]

    paths_list = ['./urls/men2/', './urls/kids2/', './urls/women/'] 

    for p in paths_list:
        folder_path = Path(p) #'./urls/kids2/')
        CATEGORY = p.strip("/").split("/")[-1]
        print(CATEGORY)
        us_files_list = sorted([
                file.name for file in folder_path.glob("*.txt") 
                if "urls_us_gemini" in file.name.lower()
            ])
        in_files_list = sorted([
                file.name for file in folder_path.glob("*.txt") 
                if "urls_in_gemini" in file.name.lower()
            ])

        print("US files:", us_files_list)
        
        for i in range(len(us_files_list)): #zara_categories: 
            us_url = us_files_list[i]
            in_url = in_files_list[i]

            print(us_url, in_url)
            
            c = us_url.split("-")[-1].strip(".txt")

            #c = i.split('/')[-1].split('-')[1]
            #us_urls = Path(f"urls_us_gemini_{c}.txt").read_text().splitlines() if Path(f"urls_us_gemini_{c}.txt").exists() else []
            #in_urls = Path(f"urls_in_gemini_{c}.txt").read_text().splitlines() if Path(f"urls_in_gemini_{c}.txt").exists() else []

            us_urls = (folder_path / us_url).read_text().splitlines() if (folder_path / us_url).exists() else []
            in_urls = (folder_path / in_url).read_text().splitlines() if (folder_path / in_url).exists() else []

            #print("US urls:", us_urls)


            OUTPUT_FILE = f"{i}_zara_full_{CURRENT_DATE}_comparison_{CATEGORY}_{c}.csv"
            
            us_data = {}
            in_data = {}

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)

                # --- SCRAPE US DATA ---
                context = browser.new_page(locale="en-US", user_agent=UA)
                # Apply stealth to the page
                #stealth_sync(context)
            
                for url in [u.strip() for u in us_urls if u.strip()]:
                    
                    FX_INR_PER_USD = get_live_fx_rate()
                    print(url, FX_INR_PER_USD)

                    time.sleep(random.uniform(2, 5))
                    
                    pid = get_product_id(url)
                    context.goto(url, timeout=60000) #wait_until="networkidle", 
                    title = context.title()

                    # Verify we aren't on a 'Access Denied' page
                    if "Search engine" in title or "Access Denied" in title:
                        print(f"⚠️ Blocked by Zara on {url}. Skipping...")
                        continue
                    
                    prices = [p.replace(",", "") for p in USD_RE.findall(context.inner_text("body"))]
                    # Use breadcrumbs to find the category
                    category = get_product_category(context)
                    cur_f = safe_float(min(prices)) if prices else None
                    orig_f = safe_float(max(prices)) if (prices and len(prices) > 1) else None
                    disc = (PCT_RE.search(context.inner_text("body")).group(1)) if PCT_RE.search(context.inner_text("body")) else None
                    mats, origin = extract_materials_and_origin(context)
                    
                    us_data[pid] = {
                        "name": title,
                        "category": category,
                        "colour": parse_colour_from_title(title),
                        "cur": cur_f,
                        "orig": orig_f,
                        "disc": disc,
                        "disc_calc": f"{(1 - cur_f / orig_f) * 100:.2f}" if (cur_f and orig_f and orig_f > cur_f) else None,
                        "on_sale": disc is not None or (cur_f and orig_f and orig_f > cur_f),
                        "materials": mats,
                        "origin": origin,
                        "exchange_rate": FX_INR_PER_USD
                    }
                context.close()

                # --- SCRAPE INDIA DATA ---
                context = browser.new_page(locale="en-IN", user_agent=UA)
                for url in [u.strip() for u in in_urls if u.strip()]:
                    pid = get_product_id(url)
                    try:
                        context.goto(url)
                        prices = [p.replace(",", "") for p in INR_RE.findall(context.inner_text("body"))]
                        cur_f = safe_float(min(prices)) if prices else None
                        orig_f = safe_float(max(prices)) if (prices and len(prices) > 1) else None
                        disc = (PCT_RE.search(context.inner_text("body")).group(1)) if PCT_RE.search(context.inner_text("body")) else None
                        
                        in_data[pid] = {
                            "cur": cur_f,
                            "orig": orig_f,
                            "disc": disc,
                            "disc_calc": f"{(1 - cur_f / orig_f) * 100:.2f}" if (cur_f and orig_f and orig_f > cur_f) else None,
                            "on_sale": disc is not None or (cur_f and orig_f and orig_f > cur_f)
                        }
                    except:
                        print(f"Timed out...skipping {url} and deleting from US data")
                        del us_data[pid]
                        print(us_data)
                        continue

                context.close()
                browser.close()

            # --- MERGE INTO ORIGINAL FIELD NAMES ---
            final_rows = []
            for pid in us_data:
                if pid in in_data:
                    us = us_data[pid]
                    ind = in_data[pid]
                    in_cur_usd = round(ind["cur"] / FX_INR_PER_USD, 2) if ind["cur"] else None
                    
                    final_rows.append({
                        "Product_ID": pid,
                        "name": us["name"],
                        "Category": us["category"], # Added Category!
                        "colour_from_title": us["colour"],
                        "US_price_current_usd": us["cur"],
                        "US_price_original_usd": us["orig"],
                        "US_discount_pct_display": us["disc"],
                        "US_on_sale": us["on_sale"],
                        "IN_price_current_inr": ind["cur"],
                        "IN_price_current_usd": in_cur_usd,
                        "IN_price_original_inr": ind["orig"],
                        "IN_discount_pct_display": ind["disc"],
                        "IN_discount_pct_calc": ind["disc_calc"],
                        "IN_on_sale": ind["on_sale"],
                        "Savings_USD": round(us["cur"] - in_cur_usd, 2) if (us["cur"] and in_cur_usd) else None,
                        "materials_text": us["materials"],
                        "made_in": us["origin"],
                        "date": CURRENT_DATE,           
                        "exchange_rate": us["exchange_rate"],
                        "time": CURRENT_TIME
                    })

            if final_rows:
##                with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
##                    writer = csv.DictWriter(f, fieldnames=final_rows[0].keys())
##                    writer.writeheader()
##                    writer.writerows(final_rows)
                print(f"✅ Success! Generated comparison with {len(final_rows)} matches.")

if __name__ == "__main__":
    main()
