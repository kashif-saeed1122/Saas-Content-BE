import asyncio
import sys
import json
import os

from playwright.async_api import async_playwright

from langchain_community.agent_toolkits import PlayWrightBrowserToolkit

async def scrape_urls(urls: list, headless: bool = True, output_file: str = "scraped_data.json"):
    """
    Scrapes a list of URLs using LangChain for navigation and Native Playwright for extraction.
    Fixes 'ERR_ABORTED' by forcing a real User-Agent globally.
    """
    results = []
    
    print(f"Initializing Hybrid Scraper (Headless: {headless})...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-web-security", 
                "--disable-features=IsolateOrigins,site-per-process",
                "--ignore-certificate-errors"
            ]
        )
        
        # 2. Initialize the Toolkit
        toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=browser)
        tools = toolkit.get_tools()
        
        # Get the navigation tool
        navigate_tool = next((t for t in tools if t.name == "navigate_browser"), None)
        
        if not navigate_tool:
            print("Error: Could not find navigate_tool in PlayWrightBrowserToolkit.")
            return []

        try:
            for url in urls:
                try:
                    print(f"Scraping: {url}")
                    
                    await navigate_tool.arun({"url": url})
                    
                    page = None
                    if browser.contexts and browser.contexts[0].pages:
                        page = browser.contexts[0].pages[0]
                    
                    if page:
                        if "google.com" in page.url:
                            print("  - Waiting for redirect (up to 15s)...")
                            try:
                                for _ in range(30): # 30 * 0.5s = 15s
                                    if "google.com" not in page.url:
                                        break
                                    await asyncio.sleep(0.5)
                                
                                print(f"  - Current URL: {page.url}")
                                
                                try:
                                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
                                except:
                                    pass 
                                
                                await page.wait_for_timeout(3000) 
                            except Exception as e:
                                print(f"  - Redirect warning: {e}")

                        # robustness: ensure body exists
                        try:
                            await page.wait_for_selector("body", timeout=5000)
                        except:
                            pass 

                        try:
                            content = await page.inner_text("body")
                        except Exception:
                            # Fallback: If inner_text fails (rare), try raw JS as last resort
                            try:
                                content = await page.evaluate("document.body.innerText")
                            except:
                                content = ""
                        
                        # Python-side cleaning
                        if content:
                            cleaned_content = " ".join(content.split())
                        else:
                            cleaned_content = ""
                            
                        # Final check for empty/failed scraping
                        if not cleaned_content or len(cleaned_content) < 200:
                             status = "possible_block_or_empty"
                             error_msg = f"Content length low ({len(cleaned_content)} chars). URL might be blocked or empty."
                        else:
                            status = "success"
                            error_msg = None
                    else:
                        content = ""
                        status = "failed"
                        error_msg = "Could not access active page in browser context"

                    results.append({
                        "url": url, 
                        "content": cleaned_content,
                        "status": status,
                        "error": error_msg
                    })
                    
                except Exception as e:
                    print(f"Error processing {url}: {e}")
                    results.append({
                        "url": url, 
                        "error": str(e),
                        "status": "failed"
                    })
                    
        finally:
            print("Closing browser...")
            # Browser context closes automatically when exiting 'async with'
    
    # # 4. Save results to JSON file
    # if output_file:
    #     try:
    #         print(f"Saving data to {output_file}...")
    #         with open(output_file, 'w', encoding='utf-8') as f:
    #             json.dump(results, f, indent=4, ensure_ascii=False)
    #         print("Save complete.")
    #     except Exception as e:
    #         print(f"Failed to save JSON: {e}")
        
    return results

# --- TESTING BLOCK ---
if __name__ == "__main__":
    # Test with the specific Google News link that was failing
    test_urls = [
        "https://news.google.com/rss/articles/CBMiYEFVX3lxTE1iNGl0TjBSdTdfSDNOb3d5bkx3a0RPOGQweGtndFlfY1N6Sk16NVJQNFo5cnlIUy05ZXFkMDdXUDF3YUpUM291cTlwdFdiLTU0OV9EUVVDek95cHRhQlJsWQ?oc=5&hl=en-PK&gl=PK&ceid=PK:en"
    ]
    
    print("Starting Hybrid LangChain Scraper...")
    
    try:
        data = asyncio.run(scrape_urls(test_urls, headless=True, output_file="scraped_data.json"))
        
        print("\n" + "="*50)
        print(f"Process finished.")
        
        for item in data:
            if item['status'] == 'success':
                print(f"✅ {item['url'][:50]}... - {len(item.get('content', ''))} chars")
            else:
                print(f"❌ {item['url'][:50]}... - {item.get('error')}")
                
    except Exception as e:
        print(f"Fatal Error: {e}")