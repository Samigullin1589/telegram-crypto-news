# app/whales/monitor/evm_components/price_aggregator.py
"""
Price Aggregator
Агрегация цен из множественных источников с умным выбором
"""

import logging
from typing import List, Optional, Tuple
from statistics import median

logger = logging.getLogger(__name__)


class PriceAggregator:
    """
    Агрегатор цен из нескольких источников
    Использует median для устойчивости к выбросам
    """
    
    def __init__(self, providers: List):
        """
        Args:
            providers: Список провайдеров в порядке приоритета
        """
        self.providers = providers
        self.use_median = True
        self.max_deviation = 0.15  # 15% максимальное отклонение
    
    async def get_price(self, token_symbol: str, chain: str) -> Optional[float]:
        """
        Получение агрегированной цены
        
        Args:
            token_symbol: Символ токена
            chain: Название блокчейна
            
        Returns:
            Агрегированная цена или None
        """
        prices = await self._fetch_all_prices(token_symbol, chain)
        
        if not prices:
            return None
        
        if len(prices) == 1:
            return prices[0]
        
        if self.use_median:
            return self._calculate_median_price(prices)
        
        return self._calculate_average_price(prices)
    
    async def _fetch_all_prices(
        self,
        token_symbol: str,
        chain: str
    ) -> List[float]:
        """
        Получение цен из всех доступных источников
        
        Args:
            token_symbol: Символ токена
            chain: Название блокчейна
            
        Returns:
            Список полученных цен
        """
        prices = []
        
        for provider in self.providers:
            try:
                price = await provider.get_price(token_symbol, chain)
                
                if price is not None and price > 0:
                    prices.append(price)
                    
                    if len(prices) >= 2:
                        break
            
            except Exception as e:
                logger.debug(
                    f"⚠️ [AGGREGATOR] Ошибка в {provider.name}: {e}"
                )
                continue
        
        return prices
    
    def _calculate_median_price(self, prices: List[float]) -> float:
        """
        Расчет median цены (устойчива к выбросам)
        
        Args:
            prices: Список цен
            
        Returns:
            Median цена
        """
        filtered_prices = self._filter_outliers(prices)
        
        if not filtered_prices:
            filtered_prices = prices
        
        result = median(filtered_prices)
        
        logger.debug(
            f"💰 [AGGREGATOR] Median из {len(prices)} источников: ${result:,.2f}"
        )
        
        return result
    
    def _calculate_average_price(self, prices: List[float]) -> float:
        """
        Расчет средней цены
        
        Args:
            prices: Список цен
            
        Returns:
            Средняя цена
        """
        filtered_prices = self._filter_outliers(prices)
        
        if not filtered_prices:
            filtered_prices = prices
        
        result = sum(filtered_prices) / len(filtered_prices)
        
        logger.debug(
            f"💰 [AGGREGATOR] Среднее из {len(prices)} источников: ${result:,.2f}"
        )
        
        return result
    
    def _filter_outliers(self, prices: List[float]) -> List[float]:
        """
        Фильтрация выбросов (цены сильно отличающиеся от медианы)
        
        Args:
            prices: Список цен
            
        Returns:
            Отфильтрованный список
        """
        if len(prices) < 3:
            return prices
        
        med = median(prices)
        
        filtered = [
            p for p in prices
            if abs(p - med) / med <= self.max_deviation
        ]
        
        return filtered if filtered else prices