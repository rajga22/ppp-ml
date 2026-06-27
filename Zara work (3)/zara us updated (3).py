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
-> Black
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


def open_composition_panel(page):
"""
Tries to open the "COMPOSITION, CARE & ORIGIN" section/panel on Zara US.
"""
candidates = [
"text=COMPOSITION, CARE & ORIGIN",
"text=COMPOSITION",
"text=Composition, care & origin",
"text=Composition",
"button:has-text('COMPOSITION')",
"button:has-text('Composition')",
"div[role='button']:has-text('COMPOSITION')",
"div[role='button']:has-text('Composition')",
"a:has-text('COMPOSITION')",
"a:has-text('Composition')",
]

for sel in candidates:
try:
el = page.query_selector(sel)
if el:
el.click()
page.wait_for_timeout(900)
return True
except Exception:
pass
return False


def extract_materials_and_origin(page):
"""
Opens the Composition panel and extracts:
- materials_text: specific materials (viscose/cotton/etc.)
- made_in: e.g. 'Morocco'
"""
open_composition_panel(page)
page.wait_for_timeout(1500)

# 1) Country of origin
made_in = None
try:
body_text = page.inner_text("body")
m = re.search(r"Made in\s+([A-Za-z][A-Za-z\s\-]+)", body_text)
if m:
made_in = m.group(1).strip()
except Exception:
pass

# 2) Composition lines (tight filtering)
materials = []
seen = set()

try:
els = page.query_selector_all("li, p, span, div")
except Exception:
els = []

bad_contains = [
"skip to main content",
"shopping bag",
"log in",
"help",
"search",
"zara united states",
"check in-store",
"shipping",
"returns",
]

good_keywords = [
"outer shell",
"lining",
"composition",
"shell",
"main fabric",
"secondary fabric",
"filling",
"padding",
"contains",
"exclusive of",
"trim",
]

material_words = [
"cotton", "viscose", "polyester", "wool", "linen", "silk", "elastane",
"nylon", "acrylic", "modal", "rayon", "leather", "suede", "cashmere",
"polyamide", "spandex"
]

for el in els:
try:
txt = (el.inner_text() or "").strip()
except Exception:
continue

if not txt:
continue

low = txt.lower()

# Kill obvious UI text
if any(b in low for b in bad_contains):
continue

# Remove price/discount lines
if "₹" in txt or "$" in txt:
continue
if re.search(r"\b-?\d{1,3}\s*%\b", txt):
continue

# Avoid giant blobs
if len(txt) > 120:
continue

looks_like_composition = False
if "%" in txt and any(w in low for w in material_words):
looks_like_composition = True
if any(k in low for k in good_keywords):
looks_like_composition = True

if not looks_like_composition:
continue

key = low
if key in seen:
continue
seen.add(key)

materials.append(txt)

materials_text = " | ".join(materials) if materials else None
return materials_text, made_in


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
print("BLOCKED (captcha/access denied). Stopping early.")
break

html = page.content()
has_img = "static.zara.net" in html.lower()

colour = parse_colour_from_title(title)
price_cur, price_orig = pick_prices_usd(page)
discount_display = pick_discount_pct_display(page)

# NEW: composition + origin
materials_text, made_in = extract_materials_and_origin(page)

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
"materials_text": materials_text,
"made_in": made_in,
"currency": "USD",
}
)

print(" title:", (title or "")[:90])
print(" materials_text:", materials_text)
print(" made_in:", made_in)

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
"materials_text",
"made_in",
"currency",
],
)
writer.writeheader()
writer.writerows(rows)

print("Saved to", out)


if __name__ == "__main__":
main()
