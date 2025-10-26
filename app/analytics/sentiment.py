# app/analytics/sentiment.py
"""
SENTIMENT ANALYSIS MODULE

Анализ настроения криптосообщества по различным источникам:
- Twitter/X posts
- Reddit discussions
- News headlines
- Telegram channels

Использует:
- VADER для быстрого анализа
- ML модели для глубокого анализа
- Агрегация по временным окнам
"""

import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False
    print("⚠️  VADER not available. Install: pip install vaderSentiment")


class SentimentAnalyzer:
    """
    Анализатор настроения криптосообщества
    
    Определяет sentiment score (-1 до +1) для:
    - Конкретных токенов
    - Общего рынка
    - Трендов
    """
    
    def __init__(self):
        self.vader = SentimentIntensityAnalyzer() if VADER_AVAILABLE else None
        
        # Crypto-specific keywords для улучшения точности
        self.bullish_keywords = [
            'moon', 'bullish', 'pump', 'rocket', 'gem', 'breakout',
            'ath', 'surge', 'rally', 'bull run', 'accumulate', 'buy',
            'undervalued', 'potential', 'promising', 'strong', 'growth'
        ]
        
        self.bearish_keywords = [
            'dump', 'bearish', 'crash', 'scam', 'rug', 'dead', 'rip',
            'sell', 'exit', 'overvalued', 'bubble', 'weak', 'decline',
            'fear', 'panic', 'bear market', 'capitulation'
        ]
        
        # Emoji sentiment
        self.positive_emojis = ['🚀', '🌙', '💎', '🔥', '💪', '📈', '✅', '🎉', '💰', '🤑']
        self.negative_emojis = ['💩', '📉', '❌', '⚠️', '🔻', '😭', '🤡', '💀', '🚫']
        
        # История для агрегации
        self.sentiment_history: Dict[str, List[Dict]] = defaultdict(list)
    
    # ========================================================================
    # MAIN ANALYSIS
    # ========================================================================
    
    def analyze_text(self, text: str, asset: Optional[str] = None) -> Dict:
        """
        Анализирует текст и возвращает sentiment
        
        Args:
            text: Текст для анализа
            asset: Название актива (BTC, ETH, etc) для контекстного анализа
        
        Returns:
            {
                "sentiment": float (-1 to +1),
                "label": str (bullish/bearish/neutral),
                "confidence": float (0 to 1),
                "keywords": List[str],
                "emojis": List[str]
            }
        """
        
        if not text:
            return self._empty_sentiment()
        
        # Очищаем текст
        cleaned_text = self._clean_text(text)
        
        # VADER анализ (базовый)
        vader_sentiment = self._analyze_vader(cleaned_text) if self.vader else 0.0
        
        # Crypto keywords анализ
        keyword_sentiment = self._analyze_keywords(cleaned_text)
        
        # Emoji анализ
        emoji_sentiment = self._analyze_emojis(text)
        
        # Комбинируем (weighted average)
        combined_sentiment = (
            vader_sentiment * 0.50 +
            keyword_sentiment * 0.35 +
            emoji_sentiment * 0.15
        )
        
        # Определяем label
        if combined_sentiment > 0.15:
            label = "bullish"
        elif combined_sentiment < -0.15:
            label = "bearish"
        else:
            label = "neutral"
        
        # Confidence (насколько сильный сигнал)
        confidence = min(1.0, abs(combined_sentiment))
        
        # Находим ключевые слова
        keywords = self._extract_keywords(cleaned_text)
        emojis = self._extract_emojis(text)
        
        result = {
            "sentiment": combined_sentiment,
            "label": label,
            "confidence": confidence,
            "keywords": keywords,
            "emojis": emojis,
            "vader_score": vader_sentiment,
            "keyword_score": keyword_sentiment,
            "emoji_score": emoji_sentiment
        }
        
        # Сохраняем в историю
        if asset:
            self.sentiment_history[asset].append({
                "timestamp": datetime.utcnow(),
                "sentiment": combined_sentiment,
                "text": text[:100]  # Первые 100 символов
            })
            
            # Ограничиваем размер истории
            if len(self.sentiment_history[asset]) > 1000:
                self.sentiment_history[asset] = self.sentiment_history[asset][-1000:]
        
        return result
    
    def analyze_batch(self, texts: List[str], asset: Optional[str] = None) -> Dict:
        """
        Анализирует несколько текстов и агрегирует результат
        
        Args:
            texts: Список текстов
            asset: Актив
        
        Returns:
            {
                "average_sentiment": float,
                "label": str,
                "confidence": float,
                "total_texts": int,
                "bullish_count": int,
                "bearish_count": int,
                "neutral_count": int
            }
        """
        
        if not texts:
            return self._empty_sentiment()
        
        results = [self.analyze_text(text, asset) for text in texts]
        
        sentiments = [r["sentiment"] for r in results]
        labels = [r["label"] for r in results]
        
        # Агрегация
        avg_sentiment = statistics.mean(sentiments)
        
        label_counts = Counter(labels)
        
        # Определяем общий label (большинство голосов)
        majority_label = label_counts.most_common(1)[0][0]
        
        # Confidence = согласованность (чем больше одинаковых labels - тем выше)
        confidence = label_counts[majority_label] / len(texts)
        
        return {
            "average_sentiment": avg_sentiment,
            "label": majority_label,
            "confidence": confidence,
            "total_texts": len(texts),
            "bullish_count": label_counts.get("bullish", 0),
            "bearish_count": label_counts.get("bearish", 0),
            "neutral_count": label_counts.get("neutral", 0),
            "sentiment_distribution": {
                "positive": sum(1 for s in sentiments if s > 0.15) / len(sentiments),
                "negative": sum(1 for s in sentiments if s < -0.15) / len(sentiments),
                "neutral": sum(1 for s in sentiments if -0.15 <= s <= 0.15) / len(sentiments)
            }
        }
    
    # ========================================================================
    # AGGREGATED ANALYSIS
    # ========================================================================
    
    def get_asset_sentiment(self, asset: str, hours: int = 24) -> Dict:
        """
        Получает агрегированный sentiment актива за период
        
        Args:
            asset: Название актива (BTC, ETH, etc)
            hours: За сколько часов
        
        Returns:
            {
                "sentiment": float,
                "label": str,
                "confidence": float,
                "sample_size": int,
                "trend": str (improving/declining/stable)
            }
        """
        
        if asset not in self.sentiment_history:
            return self._empty_sentiment()
        
        # Фильтруем по времени
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent = [
            entry for entry in self.sentiment_history[asset]
            if entry["timestamp"] >= cutoff
        ]
        
        if not recent:
            return self._empty_sentiment()
        
        # Средний sentiment
        sentiments = [entry["sentiment"] for entry in recent]
        avg_sentiment = statistics.mean(sentiments)
        
        # Label
        if avg_sentiment > 0.15:
            label = "bullish"
        elif avg_sentiment < -0.15:
            label = "bearish"
        else:
            label = "neutral"
        
        # Confidence (стабильность)
        stdev = statistics.stdev(sentiments) if len(sentiments) > 1 else 0
        confidence = 1.0 - min(1.0, stdev)
        
        # Trend (сравниваем первую и вторую половину периода)
        mid = len(recent) // 2
        if mid > 0:
            first_half = statistics.mean([e["sentiment"] for e in recent[:mid]])
            second_half = statistics.mean([e["sentiment"] for e in recent[mid:]])
            
            delta = second_half - first_half
            
            if delta > 0.10:
                trend = "improving"
            elif delta < -0.10:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "unknown"
        
        return {
            "asset": asset,
            "sentiment": avg_sentiment,
            "label": label,
            "confidence": confidence,
            "sample_size": len(recent),
            "trend": trend,
            "period_hours": hours
        }
    
    def compare_assets_sentiment(self, assets: List[str], hours: int = 24) -> Dict:
        """
        Сравнивает sentiment нескольких активов
        
        Returns:
            {
                "most_bullish": str,
                "most_bearish": str,
                "sentiments": Dict[str, float]
            }
        """
        
        sentiments = {}
        
        for asset in assets:
            result = self.get_asset_sentiment(asset, hours)
            sentiments[asset] = result["sentiment"]
        
        if not sentiments:
            return {"most_bullish": None, "most_bearish": None, "sentiments": {}}
        
        most_bullish = max(sentiments, key=sentiments.get)
        most_bearish = min(sentiments, key=sentiments.get)
        
        return {
            "most_bullish": most_bullish,
            "most_bearish": most_bearish,
            "sentiments": sentiments
        }
    
    # ========================================================================
    # ANALYSIS HELPERS
    # ========================================================================
    
    def _analyze_vader(self, text: str) -> float:
        """VADER sentiment analysis"""
        if not self.vader:
            return 0.0
        
        scores = self.vader.polarity_scores(text)
        return scores["compound"]
    
    def _analyze_keywords(self, text: str) -> float:
        """Анализ crypto-specific keywords"""
        text_lower = text.lower()
        
        bullish_count = sum(1 for kw in self.bullish_keywords if kw in text_lower)
        bearish_count = sum(1 for kw in self.bearish_keywords if kw in text_lower)
        
        total = bullish_count + bearish_count
        
        if total == 0:
            return 0.0
        
        return (bullish_count - bearish_count) / total
    
    def _analyze_emojis(self, text: str) -> float:
        """Анализ emoji sentiment"""
        positive_count = sum(1 for emoji in self.positive_emojis if emoji in text)
        negative_count = sum(1 for emoji in self.negative_emojis if emoji in text)
        
        total = positive_count + negative_count
        
        if total == 0:
            return 0.0
        
        return (positive_count - negative_count) / total
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Извлекает найденные keywords"""
        text_lower = text.lower()
        found = []
        
        for kw in self.bullish_keywords + self.bearish_keywords:
            if kw in text_lower:
                found.append(kw)
        
        return found[:5]  # Топ-5
    
    def _extract_emojis(self, text: str) -> List[str]:
        """Извлекает emojis"""
        found = []
        
        for emoji in self.positive_emojis + self.negative_emojis:
            if emoji in text:
                found.append(emoji)
        
        return found
    
    def _clean_text(self, text: str) -> str:
        """Очищает текст"""
        # Убираем URLs
        text = re.sub(r'http\S+', '', text)
        # Убираем mentions
        text = re.sub(r'@\w+', '', text)
        # Убираем hashtags (но оставляем текст)
        text = re.sub(r'#', '', text)
        
        return text.strip()
    
    def _empty_sentiment(self) -> Dict:
        """Пустой результат"""
        return {
            "sentiment": 0.0,
            "label": "neutral",
            "confidence": 0.0,
            "keywords": [],
            "emojis": []
        }


# ============================================================================
# SOCIAL MEDIA SCRAPERS (заглушки - требуют API keys)
# ============================================================================

class TwitterSentiment:
    """
    Twitter/X sentiment scraper
    
    Требует Twitter API ключи
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    async def get_tweets(self, query: str, count: int = 100) -> List[str]:
        """
        Получает tweets по запросу
        
        Args:
            query: Поисковый запрос (например "#Bitcoin")
            count: Количество твитов
        
        Returns:
            Список текстов твитов
        """
        # TODO: Реализовать через Twitter API v2
        # Пока заглушка
        return []


