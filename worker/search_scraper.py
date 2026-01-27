import logging
from typing import List
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class GoogleSearchScraper:
    """
    Google search scraper using Playwright (No API Key required).
    """

    def __init__(self, query: str):
        self.query = query

    async def search(self, num_results: int = 5) -> List[str]:
        """
        Performs a Google search using a headless browser and extracts result URLs.
        """
        urls = []
        async with async_playwright() as p:
            # Launch browser with arguments to reduce bot detection
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-gpu"
                ]
            )
            
            # Create a context with a realistic user agent
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            page = await context.new_page()

            try:
                logger.info(f"🔎 Scraping Google for: {self.query}")
                
                # Construct Google Search URL (hl=en ensures English results)
                # We request slightly more results than needed to account for ads/filtering
                search_url = f"https://www.google.com/search?q={self.query}&num={num_results + 3}&hl=en"
                
                await page.goto(search_url, timeout=15000, wait_until="domcontentloaded")
                
                # Wait for the main results container
                try:
                    await page.wait_for_selector("div.g", timeout=5000)
                except:
                    logger.warning("Timeout waiting for div.g selector. Page might be different.")

                # Extract links from standard search result headers
                # Selector strategy: Look for the main result container (div.g) and find the first anchor tag
                extracted_links = await page.evaluate("""() => {
                    const results = [];
                    const items = document.querySelectorAll('div.g');
                    for (const item of items) {
                        const anchor = item.querySelector('a');
                        if (anchor && anchor.href) {
                            results.push(anchor.href);
                        }
                    }
                    return results;
                }""")

                # Filter links
                for link in extracted_links:
                    # Skip Google internal links, cached links, or ads
                    if (
                        link.startswith("http") 
                        and "google.com" not in link 
                        and "googleusercontent" not in link
                    ):
                        urls.append(link)
                        if len(urls) >= num_results:
                            break
                            
                logger.info(f"✅ Found {len(urls)} URLs: {urls}")
                
            except Exception as e:
                logger.error(f"❌ Google Scraping Failed: {e}")
            finally:
                await browser.close()
                
        return urls