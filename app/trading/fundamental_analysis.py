"""
FUNDAMENTAL ANALYSIS ENGINE
Фундаментальный анализ криптовалют
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class FundamentalData:
    """Фундаментальные данные актива"""
    asset: str
    timestamp: datetime
    
    # Токеномика
    total_supply: Optional[float] = None
    circulating_supply: Optional[float] = None
    max_supply: Optional[float] = None
    market_cap: Optional[float] = None
    fully_diluted_valuation: Optional[float] = None
    
    # Метрики
    volume_24h: Optional[float] = None
    volume_change_24h: Optional[float] = None
    market_cap_rank: Optional[int] = None
    
    # Цена и изменения
    price: Optional[float] = None
    price_change_24h: Optional[float] = None
    price_change_7d: Optional[float] = None
    price_change_30d: Optional[float] = None
    
    # ATH/ATL
    ath: Optional[float] = None
    ath_date: Optional[datetime] = None
    ath_change_percentage: Optional[float] = None
    atl: Optional[float] = None
    atl_date: Optional[datetime] = None
    atl_change_percentage: Optional[float] = None
    
    # Социальные метрики
    twitter_followers: Optional[int] = None
    reddit_subscribers: Optional[int] = None
    github_commits: Optional[int] = None
    
    # Developer activity (последние 30 дней)
    developer_score: Optional[float] = None
    
    # Community score
    community_score: Optional[float] = None
    
    # Оценка
    fundamental_score: float = 0.0
    rating: str = 'NEUTRAL'  # 'STRONG_BUY', 'BUY', 'NEUTRAL', 'SELL', 'STRONG_SELL'
    
    def to_dict(self) -> dict:
        """Конвертация в словарь"""
        return {
            'asset': self.asset,
            'timestamp': self.timestamp.isoformat(),
            'tokenomics': {
                'total_supply': self.total_supply,
                'circulating_supply': self.circulating_supply,
                'max_supply': self.max_supply,
                'market_cap': self.market_cap,
                'fdv': self.fully_diluted_valuation
            },
            'metrics': {
                'volume_24h': self.volume_24h,
                'volume_change_24h': self.volume_change_24h,
                'market_cap_rank': self.market_cap_rank
            },
            'price': {
                'current': self.price,
                'change_24h': self.price_change_24h,
                'change_7d': self.price_change_7d,
                'change_30d': self.price_change_30d
            },
            'ath_atl': {
                'ath': self.ath,
                'ath_date': self.ath_date.isoformat() if self.ath_date else None,
                'ath_change': self.ath_change_percentage,
                'atl': self.atl,
                'atl_date': self.atl_date.isoformat() if self.atl_date else None,
                'atl_change': self.atl_change_percentage
            },
            'social': {
                'twitter': self.twitter_followers,
                'reddit': self.reddit_subscribers,
                'github_commits': self.github_commits
            },
            'scores': {
                'developer': self.developer_score,
                'community': self.community_score,
                'fundamental': self.fundamental_score
            },
            'rating': self.rating
        }


class FundamentalAnalyzer:
    """
    Фундаментальный анализ криптовалют
    
    Анализирует:
    - Токеномику (supply, market cap, dilution)
    - Метрики развития (GitHub activity, commits)
    - Социальные метрики (Twitter, Reddit)
    - Исторические данные (ATH/ATL)
    - События и новости
    """
    
    def __init__(self, coingecko_api_key: Optional[str] = None):
        self.coingecko_key = coingecko_api_key
        self.cache = {}
        self.cache_ttl = 3600  # 1 час
        
        print("📈 [FUNDAMENTAL] Инициализирован")
    
    async def analyze(self, asset: str, session: aiohttp.ClientSession) -> Optional[FundamentalData]:
        """
        Полный фундаментальный анализ актива
        
        Args:
            asset: Символ актива (BTC, ETH и т.д.)
            session: aiohttp session
        
        Returns:
            FundamentalData или None
        """
        
        # Проверка кэша
        if asset in self.cache:
            cached = self.cache[asset]
            if (datetime.utcnow() - cached['timestamp']).seconds < self.cache_ttl:
                return cached['data']
        
        try:
            # Получаем данные с CoinGecko
            coin_data = await self._fetch_coingecko_data(asset, session)
            
            if not coin_data:
                return None
            
            # Парсим данные
            fundamental = self._parse_coin_data(asset, coin_data)
            
            # Рассчитываем фундаментальный скор
            fundamental.fundamental_score = self._calculate_fundamental_score(fundamental)
            fundamental.rating = self._determine_rating(fundamental.fundamental_score)
            
            # Кэшируем
            self.cache[asset] = {
                'data': fundamental,
                'timestamp': datetime.utcnow()
            }
            
            return fundamental
            
        except Exception as e:
            print(f"❌ [FUNDAMENTAL] Ошибка анализа {asset}: {e}")
            return None
    
    async def _fetch_coingecko_data(self, asset: str, session: aiohttp.ClientSession) -> Optional[Dict]:
        """Получение данных с CoinGecko"""
        
        # Маппинг символов на CoinGecko IDs
        coin_id = self._get_coingecko_id(asset)
        if not coin_id:
            return None
        
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
        params = {
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "true",
            "developer_data": "true",
            "sparkline": "false"
        }
        
        if self.coingecko_key:
            params["x_cg_pro_api_key"] = self.coingecko_key
        
        try:
            async with session.get(url, params=params, timeout=15) as resp:
                if resp.status == 429:
                    print(f"⚠️ [FUNDAMENTAL] CoinGecko rate limit для {asset}")
                    await asyncio.sleep(60)
                    return None
                
                if resp.status != 200:
                    return None
                
                return await resp.json()
                
        except Exception as e:
            print(f"⚠️ [FUNDAMENTAL] CoinGecko ошибка для {asset}: {e}")
            return None
    
    def _parse_coin_data(self, asset: str, data: Dict) -> FundamentalData:
        """Парсинг данных от CoinGecko"""
        
        market_data = data.get('market_data', {})
        community_data = data.get('community_data', {})
        developer_data = data.get('developer_data', {})
        
        # Токеномика
        total_supply = market_data.get('total_supply')
        circulating_supply = market_data.get('circulating_supply')
        max_supply = market_data.get('max_supply')
        market_cap = market_data.get('market_cap', {}).get('usd')
        fdv = market_data.get('fully_diluted_valuation', {}).get('usd')
        
        # Метрики
        volume_24h = market_data.get('total_volume', {}).get('usd')
        market_cap_rank = market_data.get('market_cap_rank')
        
        # Цена
        price = market_data.get('current_price', {}).get('usd')
        price_change_24h = market_data.get('price_change_percentage_24h')
        price_change_7d = market_data.get('price_change_percentage_7d')
        price_change_30d = market_data.get('price_change_percentage_30d')
        
        # ATH/ATL
        ath = market_data.get('ath', {}).get('usd')
        ath_date_str = market_data.get('ath_date', {}).get('usd')
        ath_date = datetime.fromisoformat(ath_date_str.replace('Z', '+00:00')) if ath_date_str else None
        ath_change = market_data.get('ath_change_percentage', {}).get('usd')
        
        atl = market_data.get('atl', {}).get('usd')
        atl_date_str = market_data.get('atl_date', {}).get('usd')
        atl_date = datetime.fromisoformat(atl_date_str.replace('Z', '+00:00')) if atl_date_str else None
        atl_change = market_data.get('atl_change_percentage', {}).get('usd')
        
        # Социальные метрики
        twitter_followers = community_data.get('twitter_followers')
        reddit_subscribers = community_data.get('reddit_subscribers')
        
        # Developer activity
        github_commits = developer_data.get('commit_count_4_weeks')
        
        # Расчет volume change
        volume_change_24h = None
        if volume_24h:
            # Приблизительный расчет (CoinGecko не всегда возвращает это)
            volume_change_24h = market_data.get('volume_change_24h')
        
        return FundamentalData(
            asset=asset,
            timestamp=datetime.utcnow(),
            total_supply=total_supply,
            circulating_supply=circulating_supply,
            max_supply=max_supply,
            market_cap=market_cap,
            fully_diluted_valuation=fdv,
            volume_24h=volume_24h,
            volume_change_24h=volume_change_24h,
            market_cap_rank=market_cap_rank,
            price=price,
            price_change_24h=price_change_24h,
            price_change_7d=price_change_7d,
            price_change_30d=price_change_30d,
            ath=ath,
            ath_date=ath_date,
            ath_change_percentage=ath_change,
            atl=atl,
            atl_date=atl_date,
            atl_change_percentage=atl_change,
            twitter_followers=twitter_followers,
            reddit_subscribers=reddit_subscribers,
            github_commits=github_commits,
            developer_score=self._calculate_developer_score(developer_data),
            community_score=self._calculate_community_score(community_data)
        )
    
    def _calculate_developer_score(self, developer_data: Dict) -> float:
        """Оценка активности разработчиков (0-100)"""
        
        score = 0.0
        
        # GitHub commits за 4 недели
        commits = developer_data.get('commit_count_4_weeks', 0)
        if commits > 0:
            score += min(40, commits / 10)  # До 40 баллов
        
        # Stars на GitHub
        stars = developer_data.get('stars', 0)
        if stars > 0:
            score += min(20, stars / 500)  # До 20 баллов
        
        # Forks
        forks = developer_data.get('forks', 0)
        if forks > 0:
            score += min(20, forks / 200)  # До 20 баллов
        
        # Contributors
        subscribers = developer_data.get('subscribers', 0)
        if subscribers > 0:
            score += min(20, subscribers / 100)  # До 20 баллов
        
        return min(100, score)
    
    def _calculate_community_score(self, community_data: Dict) -> float:
        """Оценка активности сообщества (0-100)"""
        
        score = 0.0
        
        # Twitter
        twitter = community_data.get('twitter_followers', 0)
        if twitter > 0:
            score += min(30, twitter / 50000)  # До 30 баллов
        
        # Reddit
        reddit = community_data.get('reddit_subscribers', 0)
        if reddit > 0:
            score += min(30, reddit / 20000)  # До 30 баллов
        
        # Telegram (если есть)
        telegram = community_data.get('telegram_channel_user_count', 0)
        if telegram > 0:
            score += min(20, telegram / 30000)  # До 20 баллов
        
        # Facebook
        facebook = community_data.get('facebook_likes', 0)
        if facebook > 0:
            score += min(20, facebook / 30000)  # До 20 баллов
        
        return min(100, score)
    
    def _calculate_fundamental_score(self, data: FundamentalData) -> float:
        """
        Комплексная фундаментальная оценка (0-100)
        
        Факторы:
        - Токеномика (30%)
        - Рыночные метрики (25%)
        - Активность разработчиков (25%)
        - Активность сообщества (20%)
        """
        
        score = 0.0
        
        # 1. Токеномика (30 баллов)
        tokenomics_score = 0.0
        
        # Supply inflation
        if data.circulating_supply and data.max_supply:
            supply_ratio = data.circulating_supply / data.max_supply
            if supply_ratio > 0.9:
                tokenomics_score += 10  # Низкая инфляция
            elif supply_ratio > 0.7:
                tokenomics_score += 7
            else:
                tokenomics_score += 4
        elif data.max_supply is None:
            tokenomics_score += 5  # Неограниченный supply - нейтрально
        
        # Market cap vs FDV
        if data.market_cap and data.fully_diluted_valuation:
            mc_fdv_ratio = data.market_cap / data.fully_diluted_valuation
            if mc_fdv_ratio > 0.8:
                tokenomics_score += 10  # Малый unlock
            elif mc_fdv_ratio > 0.5:
                tokenomics_score += 6
            else:
                tokenomics_score += 2
        
        # Market cap rank
        if data.market_cap_rank:
            if data.market_cap_rank <= 10:
                tokenomics_score += 10  # Top 10
            elif data.market_cap_rank <= 50:
                tokenomics_score += 7
            elif data.market_cap_rank <= 100:
                tokenomics_score += 5
            else:
                tokenomics_score += 2
        
        score += min(30, tokenomics_score)
        
        # 2. Рыночные метрики (25 баллов)
        market_score = 0.0
        
        # Volume / Market Cap ratio
        if data.volume_24h and data.market_cap:
            vol_mc_ratio = data.volume_24h / data.market_cap
            if vol_mc_ratio > 0.3:
                market_score += 10  # Высокая ликвидность
            elif vol_mc_ratio > 0.1:
                market_score += 7
            else:
                market_score += 3
        
        # Price momentum
        if data.price_change_7d:
            if data.price_change_7d > 10:
                market_score += 8  # Сильный рост
            elif data.price_change_7d > 0:
                market_score += 5
            elif data.price_change_7d > -10:
                market_score += 3
            else:
                market_score += 1
        
        # Distance from ATH
        if data.ath_change_percentage:
            ath_distance = abs(data.ath_change_percentage)
            if ath_distance < 10:
                market_score += 7  # Близко к ATH
            elif ath_distance < 30:
                market_score += 5
            elif ath_distance < 60:
                market_score += 3
            else:
                market_score += 1  # Далеко от ATH - потенциал роста
        
        score += min(25, market_score)
        
        # 3. Developer activity (25 баллов)
        if data.developer_score:
            score += (data.developer_score / 100) * 25
        
        # 4. Community activity (20 баллов)
        if data.community_score:
            score += (data.community_score / 100) * 20
        
        return min(100, score)
    
    def _determine_rating(self, score: float) -> str:
        """Определение рейтинга на основе скора"""
        
        if score >= 80:
            return 'STRONG_BUY'
        elif score >= 65:
            return 'BUY'
        elif score >= 45:
            return 'NEUTRAL'
        elif score >= 30:
            return 'SELL'
        else:
            return 'STRONG_SELL'
    
    def _get_coingecko_id(self, asset: str) -> Optional[str]:
        """Маппинг символов на CoinGecko IDs"""
        mapping = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'SOL': 'solana',
            'BNB': 'binancecoin',
            'XRP': 'ripple',
            'ADA': 'cardano',
            'DOGE': 'dogecoin',
            'MATIC': 'matic-network',
            'DOT': 'polkadot',
            'AVAX': 'avalanche-2',
            'LINK': 'chainlink',
            'UNI': 'uniswap',
            'ATOM': 'cosmos',
            'NEAR': 'near',
            'APT': 'aptos',
            'ARB': 'arbitrum',
            'OP': 'optimism',
            'LTC': 'litecoin',
            'BCH': 'bitcoin-cash',
            'AAVE': 'aave',
            'USDT': 'tether',
            'USDC': 'usd-coin',
            'DAI': 'dai',
            'WBTC': 'wrapped-bitcoin',
            'WETH': 'weth'
        }
        
        return mapping.get(asset.upper())