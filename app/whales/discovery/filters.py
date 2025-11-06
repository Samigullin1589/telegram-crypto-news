# app/whales/discovery/filters.py
"""
Quality filters для токенов
"""

from typing import Dict
from datetime import datetime


class TokenQualityFilter:
    """Фильтры качества токенов"""
    
    def __init__(
        self,
        min_age_days: int = 30,
        min_volume_usd: float = 100_000,
        min_market_cap_usd: float = 1_000_000,
        max_price_change_percent: float = 200
    ):
        self.min_age_days = min_age_days
        self.min_volume_usd = min_volume_usd
        self.min_market_cap_usd = min_market_cap_usd
        self.max_price_change_percent = max_price_change_percent
    
    def passes_all_filters(self, token_data: Dict) -> bool:
        """Проверяет все фильтры качества"""
        return (
            self._check_age(token_data) and
            self._check_volume(token_data) and
            self._check_market_cap(token_data) and
            self._check_price_stability(token_data)
        )
    
    def _check_age(self, token_data: Dict) -> bool:
        """Проверка возраста токена"""
        age_days = token_data.get('age_days', 0)
        return age_days >= self.min_age_days
    
    def _check_volume(self, token_data: Dict) -> bool:
        """Проверка объема торговли"""
        volume_24h = token_data.get('volume_24h', 0)
        return volume_24h >= self.min_volume_usd
    
    def _check_market_cap(self, token_data: Dict) -> bool:
        """Проверка капитализации"""
        market_cap = token_data.get('market_cap', 0)
        return market_cap >= self.min_market_cap_usd
    
    def _check_price_stability(self, token_data: Dict) -> bool:
        """Проверка стабильности цены"""
        price_change = abs(token_data.get('price_change_24h', 0))
        return price_change <= self.max_price_change_percent


class TokenAgeEstimator:
    """Оценка возраста токена"""
    
    @staticmethod
    def estimate_age(coin_data: Dict) -> int:
        """
        Оценивает возраст токена на основе данных CoinGecko
        
        Returns:
            Возраст в днях (приблизительный)
        """
        age = TokenAgeEstimator._estimate_from_ath_date(coin_data)
        if age > 0:
            return age
        
        age = TokenAgeEstimator._estimate_from_market_cap_rank(coin_data)
        if age > 0:
            return age
        
        return 30
    
    @staticmethod
    def _estimate_from_ath_date(coin_data: Dict) -> int:
        """Оценка по дате all-time high"""
        ath_date_str = coin_data.get('ath_date')
        if not ath_date_str:
            return 0
        
        try:
            ath_date = datetime.fromisoformat(ath_date_str.replace('Z', '+00:00'))
            days_since_ath = (datetime.utcnow() - ath_date).days
            return days_since_ath + 30
        except (ValueError, AttributeError):
            return 0
    
    @staticmethod
    def _estimate_from_market_cap_rank(coin_data: Dict) -> int:
        """Оценка по рангу капитализации"""
        rank = coin_data.get('market_cap_rank', 9999)
        
        if rank < 100:
            return 365
        elif rank < 500:
            return 180
        elif rank < 2000:
            return 90
        else:
            return 0