import csv
import re
import os
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlsplit

import pandas as pd
import requests
from playwright.sync_api import sync_playwright

INPUT_MANGO_URLS = "mango_urls_actual_single_column_326_urls.csv"
REFERENCE_CSV = "zara_combined_men_women_kids.csv"
OUTPUT_FILE = "mango_full_comparison_by_category.csv"

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

USD_RE = re.compile(r"\$\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)")
INR_RE = re.compile(r"₹\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)|Rs\.\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)", re.IGNORECASE)
PCT_RE = re.compile(r"(-?\s*\d{1,2})\s*%")
MANGO_ID_RE = re.compile(r"_(\d+)")

TD_API_KEY = os.getenv("TWELVE_DATA_API_KEY")


def get_live_fx_rate_usd_inr():
    """
    Fetch a live-ish USD/INR rate from Twelve Data.
    Returns: (rate_float, fx_timestamp_utc_iso)
    """
    if not TD_API_KEY:
        raise RuntimeError("Missing TWELVE_DATA_API_KEY environment variable")

    url = "https://api.twelvedata.com/exchange_rate"
    params = {
        "symbol": "USD/INR",
        "apikey": TD_API_KEY,
    }

    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if "rate" not in data:
        raise RuntimeError(f"Unexpected FX response: {data}")

    rate = float(data["rate"])
    ts = data.get("timestamp")

    fx_timestamp_utc = None
    if ts is not None:
        try:
            fx_timestamp_utc = datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
        except Exception:
            fx_timestamp_utc = None

    return rate, fx_timestamp_utc


def safe_float(x):
    try:
        return float(str(x).replace(",", "").strip())
    except Exception:
        return None


def clean_url(url):
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    if "shop.mango.com" not in url:
        return None
    if "/p/" not in url:
        return None
    return url


def get_product_id(url):
    m = MANGO_ID_RE.search(url or "")
    return m.group(1) if m else None


def split_us_in_urls(urls):
    us_map = {}
    in_map = {}
    for url in urls:
        pid = get_product_id(url)
        if not pid:
            continue
        if "/us/en/" in url and pid not in us_map:
            us_map[pid] = url
        elif "/in/en/" in url and pid not in in_map:
            in_map[pid] = url
    return us_map, in_map


def load_reference_category_targets(path):
    if not Path(path).exists():
        return set()
    df = pd.read_csv(path)
    needed = {"Segment", "Source File"}
    if not needed.issubset(df.columns):
        return set()
    targets = set()
    for _, row in df[["Segment", "Source File"]].dropna().iterrows():
        seg = str(row["Segment"]).strip().lower()
        src = str(row["Source File"]).strip().lower()
        targets.add(f"{seg}::{src}")
    return targets


def infer_specific_category_from_url(url):
    path = urlsplit(url).path.lower()

    if "/women/" in path:
        segment = "Women"
    elif "/men/" in path:
        segment = "Men"
    elif any(x in path for x in ["/kids/", "/baby-", "/boys/", "/girls/", "/newborn/"]):
        segment = "Kids"
    else:
        segment = "General"

    source_file = "comparison_misc"

    if "/women/dresses-and-jumpsuits/" in path:
        source_file = "comparison_dresses"
    elif "/women/tops/" in path or "/women/shirts---blouses/" in path:
        source_file = "comparison_tops"
    elif "/women/skirts/" in path:
        source_file = "comparison_skirts"
    elif "/women/trousers/" in path:
        source_file = "comparison_trousers"
    elif "/women/jeans/" in path:
        source_file = "comparison_jeans"
    elif "/women/sweaters-and-cardigans/" in path or "/women/knitwear/" in path:
        source_file = "comparison_knitwear"
    elif "/women/jackets/" in path or "/women/coats/" in path or "/women/outerwear/" in path:
        source_file = "comparison_outerwear"
    elif "/women/shoes/" in path:
        source_file = "comparison_shoes"
    elif "/women/bags/" in path:
        source_file = "comparison_bags"
    elif "/men/shirts/" in path:
        source_file = "comparison_men_shirts"
    elif "/men/t-shirts/" in path:
        source_file = "comparison_tshirts"
    elif "/men/trousers/" in path:
        source_file = "comparison_men_trousers"
    elif "/men/jeans/" in path:
        source_file = "comparison_men_jeans"
    elif "/men/sweaters-and-cardigans/" in path:
        source_file = "comparison_men_knitwear"
    elif "/men/jackets-and-overshirts/" in path or "/men/coats/" in path:
        source_file = "comparison_men_outerwear"
    elif "/men/blazers/" in path or "/men/suits/" in path:
        source_file = "comparison_men_suits"
    elif "/men/shoes/" in path:
        source_file = "comparison_men_shoes"
    elif "/men/bags/" in path:
        source_file = "comparison_men_bags"
    elif any(x in path for x in ["/kids-girl/", "/girl-", "/baby-girls/"]):
        if "/dresses" in path:
            source_file = "comparison_girldresses"
        elif "/tops" in path or "/shirts" in path or "/blouses" in path:
            source_file = "comparison_girltops"
        else:
            source_file = "comparison_girlnew"
    elif any(x in path for x in ["/kids-boy/", "/boy-", "/baby-boys/", "/boys/"]):
        if "/shirts" in path:
            source_file = "comparison_boyshirts"
        elif "/trousers" in path or "/jeans" in path:
            source_file = "comparison_boytrousers"
        else:
            source_file = "comparison_boynew"

    specific_category = f"{segment}_{source_file.replace('comparison_', '')}"
    return segment, source_file, specific_category