class RedditSentiment:
    """
    Reddit sentiment scraper
    
    Использует Reddit API или PRAW
    """
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
    
    async def get_posts(self, subreddit: str, count: int = 100) -> List[str]:
        """
        Получает посты из subreddit
        
        Args:
            subreddit: Название (например "CryptoCurrency")
            count: Количество постов
        
        Returns:
            Список текстов постов
        """
        # TODO: Реализовать через PRAW
        # Пока заглушка
        return []


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def analyze_sentiment(text: str) -> Dict:
    """
    Quick sentiment analysis
    
    Usage:
        from app.analytics.sentiment import analyze_sentiment
        
        result = analyze_sentiment("Bitcoin going to the moon! 🚀")
        print(result["label"])  # "bullish"
    """
    analyzer = SentimentAnalyzer()
    return analyzer.analyze_text(text)


def analyze_batch_sentiment(texts: List[str]) -> Dict:
    """
    Batch sentiment analysis
    
    Usage:
        texts = ["BTC pump!", "ETH dump", "Hold strong"]
        result = analyze_batch_sentiment(texts)
        print(result["label"])  # "bullish" or "bearish"
    """
    analyzer = SentimentAnalyzer()
    return analyzer.analyze_batch(texts)


# ============================================================================
# CLI TESTING
# ============================================================================

