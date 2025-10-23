# app/whales/news.py
import aiohttp
from typing import List, Dict
from datetime import datetime, timedelta
from app import settings
from app.whales.normalize import WhaleEvent

class NewsGate:
    """Умный гейт новостей: только релевантные к whale events"""
    
    WHALE_KEYWORDS = [
        "deposit", "withdrawal", "inflow", "outflow", "whale", "large transfer",
        "ETF", "exchange", "binance", "coinbase", "kraken", "okx", "bybit",
        "launch", "listing", "upgrade", "halt", "maintenance", "suspend"
    ]
    
    def __init__(self):
        self.cache: Dict[str, List[Dict]] = {}
        self.cache_ttl = 300  # 5 минут
    
    async def get_relevant_news(self, event: WhaleEvent, session: aiohttp.ClientSession) -> List[Dict]:
        """Возвращает 0-2 новости, релевантные событию"""
        
        cache_key = f"{event.asset}_{int(event.tx_time_utc.timestamp())}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        relevant_news = []
        
        if settings.CRYPTOPANIC_KEY:
            cp_news = await self._fetch_cryptopanic(event, session)
            relevant_news.extend(cp_news)
        
        if settings.NEWS_API_KEY and len(relevant_news) < 2:
            na_news = await self._fetch_newsapi(event, session)
            relevant_news.extend(na_news)
        
        filtered = self._filter_relevant(event, relevant_news)
        result = filtered[:2]
        
        self.cache[cache_key] = result
        return result
    
    async def _fetch_cryptopanic(self, event: WhaleEvent, session: aiohttp.ClientSession) -> List[Dict]:
        """Получает новости из CryptoPanic API"""
        try:
            url = "https://cryptopanic.com/api/v1/posts/"
            params = {
                "auth_token": settings.CRYPTOPANIC_KEY,
                "currencies": event.asset,
                "filter": "hot",
                "public": "true"
            }
            
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status != 200:
                    return []
                
                data = await resp.json()
                posts = data.get("results", [])
                
                news_list = []
                window_start = event.tx_time_utc - timedelta(hours=6)
                window_end = event.tx_time_utc + timedelta(hours=6)
                
                for post in posts[:10]:
                    published = datetime.fromisoformat(post.get("published_at", "").replace("Z", "+00:00"))
                    
                    if not (window_start <= published <= window_end):
                        continue
                    
                    news_list.append({
                        "title": post.get("title", ""),
                        "url": post.get("url", ""),
                        "published_at": published,
                        "source": post.get("source", {}).get("title", "CryptoPanic")
                    })
                
                return news_list
                
        except Exception as e:
            print(f"⚠️  [NEWS] CryptoPanic ошибка: {e}")
            return []
    
    async def _fetch_newsapi(self, event: WhaleEvent, session: aiohttp.ClientSession) -> List[Dict]:
        """Получает новости из NewsAPI"""
        try:
            url = "https://newsapi.org/v2/everything"
            query = f"{event.asset} AND (crypto OR cryptocurrency)"
            
            params = {
                "apiKey": settings.NEWS_API_KEY,
                "q": query,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 10
            }
            
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status != 200:
                    return []
                
                data = await resp.json()
                articles = data.get("articles", [])
                
                news_list = []
                window_start = event.tx_time_utc - timedelta(hours=6)
                window_end = event.tx_time_utc + timedelta(hours=6)
                
                for article in articles:
                    published = datetime.fromisoformat(article.get("publishedAt", "").replace("Z", "+00:00"))
                    
                    if not (window_start <= published <= window_end):
                        continue
                    
                    news_list.append({
                        "title": article.get("title", ""),
                        "url": article.get("url", ""),
                        "published_at": published,
                        "source": article.get("source", {}).get("name", "NewsAPI")
                    })
                
                return news_list
                
        except Exception as e:
            print(f"⚠️  [NEWS] NewsAPI ошибка: {e}")
            return []
    
    def _filter_relevant(self, event: WhaleEvent, news_list: List[Dict]) -> List[Dict]:
        """Фильтрует новости по релевантности"""
        relevant = []
        
        entities = set()
        for label_list in event.labels.values():
            for label in label_list:
                if label.details:
                    entity = label.details.split()[0].lower()
                    entities.add(entity)
        
        for news in news_list:
            title_lower = news["title"].lower()
            
            has_keyword = any(kw.lower() in title_lower for kw in self.WHALE_KEYWORDS)
            has_asset = event.asset.lower() in title_lower
            
            if has_keyword and has_asset:
                relevant.append(news)
                continue
            
            has_entity = any(entity in title_lower for entity in entities)
            if has_entity:
                relevant.append(news)
        
        return relevant