def parse_colour_from_page(page):
    def clean(s: str):
        if not s:
            return None
        s = " ".join(s.replace("\n", " ").split()).strip()
        prefixes = [
            "select a colour", "select colour", "select a color", "select color",
            "choose colour", "choose color",
        ]
        low = s.lower()
        for p in prefixes:
            if low.startswith(p):
                s = s[len(p):].strip()
                break
        return s

    def looks_like_colour(s: str):
        if not s:
            return False
        low = s.lower()
        banned = {
            "skip to main content", "size guide", "see look", "add", "wishlist",
            "women", "men", "kids", "teen", "search", "bag", "log in", "help"
        }
        if low in banned:
            return False
        if "rs." in low or "$" in low or "%" in low:
            return False
        if re.fullmatch(r"\d+", s):
            return False
        if s.isupper() and len(s) > 8:
            return False
        if len(s) < 3 or len(s) > 35:
            return False
        if not re.fullmatch(r"[A-Za-z]+([ \-][A-Za-z]+)*", s):
            return False
        return True

    try:
        candidate = page.evaluate(
            """
            () => {
              function isVisible(el){
                const s = getComputedStyle(el);
                if (s.display==='none'||s.visibility==='hidden'||s.opacity==='0') return false;
                const r = el.getBoundingClientRect();
                return r.width>0 && r.height>0;
              }

              const divs = Array.from(document.querySelectorAll("div"));
              for (const d of divs) {
                if (!isVisible(d)) continue;

                const squares = Array.from(d.querySelectorAll("button, [role='button'], div, span"))
                  .filter(x => {
                    if (!isVisible(x)) return false;
                    const r = x.getBoundingClientRect();
                    return r.width >= 10 && r.width <= 40 && r.height >= 10 && r.height <= 40;
                  });

                if (squares.length >= 2) {
                  const row = d.parentElement || d;
                  const texts = Array.from(row.querySelectorAll("span, p, div, strong, label"))
                    .map(el => (el.innerText || "").trim())
                    .map(t => t.split("\\n")[0].trim())
                    .filter(t => t && t.length >= 3 && t.length <= 60);

                  const mixed = texts.find(t => /[a-z]/.test(t) && /[A-Z]/.test(t));
                  if (mixed) return mixed;

                  return texts[0] || null;
                }
              }
              return null;
            }
            """
        )
        candidate = clean(candidate)
        if candidate and looks_like_colour(candidate):
            return candidate
    except Exception:
        pass

    return None


def pick_prices_usd(page):
    text = page.inner_text("body")
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


def pick_prices_inr(page):
    text = page.inner_text("body")
    vals = []
    for m1, m2 in INR_RE.findall(text):
        raw = m1 or m2
        if raw:
            try:
                vals.append(float(raw.replace(",", "")))
            except Exception:
                pass
    if not vals:
        return None, None
    lo, hi = min(vals), max(vals)
    return f"{lo:.2f}", (f"{hi:.2f}" if hi != lo else None)


def pick_discount_pct_display(page):
    text = page.inner_text("body")
    matches = PCT_RE.findall(text)
    cleaned = []
    for m in matches:
        m2 = m.replace(" ", "")
        try:
            v = int(m2)
            if -90 <= v <= 90 and v != 0:
                cleaned.append(v)
        except Exception:
            pass
    if not cleaned:
        return None
    negs = [v for v in cleaned if v < 0]
    return str(negs[0]) if negs else None


