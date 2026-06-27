import csv
import re
import time
import random
from pathlib import Path
from playwright.sync_api import sync_playwright

USD_RE = re.compile(r"\$\s*([0-9]+(?:\.[0-9]{2})?)")
PCT_RE = re.compile(r"(-?\s*\d{1,3})\s*%")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

def convert_to_india_url(us_url):
    # Replaces the country code 'us' with 'in'
    return us_url.replace("zara.com/us/", "zara.com/in/")

# Example usage:
#us_link = "https://www.zara.com/us/en/satin-lace-dress-zw-collection-p05919040.html?v1=506289211"
#india_link = convert_to_india_url(us_link)
#print(india_link)

def safe_float(x):
    try:
        return float(x)
    except:
        return None


def parse_colour_from_title(title):
    if not title:
        return None
    left = title.split("|")[0]
    return left.rsplit(" - ", 1)[-1].strip() if " - " in left else None


def pick_prices_usd(page):
    prices = [float(p) for p in USD_RE.findall(page.inner_text("body"))]
    if not prices:
        return None, None
    lo, hi = min(prices), max(prices)
    return f"{lo:.2f}", (f"{hi:.2f}" if hi != lo else None)


def pick_discount_pct(page):
    m = PCT_RE.search(page.inner_text("body"))
    return m.group(1) if m else None


def open_composition(page):
    for sel in [
        "text=COMPOSITION, CARE & ORIGIN",
        "text=COMPOSITION",
        "button:has-text('Composition')",
    ]:
        try:
            el = page.query_selector(sel)
            if el:
                el.click()
                page.wait_for_timeout(1200)
                return
        except:
            pass


def extract_materials_and_origin(page):
    open_composition(page)
    page.wait_for_timeout(1200)

    body = page.inner_text("body")

    made_in = None
    m = re.search(r"Made in\s+([A-Za-z ]+)", body)
    if m:
        made_in = m.group(1).strip()

    materials = []
    for line in body.splitlines():
        l = line.lower()
        if "%" in line and any(
            m in l for m in ["cotton", "viscose", "wool", "polyester", "linen", "silk"]
        ):
            if len(line) < 120:
                materials.append(line.strip())

    return " | ".join(dict.fromkeys(materials)) if materials else None, made_in


def main():
    urls = Path("urls_copy_SP.txt").read_text().splitlines()
    urls = [u.strip() for u in urls if u.strip()]
    print(urls)
    rows = []
    in_urls = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(locale="en-US", user_agent=UA)

        for i, url in enumerate(urls, 1):
            print(f"[{i}/{len(urls)}] Loading (US): {url}")
            time.sleep(random.uniform(2.5, 4.5))
            page.goto(url, timeout=30000)
            page.wait_for_timeout(5000)

            title = page.title()
            colour = parse_colour_from_title(title)
            cur, orig = pick_prices_usd(page)
            disc = pick_discount_pct(page)
            materials, made_in = extract_materials_and_origin(page)

            cur_f = safe_float(cur)
            orig_f = safe_float(orig)

            on_sale = disc is not None or (cur_f and orig_f and orig_f > cur_f)
            disc_calc = (
                f"{(1 - cur_f / orig_f) * 100:.2f}" if cur_f and orig_f and orig_f > cur_f else None
            )

            rows.append({
                "name": title,
                "colour_from_title": colour,
                "price_current_local": cur,
                "price_current_usd": cur,
                "price_original_local": orig,
                "discount_pct_display": disc,
                "discount_pct_calc": disc_calc,
                "on_sale": on_sale,
                "materials_text": materials,
                "made_in": made_in,
                "currency": "USD",
            })

            in_urls.append(convert_to_india_url(url))

        browser.close()

    if not rows:
        print("No data collected.")
        return

    out = "zara_us.csv"
    out2 = "zara_in.txt"
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved {len(rows)} rows → {out}")

    with open(out2, "w", newline="", encoding="utf-8") as f:
        for i in in_urls:
            f.write(i + "\n")


if __name__ == "__main__":
    main()
