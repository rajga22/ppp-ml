import csv
import re
import time
import random
from pathlib import Path
from playwright.sync_api import sync_playwright

# INR patterns like "₹ 3,990" or "₹3,990.00"
INR_RE = re.compile(r"₹\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)")

# Discount badge like "-80 %" / "80%"
PCT_RE = re.compile(r"(-?\s*\d{1,3})\s*%")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

# ---- FX ----
# INR per 1 USD. Update this to whatever rate you want to use.
FX_INR_PER_USD = 83.0


def inr_to_usd(inr_amount: float, fx_inr_per_usd: float = FX_INR_PER_USD) -> float:
if inr_amount is None:
return None
if fx_inr_per_usd <= 0:
return None
return inr_amount / fx_inr_per_usd


def safe_float(s):
try:
return float(s)
except Exception:
return None


def parse_colour_from_title(title: str):
"""
Zara title usually: "PRODUCT NAME - Colour | ZARA India"
Returns colour or None.
"""
if not title:
return None
t = title.strip()

# take left side of "|"
left = t.split("|")[0].strip()

# colour is usually after the last " - "
if " - " in left:
colour = left.rsplit(" - ", 1)[-1].strip()
if 1 <= len(colour) <= 40:
return colour

return None


def pick_discount_pct_display(page):
"""
Try to extract the discount badge shown on the page, e.g. "-80 %".
We search in likely price containers first, then fallback to body.
Returns a string like "-80" or "80" (without %), or None.
"""
def text_if(selector: str):
try:
el = page.query_selector(selector)
if not el:
return None
txt = (el.inner_text() or "").strip()
return txt if txt else None
except Exception:
return None

# try common-ish containers around prices
candidates = [
"[data-qa-id='product-price']",
"[data-testid='product-price']",
"[class*='price']",
"[class*='discount']",
"span:has-text('%')",
]

text_blob = None
for sel in candidates:
t = text_if(sel)
if t and "%" in t:
text_blob = t
break

if not text_blob:
# fallback: whole page text (can be noisy)
text_blob = page.inner_text("body")

# find a percent; prefer negative ones like "-80"
matches = PCT_RE.findall(text_blob)
if not matches:
return None

cleaned = []
for m in matches:
m2 = m.replace(" ", "")
# keep sane values only
try:
v = int(m2)
if -99 <= v <= 99 and v != 0:
cleaned.append(v)
except Exception:
pass

if not cleaned:
return None

# prefer negative discount like -80, else first
negs = [v for v in cleaned if v < 0]
chosen = negs[0] if negs else cleaned[0]
return str(chosen)


def pick_prices_inr(page):
"""
More robust extraction:
- Collect text from multiple likely price selectors (including old/original/strikethrough)
- Parse all ₹ amounts
Returns (current, original) as strings formatted to 2 decimals, or (None, None).
"""
def texts_for(selector: str):
out = []
try:
els = page.query_selector_all(selector)
for el in els or []:
try:
t = (el.inner_text() or "").strip()
if t and "₹" in t:
out.append(t)
except Exception:
pass
except Exception:
pass
return out

selectors = [
"[data-qa-id='product-price']",
"[data-testid='product-price']",
# common price areas
"[class*='price']",
# old/original price patterns
"del:has-text('₹')",
"s:has-text('₹')",
"[class*='old']:has-text('₹')",
"[class*='original']:has-text('₹')",
"[class*='previous']:has-text('₹')",
"span:has-text('₹')",
]

blobs = []
for sel in selectors:
blobs.extend(texts_for(sel))

price_text = "\n".join(blobs).strip() if blobs else None

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


def compute_sale_fields(price_current_str, price_original_str, discount_pct_display_str):
"""
Determine on_sale:
- If discount badge exists -> on_sale True
- Else if original > current -> on_sale True
Also computes discount_pct_calc (from prices) when possible.
"""
cur = safe_float(price_current_str)
orig = safe_float(price_original_str)

# on_sale from badge
if discount_pct_display_str is not None:
on_sale = True
else:
on_sale = (cur is not None and orig is not None and orig > cur)

# computed discount from prices (only if both exist)
discount_pct_calc = None
if cur is not None and orig is not None and orig > 0 and orig > cur:
discount_pct_calc = f"{(1.0 - (cur / orig)) * 100.0:.2f}"

# USD conversion
price_current_usd = f"{inr_to_usd(cur):.2f}" if cur is not None else None

# sale_price_usd should only be filled if on_sale
sale_price_usd = price_current_usd if on_sale else None

return on_sale, discount_pct_calc, price_current_usd, sale_price_usd


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
print(" ERROR loading:", repr(e))
continue

title = (page.title() or "").strip()
body_text = page.inner_text("body").lower()

if "access denied" in body_text or "captcha" in body_text:
print(" BLOCKED (access denied/captcha). Stopping early.")
break

html = page.content()
has_img = "static.zara.net" in html.lower()

# Colour from title (what you asked)
colour_from_title = parse_colour_from_title(title)

# Prices and discount badge
price_current_inr, price_original_inr = pick_prices_inr(page)
discount_pct_display = pick_discount_pct_display(page) # e.g. "-80"

on_sale, discount_pct_calc, price_current_usd, sale_price_usd = compute_sale_fields(
price_current_inr,
price_original_inr,
discount_pct_display,
)

rows.append(
{
"name": title if title else None,
"colour_from_title": colour_from_title,
"has_static_image": has_img,
"price_current_inr": price_current_inr,
"price_current_usd": price_current_usd, # USD for ALL items
"price_original_inr": price_original_inr, # original (higher) price if found
"discount_pct_display": discount_pct_display, # badge from site (e.g. -80)
"discount_pct_calc": discount_pct_calc, # computed from prices when possible
"on_sale": on_sale,
"sale_price_usd": sale_price_usd, # only populated when on_sale
"currency": "INR",
}
)

print(" title:", title[:90])
print(" colour_from_title:", colour_from_title)
print(" price_current_inr:", price_current_inr, "| price_original_inr:", price_original_inr)
print(" discount_pct_display:", discount_pct_display, "| discount_pct_calc:", discount_pct_calc)
print(" on_sale:", on_sale)
print(" price_current_usd:", price_current_usd, "| sale_price_usd:", sale_price_usd)

browser.close()

out = "/Users/ananya/Desktop/zara_in.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
w = csv.DictWriter(
f,
fieldnames=[
"name",
"colour_from_title",
"has_static_image",
"price_current_inr",
"price_current_usd",
"price_original_inr",
"discount_pct_display",
"discount_pct_calc",
"on_sale",
"sale_price_usd",
"currency",
],
)
w.writeheader()
w.writerows(rows)

print(f"\nSaved {len(rows)} rows to {out}")


if __name__ == "__main__":
main()