def open_details_and_composition(page):
    detail_selectors = [
        "text=SEE DETAILS",
        "text=See details",
        "text=DETAILS",
        "text=Details",
        "text=Product details",
        "button:has-text('SEE DETAILS')",
        "button:has-text('See details')",
        "button:has-text('DETAILS')",
        "button:has-text('Details')",
        "button:has-text('Product details')",
        "a:has-text('SEE DETAILS')",
        "a:has-text('See details')",
        "[role='button']:has-text('DETAILS')",
        "[role='button']:has-text('Details')",
    ]

    composition_selectors = [
        "text=COMPOSITION AND CARE",
        "text=Composition and care",
        "text=COMPOSITION",
        "text=Composition",
        "text=MATERIALS",
        "text=Materials",
        "text=Care",
        "button:has-text('COMPOSITION AND CARE')",
        "button:has-text('Composition and care')",
        "button:has-text('COMPOSITION')",
        "button:has-text('Composition')",
        "button:has-text('MATERIALS')",
        "button:has-text('Materials')",
        "a:has-text('COMPOSITION AND CARE')",
        "a:has-text('Composition and care')",
        "[role='button']:has-text('COMPOSITION')",
        "[role='button']:has-text('Composition')",
        "[role='button']:has-text('Materials')",
    ]

    opened_detail = None
    for sel in detail_selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible(timeout=1000):
                loc.click(timeout=2000)
                page.wait_for_timeout(700)
                opened_detail = sel
                break
        except Exception:
            pass

    opened_comp = None
    for sel in composition_selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible(timeout=1000):
                loc.click(timeout=2000)
                page.wait_for_timeout(700)
                opened_comp = sel
                break
        except Exception:
            pass

    return opened_detail, opened_comp


def extract_materials_and_origin(page):
    opened_detail, opened_comp = open_details_and_composition(page)
    body = page.inner_text("body")

    made_in = None
    made_patterns = [
        r"Manufacture:\s*([A-Za-z][A-Za-z\s\-]+)",
        r"Made in\s*([A-Za-z][A-Za-z\s\-]+)",
        r"Origin\s*[:\-]?\s*([A-Za-z][A-Za-z\s\-]+)",
    ]

    for pat in made_patterns:
        m = re.search(pat, body, flags=re.IGNORECASE)
        if m:
            made_in = m.group(1).strip()
            break

    material_words = [
        "cotton", "viscose", "polyamide", "polyester", "wool", "linen", "silk",
        "elastane", "nylon", "acrylic", "modal", "rayon", "leather", "cashmere",
        "spandex", "lyocell"
    ]

    lines = []
    seen = set()
    for line in body.splitlines():
        s = " ".join(line.strip().split())
        if not s or len(s) > 200:
            continue
        low = s.lower()
        if "%" in s and any(w in low for w in material_words):
            if low not in seen:
                seen.add(low)
                lines.append(s)
                continue
        if ("composition" in low or "material" in low) and any(w in low for w in material_words):
            if low not in seen:
                seen.add(low)
                lines.append(s)

    materials_text = " | ".join(lines) if lines else None
    return materials_text, made_in, opened_detail, opened_comp


def load_product_page(page, url):
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(1200)


