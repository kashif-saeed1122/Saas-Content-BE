import logging
from typing import List, Dict
from langchain.tools import tool
from gnews import GNews
# import requests  # Commented out for now
from config import Config

logger = logging.getLogger(__name__)

# Global counter for API usage
API_USAGE_COUNTER = 0

@tool
def search_tool(query: str) -> List[Dict]:
    """
    Searches for a topic using Google News first. 
    If no news is found, returns empty list (Google API fallback disabled).
    Returns standardized articles with 'source_origin' tag.
    """
    global API_USAGE_COUNTER
    
    # --- STEP 1: Try Google News ---
    logger.info(f"🕵️ Checking Google News for: {query}")
    try:
        google_news = GNews(language='en', country='US', max_results=10)
        results = google_news.get_news(query)
        
        if results and len(results) > 0:
            logger.info(f"✅ Found {len(results)} results on Google News.")
            # Tag as Google News
            return [_standardize_result(item, source_type="Google News") for item in results[:5]]
    except Exception as e:
        logger.error(f"⚠️ Google News failed: {e}")

    # --- STEP 2: Fallback to Google API (DISABLED) ---
    logger.warning("⚠️ No news found. Google API fallback is DISABLED.")
    
    # COMMENTED OUT - Enable when you have Google API working
    # logger.info("⚠️ No news found (or error). Switching to Google Custom Search API...")
    # 
    # if API_USAGE_COUNTER >= Config.DAILY_API_LIMIT:
    #     logger.warning(f"⛔ API Limit Reached ({API_USAGE_COUNTER}/{Config.DAILY_API_LIMIT}). Search locked.")
    #     return []
    #
    # api_results = _google_api_search(query)
    # 
    # if api_results:
    #     API_USAGE_COUNTER += 1
    #     logger.info(f"✅ Found {len(api_results)} results via API. (Usage: {API_USAGE_COUNTER}/{Config.DAILY_API_LIMIT})")
    #     return api_results
    
    logger.warning("❌ No results found in News or Search API.")
    return []

# COMMENTED OUT - Uncomment when you enable Google API
# def _google_api_search(query: str):
#     if not Config.GOOGLE_API_KEY or not Config.GOOGLE_CSE_ID:
#         logger.error("❌ Missing GOOGLE_API_KEY or GOOGLE_CSE_ID.")
#         return []
#
#     url = "https://www.googleapis.com/customsearch/v1"
#     params = {
#         "key": Config.GOOGLE_API_KEY,
#         "cx": Config.GOOGLE_CSE_ID,
#         "q": query,
#         "num": 5
#     }
#
#     try:
#         resp = requests.get(url, params=params)
#         resp.raise_for_status()
#         data = resp.json()
#         
#         if "items" not in data:
#             return []
#             
#         return [_standardize_result(item, source_type="Google Custom Search", is_api=True) for item in data["items"]]
#
#     except Exception as e:
#         logger.error(f"❌ Google API Error: {e}")
#         return []

def _standardize_result(item, source_type, is_api=False):
    """
    Standardizes output and adds 'source_origin'.
    """
    if is_api:
        # This is for Google Custom Search API results
        from datetime import datetime
        published_date = "Unknown"
        if "pagemap" in item and "metatags" in item["pagemap"]:
            metatags = item["pagemap"]["metatags"][0]
            published_date = metatags.get("article:published_time", 
                             metatags.get("date", 
                             datetime.now().strftime("%Y-%m-%d")))

        return {
            "url": item.get("link"),
            "title": item.get("title"),
            "description": item.get("snippet", ""),
            "publisher": {
                "href": item.get("displayLink"),
                "title": item.get("displayLink")
            },
            "published date": published_date,
            "source_origin": source_type
        }
    else:
        # This is for GNews results
        return {
            "url": item.get("url"),
            "title": item.get("title"),
            "description": item.get("description"),
            "publisher": item.get("publisher", {}),
            "published date": item.get("published date"),
            "source_origin": source_type
        }