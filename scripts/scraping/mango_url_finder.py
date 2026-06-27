import asyncio
import re
from playwright.async_api import async_playwright


async def handle_popups(page):
    close_selectors = [
        'button[aria-label="Close"]',
        'button[aria-label="close"]',
        'button[class*="close"]',
        '[data-testid="close"]',
        '.modal button',
        '.newsletter button'
    ]

    for selector in close_selectors:
        try:
            button = page.locator(selector).first
            if await button.is_visible(timeout=1000):
                await button.click()
                print(f"Closed pop-up: {selector}")
                await page.wait_for_timeout(1000)
        except Exception:
            continue


async def click_show_more_if_present(page):
    texts = [
        "Show more items",
        "Show maximum items",
        "Show more"
    ]

    for text in texts:
        try:
            btn = page.get_by_text(text, exact=False).first
            if await btn.is_visible(timeout=1000):
                await btn.click()
                print(f"Clicked: {text}")
                await page.wait_for_timeout(2500)
                return True
        except Exception:
            continue

    return False


def is_mango_product_url(url: str) -> bool:
    if not url:
        return False

    patterns = [
        r"shop\.mango\.com/.*/p/",
        r"shop\.mango\.com/.+/\d+\.html",
        r"shop\.mango\.com/.+/[0-9]{6,}",
    ]

    return any(re.search(p, url) for p in patterns)


def convert_us_to_india(url: str) -> str:
    return url.replace("/us/en/", "/in/en/")


async def extract_product_links(page):
    hrefs = await page.locator("a").evaluate_all(
        "els => els.map(e => e.href).filter(Boolean)"
    )

    cleaned = []
    seen = set()

    for href in hrefs:
        href = href.split("?")[0].strip()
        if is_mango_product_url(href) and href not in seen:
            seen.add(href)
            cleaned.append(href)

    return cleaned


async def fully_load_page(page, max_rounds=40):
    last_height = 0
    stable_rounds = 0

    for i in range(max_rounds):
        print(f"Load round {i+1}")

        clicked = await click_show_more_if_present(page)

        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2500)

        new_height = await page.evaluate("document.body.scrollHeight")
        print(f"Page height: {new_height}")

        if new_height == last_height and not clicked:
            stable_rounds += 1
        else:
            stable_rounds = 0

        last_height = new_height

        if stable_rounds >= 3:
            print("Page height stopped changing.")
            break


async def harvest_mango_urls(category_url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        print(f"Opening: {category_url}")
        await page.goto(category_url, wait_until="domcontentloaded", timeout=90000)
        await page.wait_for_timeout(4000)

        await handle_popups(page)
        await fully_load_page(page)

        links = await extract_product_links(page)

        print(f"Found {len(links)} product URLs")

        with open("mango_urls_us.txt", "w", encoding="utf-8") as f:
            for link in links:
                f.write(link + "\n")

        with open("mango_urls_in.txt", "w", encoding="utf-8") as f:
            for link in links:
                f.write(convert_us_to_india(link) + "\n")

        print("Saved mango_urls_us.txt and mango_urls_in.txt")
        await browser.close()


if __name__ == "__main__":
    category_url = "https://shop.mango.com/us/en/c/women/tops/227371cd"
    asyncio.run(harvest_mango_urls(category_url))