def main():
    if not TD_API_KEY:
        raise RuntimeError("Set your Twelve Data key first: export TWELVE_DATA_API_KEY='YOUR_KEY'")

    if not Path(INPUT_MANGO_URLS).exists():
        print(f"Missing {INPUT_MANGO_URLS}")
        return

    urls_df = pd.read_csv(INPUT_MANGO_URLS)
    if "url" not in urls_df.columns:
        print("Input Mango CSV must have a column named 'url'")
        return

    raw_urls = [clean_url(u) for u in urls_df["url"].dropna().tolist()]
    raw_urls = [u for u in raw_urls if u]

    us_map, in_map = split_us_in_urls(raw_urls)
    shared_ids = sorted(set(us_map) & set(in_map))

    print(f"Found {len(shared_ids)} matched Mango US/IN products")

    reference_targets = load_reference_category_targets(REFERENCE_CSV)
    if reference_targets:
        print(f"Loaded {len(reference_targets)} reference Segment/Source File combinations from {REFERENCE_CSV}")

    final_rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        context_us = browser.new_context(user_agent=UA, locale="en-US")
        context_in = browser.new_context(user_agent=UA, locale="en-IN")

        page_us = context_us.new_page()
        page_in = context_in.new_page()

        for i, pid in enumerate(shared_ids, 1):
            us_url = us_map[pid]
            in_url = in_map[pid]

            row_collected_at_local = datetime.now().astimezone().isoformat()
            row_collected_at_utc = datetime.now(timezone.utc).isoformat()

            try:
                fx_inr_per_usd, fx_timestamp_utc = get_live_fx_rate_usd_inr()
            except Exception as e:
                raise RuntimeError(f"Live FX failed for {pid}: {e}")

            print(f"\n[{i}/{len(shared_ids)}] {pid}")
            print(" US:", us_url)
            print(" IN:", in_url)
            print(" FX:", fx_inr_per_usd, fx_timestamp_utc)

            try:
                load_product_page(page_us, us_url)
            except Exception as e:
                print("  US load failed:", repr(e))
                continue

            us_title = (page_us.title() or "").strip()
            us_body = page_us.inner_text("body").lower()
            if "access denied" in us_body or "captcha" in us_body:
                print("  US blocked. stopping.")
                break

            try:
                load_product_page(page_in, in_url)
            except Exception as e:
                print("  IN load failed:", repr(e))
                continue

            in_body_low = page_in.inner_text("body").lower()
            if "access denied" in in_body_low or "captcha" in in_body_low:
                print("  IN blocked. stopping.")
                break

            colour = parse_colour_from_page(page_us)

            us_cur_s, us_orig_s = pick_prices_usd(page_us)
            us_cur = safe_float(us_cur_s)
            us_orig = safe_float(us_orig_s)
            us_disc = pick_discount_pct_display(page_us)
            us_disc_calc = None
            if us_cur is not None and us_orig is not None and us_orig > us_cur:
                us_disc_calc = f"{(1 - (us_cur / us_orig)) * 100:.2f}"
            us_on_sale = (us_disc is not None) or (us_cur is not None and us_orig is not None and us_orig > us_cur)

            in_cur_s, in_orig_s = pick_prices_inr(page_in)
            in_cur = safe_float(in_cur_s)
            in_orig = safe_float(in_orig_s)
            in_disc = pick_discount_pct_display(page_in)
            in_disc_calc = None
            if in_cur is not None and in_orig is not None and in_orig > in_cur:
                in_disc_calc = f"{(1 - (in_cur / in_orig)) * 100:.2f}"
            in_on_sale = (in_disc is not None) or (in_cur is not None and in_orig is not None and in_orig > in_cur)

            materials_text, made_in, opened_detail_us, opened_comp_us = extract_materials_and_origin(page_us)
            _, _, opened_detail_in, opened_comp_in = extract_materials_and_origin(page_in)

            segment, source_file, specific_category = infer_specific_category_from_url(us_url)

            in_cur_usd = round(in_cur / fx_inr_per_usd, 2) if in_cur is not None else None
            in_orig_usd = round(in_orig / fx_inr_per_usd, 2) if in_orig is not None else None

            savings_usd = None
            if us_cur is not None and in_cur_usd is not None:
                savings_usd = round(us_cur - in_cur_usd, 2)

            final_rows.append({
                "Product_ID": pid,
                "Segment": segment,
                "Source File": source_file,
                "Specific_Category": specific_category,
                "US_url": us_url,
                "IN_url": in_url,
                "name": us_title,
                "colour_from_title": colour,
                "US_price_current_usd": us_cur,
                "US_price_original_usd": us_orig,
                "US_discount_pct_display": us_disc,
                "US_discount_pct_calc": us_disc_calc,
                "US_on_sale": us_on_sale,
                "IN_price_current_inr": in_cur,
                "IN_price_original_inr": in_orig,
                "IN_price_current_usd": in_cur_usd,
                "IN_price_original_usd": in_orig_usd,
                "IN_discount_pct_display": in_disc,
                "IN_discount_pct_calc": in_disc_calc,
                "IN_on_sale": in_on_sale,
                "Savings_USD": savings_usd,
                "materials_text": materials_text,
                "made_in": made_in,
                "US_detail_selector": opened_detail_us,
                "US_composition_selector": opened_comp_us,
                "IN_detail_selector": opened_detail_in,
                "IN_composition_selector": opened_comp_in,
                "row_collected_at_local": row_collected_at_local,
                "row_collected_at_utc": row_collected_at_utc,
                "fx_rate_live_usd_inr": fx_inr_per_usd,
                "fx_rate_timestamp_utc": fx_timestamp_utc,
            })

        browser.close()

    if not final_rows:
        print("❌ No matched rows produced.")
        return

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=final_rows[0].keys())
        writer.writeheader()
        writer.writerows(final_rows)

    print(f"\n✅ Saved {len(final_rows)} rows to {OUTPUT_FILE}")

    out_dir = Path("mango_category_outputs")
    out_dir.mkdir(exist_ok=True)

    df_out = pd.DataFrame(final_rows)
    for cat, sub in df_out.groupby("Specific_Category"):
        safe = re.sub(r"[^a-zA-Z0-9_\-]+", "_", str(cat))
        sub.to_csv(out_dir / f"{safe}.csv", index=False)

    print(f"✅ Also wrote per-category files into: {out_dir.resolve()}")


if __name__ == "__main__":
    main()
