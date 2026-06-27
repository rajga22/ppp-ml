import csv
import re
import time
import random
from pathlib import Path
from playwright.sync_api import sync_playwright

# Finds money like "$149.00"
USD_RE = re.compile(r"\$\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)")
PCT_RE = re.compile(r"(-?\s*\d{1,3})\s*%")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"


def safe_float(x):
try:
return float(x)
except Exception:
return None


def parse_colour_from_title(title: str):
"""
Example:
'SATIN MIDI DRESS - Black | ZARA United States'
→ Black
"""
if not title:
return None
left = title.split("|")[0].strip()
if " - " in left:
return left.rsplit(" - ", 1)[-1].strip()
return None


def pick_discount_pct_display(page):
text = page.inner_text("body")
matches = PCT_RE.findall(text)
if not matches:
return None

vals = []
for m in matches:
try:
v = int(m.replace(" ", ""))
if -99 <= v <= 99 and v != 0:
vals.append(v)
except Exception:
pass

if not vals:
return None

negs = [v for v in vals if v < 0]
return str(negs[0] if negs else vals[0])


def pick_prices_usd(page):
selectors = [
"[data-qa-id='product-price']",
"[class*='price']",
"del:has-text('$')",
"s:has-text('$')",
"span:has-text('$')",
]

blobs = []
for sel in selectors:
try:
for el in page.query_selector_all(sel):
t = (el.inner_text() or "").strip()
if "$" in t:
blobs.append(t)
except Exception:
pass

text = "\n".join(blobs) if blobs else page.inner_text("body")

vals = []
for m in USD_RE.findall(text):
try:
vals.append(float(m.replace(",", "")))
except Exception:
pass

if not vals:
return None, None

lo, hi = min(vals), max(vals)
return f"{lo:.2f}", (f"{hi:.2f}" if hi != lo else None)


def main():
urls = Path("urls.txt").read_text().splitlines()
urls = [u.strip() for u in urls if u.strip()][:10]

rows = []

with sync_playwright() as p:
browser = p.chromium.launch(headless=False)
context = browser.new_context(user_agent=UA, locale="en-US")
page = context.new_page()

for url in urls:
print("Loading:", url)
time.sleep(random.uniform(2.5, 4.5))
page.goto(url, wait_until="domcontentloaded", timeout=60000)
page.wait_for_timeout(5000)

title = page.title()
low = page.inner_text("body").lower()
if "captcha" in low or "access denied" in low:
break

html = page.content()
has_img = "static.zara.net" in html.lower()

colour = parse_colour_from_title(title)
price_cur, price_orig = pick_prices_usd(page)
discount_display = pick_discount_pct_display(page)

cur = safe_float(price_cur)
orig = safe_float(price_orig)

on_sale = (
discount_display is not None
or (cur is not None and orig is not None and orig > cur)
)

discount_calc = (
f"{(1 - cur / orig) * 100:.2f}"
if cur and orig and orig > cur
else None
)

rows.append(
{
"name": title,
"colour_from_title": colour,
"has_static_image": has_img,
"price_current_local": price_cur,
"price_current_usd": price_cur, # already USD
"price_original_local": price_orig,
"discount_pct_display": discount_display,
"discount_pct_calc": discount_calc,
"on_sale": on_sale,
"currency": "USD",
}
)

browser.close()

out = "/Users/ananya/Desktop/zara_us.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
writer = csv.DictWriter(
f,
fieldnames=[
"name",
"colour_from_title",
"has_static_image",
"price_current_local",
"price_current_usd",
"price_original_local",
"discount_pct_display",
"discount_pct_calc",
"on_sale",
"currency",
],
)
writer.writeheader()
writer.writerows(rows)

print("Saved to", out)


if __name__ == "__main__":
main()
