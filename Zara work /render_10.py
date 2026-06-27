import csv
import re
import time
import random
from pathlib import Path
from playwright.sync_api import sync_playwright

# Finds money like "$ 149.00" or "$149.00"
PRICE_RE = re.compile(r"\$\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"


def pick_prices(page):
    """
    DOM-based extraction of the main product price (more accurate than regex across whole page).
    Returns (current, original).
    """

    def text_if(selector: str):
        try:
            el = page.query_selector(selector)
            if not el:
                return None
            t = el.inner_text().strip()
            return t if t else None
        except Exception:
            return None

    candidates = [
        "[data-qa-id='product-price']",
        "[data-testid='product-price']",
        "[class*='price'] [class*='current']",
        "[class*='price']",
        "span:has-text('$')",
    ]

    current_text = None
    for sel in candidates:
        t = text_if(sel)
        if t and "$" in t:
            current_text = t
            break

    if not current_text:
        return None, None

    matches = PRICE_RE.findall(current_text)
    vals = []
    for m in matches:
        try:
            vals.append(float(m.replace(",", "")))
        except ValueError:
            pass

    if not vals:
        return None, None

    lo, hi = min(vals), max(vals)
    current = f"{lo:.2f}"
    original = f"{hi:.2f}" if hi != lo else None
    return current, original


def main():
    url_file = Path("urls.txt")
    if not url_file.exists():
        print("Missing urls.txt (put 10 URLs in it, one per line).")
        return

    urls = [u.strip() for u in url_file.read_text().splitlines() if u.strip()]
    urls = urls[:10]
    print(f"Will render {len(urls)} URLs")

    rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(user_agent=UA, locale="en-US")
        page = context.new_page()

        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Loading: {url}")

            time.sleep(random.uniform(2.5, 4.5))

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(5000)
            except Exception as e:
                print("  ERROR loading:", repr(e))
                continue

            title = (page.title() or "").strip()
            body_text = page.inner_text("body")

            low = body_text.lower()
            if "access denied" in low or "captcha" in low:
                print("  BLOCKED on this page (access denied/captcha). Stopping early.")
                break

            html = page.content()
            has_img = "static.zara.net" in html.lower()

            price_current, price_original = pick_prices(page)

            rows.append(
                {
                    "name": title if title else None,
                    "has_static_image": has_img,
                    "price_current": price_current,
                    "price_original": price_original,
                    "currency": "USD",
                }
            )

            print("  title:", title[:90])
            print("  has_static_image:", has_img)
            print("  price_current:", price_current, "| price_original:", price_original)

        browser.close()

    out = "/Users/ananya/Desktop/zara_10_test.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["name", "has_static_image", "price_current", "price_original", "currency"],
        )
        w.writeheader()
        w.writerows(rows)

    print(f"\nSaved {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