if __name__ == "__main__":
    print("🧪 TESTING SENTIMENT ANALYZER\n")
    
    analyzer = SentimentAnalyzer()
    
    # Тестовые тексты
    test_cases = [
        "Bitcoin going to the moon! 🚀🚀🚀 Buy now!",
        "ETH is dumping hard. Sell everything! 📉",
        "Just bought some BTC. HODL strong 💎",
        "This is a scam! Exit now before you lose money 💩",
        "Neutral observation about the market today.",
        "BTC broke resistance! Bullish breakout incoming! 🔥",
        "Bear market is here. Time to accumulate? 🤔"
    ]
    
    print("=" * 80)
    print("INDIVIDUAL ANALYSIS")
    print("=" * 80)
    
    for i, text in enumerate(test_cases, 1):
        result = analyzer.analyze_text(text)
        
        emoji = {"bullish": "📈", "bearish": "📉", "neutral": "➡️"}[result["label"]]
        
        print(f"\n{i}. {text}")
        print(f"   {emoji} {result['label'].upper()} (sentiment: {result['sentiment']:+.2f}, confidence: {result['confidence']:.2f})")
        if result["keywords"]:
            print(f"   Keywords: {', '.join(result['keywords'])}")
    
    print("\n" + "=" * 80)
    print("BATCH ANALYSIS")
    print("=" * 80)
    
    batch_result = analyzer.analyze_batch(test_cases, "BTC")
    
    print(f"\nOverall: {batch_result['label'].upper()}")
    print(f"Average sentiment: {batch_result['average_sentiment']:+.2f}")
    print(f"Confidence: {batch_result['confidence']:.2f}")
    print(f"Bullish: {batch_result['bullish_count']}, Bearish: {batch_result['bearish_count']}, Neutral: {batch_result['neutral_count']}")
    
    print("\n✅ Testing complete!")