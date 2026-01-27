import logging
from typing import List, Dict
from gnews import GNews

logger = logging.getLogger(__name__)

class NewsSearcher:
    """
    Fetches articles using the GNews library (Google News RSS).
    """

    def __init__(self, topic: str):
        self.topic = topic
        # Initialize GNews: English language, US country (configurable)
        self.google_news = GNews(language='en', country='US', max_results=5)

    def search(self) -> List[Dict]:
        """
        Returns a list of dictionaries with keys: title, published date, url, publisher, etc.
        """
        try:
            logger.info(f"📰 Searching Google News for: {self.topic}")
            news_results = self.google_news.get_news(self.topic)
            
            logger.info(f"✅ Found {len(news_results)} news articles.")
            return news_results
        except Exception as e:
            logger.error(f"❌ GNews Search Failed: {e}")
            return []