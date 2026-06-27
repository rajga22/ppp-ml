import asyncio
from playwright.async_api import async_playwright

async def handle_popups(page):
    # Common selectors for Zara's close buttons (2026 structure)
    close_selectors = [
        'button.layout-catalog-newsletter-modal__close-button', 
        'button.zara-newsletter-modal__close-button',
        'svg[aria-label="Close"]', 
        '.modal-close-icon'
    ]
    
    for selector in close_selectors:
        try:
            # Check if it's visible before clicking
            button = page.locator(selector).first
            if await button.is_visible(timeout=500):
                await button.click()
                print(f"✅ Closed pop-up: {selector}")
                await page.wait_for_timeout(500) # Wait for animation to finish
        except Exception:
            continue # If not found, just move to the next one
        
async def harvest_zara_urls(hicat, syp):
    async with async_playwright() as p:
        category = "".join(syp.split('/')[-1].split('-')[1:3])
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        await context.add_cookies([
        {
            "name": "newsletter-modal-dismissed",
            "value": "true",
            "domain": ".zara.com",
            "path": "/"
        },
        {
            "name": "store-selector-dismissed",
            "value": "true",
            "domain": ".zara.com",
            "path": "/"
        }
        ])
        
        page = await context.new_page()

        print(f"🔗 Accessing Zara US {category}...")
        await page.goto(syp, wait_until="commit")
        await handle_popups(page)

        # --- SCROLL LOGIC START ---
        print("🖱️ Scrolling to load more items...")
        found_count = 0
        max_attempts = 100
        
        for _ in range(max_attempts):
            # Scroll down by 1000 pixels
            await page.mouse.wheel(0, 100)
            # check if scrolling triggered a pop-up
            #await handle_popups(page)
            await page.keyboard.press("Escape")
            # Wait a moment for lazy-load to trigger
            await page.wait_for_load_state("domcontentloaded")
            #await page.wait_for_timeout(2000) 
            
            # Check how many links we have now
            current_links = await page.locator('a.product-link').evaluate_all(
                "elements => elements.map(e => e.href)"
            )
            print("Current links:", current_links)
            
            # Filter for unique product links
            unique_so_far = [u for u in set(current_links) if "-p" in u]
            print(unique_so_far)
            found_count = len(unique_so_far)
            
            print(f"   Found {found_count} products...")
            #if found_count >= 30:
            #    break
        # --- SCROLL LOGIC END ---

        # Final extraction
        all_hrefs = await page.locator('a.product-link').evaluate_all(
            "elements => elements.map(e => e.href)"
        )
        
        unique_us_urls = []
        for url in all_hrefs:
            if url not in unique_us_urls and "-p" in url:
                unique_us_urls.append(url)
            #if len(unique_us_urls) == 30:
            #    break

        # Save to files
        if unique_us_urls:
            with open(f"urls_us_gemini_{hicat}-{category}.txt", "w") as f_us:
                for url in unique_us_urls:
                    f_us.write(f"{url}\n")
            
            with open(f"urls_in_gemini_{hicat}-{category}.txt", "w") as f_in:
                for url in unique_us_urls:
                    f_in.write(f"{url.replace('/us/', '/in/')}\n")
            
            print(f"✅ Success! Saved {len(unique_us_urls)} US and India links to txt files.")
        else:
            print("❌ Still couldn't find enough links.")

        await browser.close()

if __name__ == "__main__":
    women_list = [
    #"https://www.zara.com/us/en/woman-dresses-l1066.html",
    "https://www.zara.com/us/en/woman-tops-l1322.html",
    "https://www.zara.com/us/en/woman-blazers-l758.html",
    "https://www.zara.com/us/en/woman-skirts-l1299.html",
    "https://www.zara.com/us/en/woman-trousers-l1335.html",
    "https://www.zara.com/us/en/woman-jeans-l1055.html",
    "https://www.zara.com/us/en/woman-knitwear-l1152.html",
    "https://www.zara.com/us/en/woman-outerwear-l1184.html",
    "https://www.zara.com/us/en/woman-shoes-l1251.html",
    "https://www.zara.com/us/en/woman-bags-l1024.html"
    ]
    man_list = [
    #"https://www.zara.com/us/en/man-new-in-l711.html",
    #"https://www.zara.com/us/en/man-suits-l808.html"
    #"https://www.zara.com/us/en/man-shirts-l737.html",
    #"https://www.zara.com/us/en/man-t-shirts-l855.html",
    #"https://www.zara.com/us/en/man-trousers-l838.html",
    "https://www.zara.com/us/en/man-jeans-l765.html", # routes to shirts
    #"https://www.zara.com/us/en/man-shoes-l797.html", #nothing
    #"https://www.zara.com/us/en/man-shoes-l769.html?v1=2436382&regionGroupId=133", #nothing
    #"https://www.zara.com/us/en/man-bags-l715.html" #routes to outerwear, nothing
    ]

    kids_list = [
    "https://www.zara.com/us/en/kids-girl-new-in-l391.html",
    "https://www.zara.com/us/en/kids-boy-new-in-l228.html",
    "https://www.zara.com/us/en/kids-girl-dresses-l362.html",
    "https://www.zara.com/us/en/kids-girl-tops-l378.html",
    "https://www.zara.com/us/en/kids-boy-shirts-l184.html",
    "https://www.zara.com/us/en/kids-boy-trousers-l216.html", #routes to knitwear
    #"https://www.zara.com/us/en/kids-girl-shoes-l385.html",
    #"https://www.zara.com/us/en/kids-boy-shoes-l222.html"
    ]

    zara_categories = {"men": man_list, "kids": kids_list, "women": women_list} 
                       
    
    for i in zara_categories:
        for j in zara_categories[i]:
            print(j)
            asyncio.run(harvest_zara_urls(i, j))
