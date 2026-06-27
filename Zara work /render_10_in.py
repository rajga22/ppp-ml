import csv
import re
import time
import random
from pathlib import Path
from playwright.sync_api import sync_playwright

# INR patterns like "₹ 3,990" or "₹3,990.00"
INR_RE = re.compile(r"₹\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"


def pick_prices_inr(page):
    """
    DOM-based extraction: find a likely price block, then parse ₹ amounts inside it.
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
        "span:has-text('₹')",
    ]

    price_text = None
    for sel in candidates:
        t = text_if(sel)
        if t and "₹" in t:
            price_text = t
            break

    if not price_text:
        body = page.inner_text("body")
        if "₹" not in body:
            return None, None
        price_text = body

    matches = INR_RE.findall(price_text)
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
    url_file = Path("urls_in.txt")
    if not url_file.exists():
        print("Missing urls_in.txt (put your India URLs in it, one per line).")
        return

    urls = [u.strip() for u in url_file.read_text().splitlines() if u.strip()]
    urls = urls[:10]
    print(f"Will render {len(urls)} India URLs")

    rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(user_agent=UA, locale="en-IN")
        page = context.new_page()

        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Loading (IN): {url}")

            time.sleep(random.uniform(2.5, 4.5))

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(5000)
            except Exception as e:
                print("  ERROR loading:", repr(e))
                continue

            title = (page.title() or "").strip()
            body_text = page.inner_text("body").lower()

            if "access denied" in body_text or "captcha" in body_text:
                print("  BLOCKED (access denied/captcha). Stopping early.")
                break

            html = page.content()
            has_img = "static.zara.net" in html.lower()

            price_current, price_original = pick_prices_inr(page)

            rows.append(
                {
                    "name": title if title else None,
                    "has_static_image": has_img,
                    "price_current": price_current,
                    "price_original": price_original,
                    "currency": "INR",
                }
            )

            print("  title:", title[:90])
            print("  price_current:", price_current, "| price_original:", price_original)

        browser.close()

    out = "/Users/ananya/Desktop/zara_in.csv"
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
