# app/whales/discovery/providers.py
"""
Data providers для получения информации о токенах
"""

import aiohttp
import asyncio
from typing import List, Dict, Optional
from datetime import datetime

from app.whales.discovery.filters import TokenAgeEstimator


class CoinGeckoProvider:
    """Провайдер данных CoinGecko"""
    
    PLATFORM_MAP = {
        'ethereum': 'ethereum',
        'bsc': 'binance-smart-chain',
        'solana': 'solana',
        'base': 'base',
        'arbitrum': 'arbitrum-one',
        'polygon': 'polygon-pos'
    }
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_base = 'https://api.coingecko.com/api/v3'
        self.api_key = api_key
        self.rate_limit_delay = 1.5
        self.last_call_time: Dict[str, datetime] = {}
    
    async def get_top_tokens(
        self,
        chain: str,
        limit: int,
        session: aiohttp.ClientSession
    ) -> List[Dict]:
        """
        Получает топ токены для chain
        
        Args:
            chain: Название blockchain
            limit: Количество токенов
            session: aiohttp сессия
        
        Returns:
            Список данных токенов
        """
        platform_id = self.PLATFORM_MAP.get(chain)
        if not platform_id:
            print(f'⚠️  [COINGECKO] Неизвестный chain: {chain}')
            return []
        
        await self._wait_rate_limit(chain)
        
        try:
            url = f'{self.api_base}/coins/markets'
            params = self._build_request_params(limit)
            headers = self._build_request_headers()
            
            async with session.get(
                url,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 429:
                    print(f'⚠️  [COINGECKO] Rate limit для {chain}, жду 60с...')
                    await asyncio.sleep(60)
                    return []
                
                if response.status != 200:
                    print(f'⚠️  [COINGECKO] Статус {response.status} для {chain}')
                    return []
                
                data = await response.json()
            
            tokens = self._parse_tokens_response(data, chain, platform_id)
            print(f'✅ [COINGECKO] {chain}: получено {len(tokens)} токенов')
            return tokens
        
        except asyncio.TimeoutError:
            print(f'⏱️  [COINGECKO] Timeout для {chain}')
            return []
        
        except Exception as e:
            print(f'❌ [COINGECKO] Ошибка для {chain}: {e}')
            return []
    
    def _build_request_params(self, limit: int) -> Dict:
        """Формирует параметры запроса"""
        params = {
            'vs_currency': 'usd',
            'category': 'cryptocurrency',
            'order': 'volume_desc',
            'per_page': limit,
            'page': 1,
            'sparkline': False,
            'price_change_percentage': '24h',
            'locale': 'en'
        }
        
        if self.api_key:
            params['x_cg_pro_api_key'] = self.api_key
        
        return params
    
    def _build_request_headers(self) -> Dict:
        """Формирует заголовки запроса"""
        return {
            'Accept': 'application/json',
            'User-Agent': 'CryptoCompass/3.0'
        }
    
    def _parse_tokens_response(
        self,
        data: List[Dict],
        chain: str,
        platform_id: str
    ) -> List[Dict]:
        """Парсит ответ API и формирует список токенов"""
        tokens = []
        
        for coin in data:
            platforms = coin.get('platforms', {})
            
            if platforms and platform_id not in platforms:
                continue
            
            token_data = {
                'symbol': coin.get('symbol', '').upper(),
                'name': coin.get('name', ''),
                'market_cap': coin.get('market_cap', 0),
                'volume_24h': coin.get('total_volume', 0),
                'price': coin.get('current_price', 0),
                'price_change_24h': coin.get('price_change_percentage_24h', 0),
                'age_days': TokenAgeEstimator.estimate_age(coin),
                'chain': chain
            }
            
            tokens.append(token_data)
        
        return tokens
    
    async def _wait_rate_limit(self, key: str):
        """Rate limiting для запросов"""
        if key in self.last_call_time:
            elapsed = (datetime.utcnow() - self.last_call_time[key]).total_seconds()
            
            if elapsed < self.rate_limit_delay:
                wait_time = self.rate_limit_delay - elapsed
                await asyncio.sleep(wait_time)
        
        self.last_call_time[key] = datetime.utcnow()