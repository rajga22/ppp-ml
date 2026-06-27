import csv
import re
import time
import random
from pathlib import Path
from playwright.sync_api import sync_playwright

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

USD_RE = re.compile(r"\$\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)")
PCT_RE = re.compile(r"(-?\s*\d{1,2})\s*%")

TARGET_GOOD = 10


def safe_float(x):
    try:
        return float(x)
    except Exception:
        return None


def looks_like_wrong_redirect(title: str):
    if not title:
        return False
    low = title.lower()
    if " - men |" in low or " - kids |" in low or " - teen |" in low:
        return True
    if "home | mango" in low:
        return True
    return False


def parse_colour_from_page(page):
    def clean(s: str):
        if not s:
            return None
        s = " ".join(s.replace("\n", " ").split()).strip()

        prefixes = [
            "select a colour",
            "select colour",
            "select a color",
            "select color",
            "choose colour",
            "choose color",
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

    # 1) Swatch-row anchored JS search
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

    # 2) Right-panel fallback scan
    try:
        title = (page.title() or "").strip().lower()
    except Exception:
        title = ""

    try:
        els = page.query_selector_all("main span, main p, main strong, main label, main div")
        for el in els[:450]:
            t = clean(el.inner_text())
            if not looks_like_colour(t):
                continue
            if title and t.lower() in title:
                continue
            return t
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
    current = f"{lo:.2f}"
    original = f"{hi:.2f}" if hi != lo else None
    return current, original


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


def click_see_details_and_composition(page):
    for sel in ["text=SEE DETAILS", "button:has-text('SEE DETAILS')", "a:has-text('SEE DETAILS')"]:
        try:
            el = page.query_selector(sel)
            if el:
                el.click()
                page.wait_for_timeout(1200)
                break
        except Exception:
            pass

    for sel in ["text=COMPOSITION AND CARE", "button:has-text('COMPOSITION AND CARE')", "a:has-text('COMPOSITION AND CARE')"]:
        try:
            el = page.query_selector(sel)
            if el:
                el.click()
                page.wait_for_timeout(1200)
                return
        except Exception:
            pass


def extract_materials_and_origin(page):
    click_see_details_and_composition(page)
    body = page.inner_text("body")

    made_in = None
    m = re.search(r"Manufacture:\s*([A-Za-z][A-Za-z\s\\-]+)", body)
    if m:
        made_in = m.group(1).strip()

    material_words = [
        "cotton", "viscose", "polyamide", "polyester", "wool", "linen", "silk",
        "elastane", "nylon", "acrylic", "modal", "rayon", "leather", "cashmere",
        "spandex", "lyocell"
    ]

    lines = []
    seen = set()
    for line in body.splitlines():
        s = line.strip()
        if not s or len(s) > 180:
            continue
        low = s.lower()
        if ("composition" in low or "%" in s) and any(w in low for w in material_words):
            if low not in seen:
                seen.add(low)
                lines.append(s)

    materials_text = " | ".join(lines) if lines else None
    return materials_text, made_in


def main():
    url_file = Path("mango_urls_us.txt")
    if not url_file.exists():
        print("Missing mango_urls_us.txt")
        return

    urls = [u.strip() for u in url_file.read_text().splitlines() if u.strip()]
    print(f"Will render up to {len(urls)} Mango US URLs (target {TARGET_GOOD} valid)")

    rows = []
    bad_urls = []
    good_count = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(user_agent=UA, locale="en-US")
        page = context.new_page()

        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Loading (US): {url}")
            time.sleep(random.uniform(2.0, 3.5))

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3500)
            except Exception as e:
                print("  ERROR loading:", repr(e))
                bad_urls.append(url)
                continue

            title = (page.title() or "").strip()
            low_body = page.inner_text("body").lower()

            if "access denied" in low_body or "captcha" in low_body:
                print("  BLOCKED (captcha/access denied). Stopping.")
                break

            if looks_like_wrong_redirect(title):
                print("  ⚠️ Redirected to wrong section:", title)
                bad_urls.append(url)
                continue

            colour = parse_colour_from_page(page)

            price_current_local, price_original_local = pick_prices_usd(page)
            cur = safe_float(price_current_local)
            orig = safe_float(price_original_local)

            discount_pct_display = pick_discount_pct_display(page)

            on_sale = (discount_pct_display is not None) or (cur is not None and orig is not None and orig > cur)

            discount_pct_calc = None
            if cur is not None and orig is not None and orig > cur and orig > 0:
                discount_pct_calc = f"{(1 - (cur / orig)) * 100:.2f}"

            materials_text, made_in = extract_materials_and_origin(page)

            is_valid = (title and price_current_local is not None and materials_text is not None)

            print("  title:", title[:90])
            print("  colour:", colour)
            print("  price_current_local:", price_current_local, "| price_original_local:", price_original_local)
            print("  discount_pct_display:", discount_pct_display, "| discount_pct_calc:", discount_pct_calc)
            print("  materials_text:", materials_text)
            print("  made_in:", made_in)

            if not is_valid:
                bad_urls.append(url)
                continue

            rows.append({
                "name": title,
                "colour_from_title": colour,
                "price_current_usd": price_current_local,
                "price_current_local": price_current_local,
                "price_original_local": price_original_local,
                "discount_pct_display": discount_pct_display,
                "discount_pct_calc": discount_pct_calc,
                "on_sale": on_sale,
                "materials_text": materials_text,
                "made_in": made_in,
                "currency": "USD",
            })

            good_count += 1
            if good_count >= TARGET_GOOD:
                print(f"\n🎯 Reached {TARGET_GOOD} valid products. Stopping early.")
                break

        browser.close()

    out = Path.home() / "Desktop" / "mango_us.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "name",
                "colour_from_title",
                "price_current_usd",
                "price_current_local",
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

    print(f"\n✅ Saved {len(rows)} valid rows to {out}")

    if bad_urls:
        bad_out = Path("mango_bad_us_urls.txt")
        bad_out.write_text("\n".join(bad_urls) + "\n")
        print(f"⚠️ Saved rejected/failed URLs to: {bad_out.resolve()}")


if __name__ == "__main__":
    main()
