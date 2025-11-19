"""
Whale monitoring features module
Настройки мониторинга крупных транзакций
"""

import logging
from typing import Dict, Any, List
from .base import BaseFeatureConfig

logger = logging.getLogger(__name__)


class WhaleFeatures(BaseFeatureConfig):
    """
    Конфигурация мониторинга whale транзакций
    
    Управляет:
    - Порогами обнаружения
    - Категориями whale активности
    - Фильтрацией событий
    - Приоритизацией уведомлений
    """
    
    def __init__(self):
        """Инициализация конфигурации whale мониторинга"""
        
        # Основные настройки
        self.enabled = self.get_bool_env('WHALE_ENABLED', True)
        
        # Пороги в USD
        self.min_usd_threshold = self.get_float_env('WHALE_MIN_USD_THRESHOLD', 100000)
        self.mega_threshold = self.get_float_env('WHALE_MEGA_THRESHOLD', 1000000)
        self.ultra_threshold = self.get_float_env('WHALE_ULTRA_THRESHOLD', 10000000)
        self.legendary_threshold = self.get_float_env('WHALE_LEGENDARY_THRESHOLD', 50000000)
        
        # Категории whale
        self.track_exchanges = self.get_bool_env('WHALE_TRACK_EXCHANGES', True)
        self.track_defi = self.get_bool_env('WHALE_TRACK_DEFI', True)
        self.track_nft = self.get_bool_env('WHALE_TRACK_NFT', False)
        self.track_staking = self.get_bool_env('WHALE_TRACK_STAKING', True)
        self.track_bridge = self.get_bool_env('WHALE_TRACK_BRIDGE', True)
        
        # Фильтрация
        self.filter_dust = self.get_bool_env('WHALE_FILTER_DUST', True)
        self.filter_internal = self.get_bool_env('WHALE_FILTER_INTERNAL', True)
        self.filter_contract_creation = self.get_bool_env('WHALE_FILTER_CONTRACT_CREATION', True)
        self.filter_failed_tx = self.get_bool_env('WHALE_FILTER_FAILED_TX', True)
        
        # Блокчейны
        self.monitored_chains = self._parse_chains()
        self.chain_priorities = self._parse_chain_priorities()
        
        # Лимиты публикаций
        self.posts_per_hour = self.get_int_env('WHALE_POSTS_PER_HOUR', 20)
        self.posts_per_hour_cap = self.posts_per_hour  # Alias для обратной совместимости
        self.max_queue_size = self.get_int_env('WHALE_MAX_QUEUE_SIZE', 100)
        self.dedup_window_seconds = self.get_int_env('WHALE_DEDUP_WINDOW', 300)
        
        # Уверенность и качество
        self.min_confidence = self.get_int_env('MIN_WHALE_CONFIDENCE', 60)
        self.min_confidence_score = self.min_confidence  # Alias для обратной совместимости
        self.require_token_info = self.get_bool_env('WHALE_REQUIRE_TOKEN_INFO', True)
        self.require_price_data = self.get_bool_env('WHALE_REQUIRE_PRICE_DATA', False)
        
        # Интервалы
        self.check_interval = self.get_int_env('WHALE_CHECK_INTERVAL', 60)
        self.refresh_interval = self.get_int_env('WHALE_REFRESH_INTERVAL', 30)
        self.historical_lookback_hours = self.get_int_env('WHALE_HISTORICAL_LOOKBACK_HOURS', 24)
        
        # Обогащение данных
        self.enrich_with_labels = self.get_bool_env('WHALE_ENRICH_LABELS', True)
        self.enrich_with_balance = self.get_bool_env('WHALE_ENRICH_BALANCE', True)
        self.enrich_with_history = self.get_bool_env('WHALE_ENRICH_HISTORY', False)
        self.lookup_ens_names = self.get_bool_env('WHALE_LOOKUP_ENS', True)
        
        # Smart money detection
        self.smart_money_enabled = self.get_bool_env('WHALE_SMART_MONEY_ENABLED', True)
        self.smart_money_min_profit = self.get_float_env('SMART_MONEY_MIN_PROFIT', 20.0)
        self.smart_money_min_trades = self.get_int_env('SMART_MONEY_MIN_TRADES', 10)
        
        # Уведомления
        self.notify_mega_whales = self.get_bool_env('NOTIFY_MEGA_WHALES', True)
        self.notify_smart_money = self.get_bool_env('NOTIFY_SMART_MONEY', True)
        self.notify_suspicious = self.get_bool_env('NOTIFY_SUSPICIOUS', True)
        
        # Логирование
        self._log_configuration()
    
    def _parse_chains(self) -> List[str]:
        """Парсинг отслеживаемых блокчейнов"""
        chains_str = self.get_str_env('WHALE_MONITORED_CHAINS', 
                                      'ethereum,solana,bsc,polygon,arbitrum,base,optimism,avalanche')
        return [chain.strip().lower() for chain in chains_str.split(',')]
    
    def _parse_chain_priorities(self) -> Dict[str, int]:
        """Парсинг приоритетов блокчейнов"""
        default_priorities = {
            'ethereum': 10,
            'solana': 9,
            'bsc': 8,
            'polygon': 7,
            'arbitrum': 7,
            'base': 7,
            'optimism': 6,
            'avalanche': 6
        }
        
        # Можно расширить парсингом из env
        return default_priorities
    
    def _log_configuration(self):
        """Логирование конфигурации"""
        status = "✅ ENABLED" if self.enabled else "❌ DISABLED"
        
        logger.info(f"[WHALE] Status: {status}")
        
        if self.enabled:
            logger.info(f"[WHALE] Thresholds: min=${self.min_usd_threshold:,.0f}, "
                       f"mega=${self.mega_threshold:,.0f}, "
                       f"ultra=${self.ultra_threshold:,.0f}")
            logger.info(f"[WHALE] Monitoring: {len(self.monitored_chains)} chains - "
                       f"{', '.join(self.monitored_chains)}")
            logger.info(f"[WHALE] Limits: {self.posts_per_hour} posts/hour, "
                       f"confidence≥{self.min_confidence}")
            
            categories = []
            if self.track_exchanges:
                categories.append('exchanges')
            if self.track_defi:
                categories.append('DeFi')
            if self.track_nft:
                categories.append('NFT')
            if self.track_staking:
                categories.append('staking')
            if self.track_bridge:
                categories.append('bridges')
            
            logger.info(f"[WHALE] Tracking: {', '.join(categories)}")
    
    def get_threshold_category(self, usd_amount: float) -> str:
        """
        Определение категории whale по сумме
        
        Args:
            usd_amount: Сумма в USD
            
        Returns:
            str: Категория ('normal', 'mega', 'ultra', 'legendary')
        """
        if usd_amount >= self.legendary_threshold:
            return 'legendary'
        elif usd_amount >= self.ultra_threshold:
            return 'ultra'
        elif usd_amount >= self.mega_threshold:
            return 'mega'
        elif usd_amount >= self.min_usd_threshold:
            return 'normal'
        else:
            return 'below_threshold'
    
    def is_whale_transaction(self, usd_amount: float) -> bool:
        """
        Проверка является ли транзакция whale
        
        Args:
            usd_amount: Сумма в USD
            
        Returns:
            bool: True если сумма превышает порог
        """
        return usd_amount >= self.min_usd_threshold
    
    def is_chain_monitored(self, chain: str) -> bool:
        """
        Проверка отслеживается ли блокчейн
        
        Args:
            chain: Название блокчейна
            
        Returns:
            bool: True если блокчейн отслеживается
        """
        return chain.lower() in self.monitored_chains
    
    def get_chain_priority(self, chain: str) -> int:
        """
        Получение приоритета блокчейна
        
        Args:
            chain: Название блокчейна
            
        Returns:
            int: Приоритет (выше = важнее)
        """
        return self.chain_priorities.get(chain.lower(), 0)
    
    def should_notify(self, usd_amount: float, is_smart_money: bool = False, 
                     is_suspicious: bool = False) -> bool:
        """
        Определение нужно ли отправлять уведомление
        
        Args:
            usd_amount: Сумма в USD
            is_smart_money: Признак smart money
            is_suspicious: Признак подозрительной активности
            
        Returns:
            bool: True если нужно уведомление
        """
        category = self.get_threshold_category(usd_amount)
        
        if category in ['mega', 'ultra', 'legendary'] and self.notify_mega_whales:
            return True
        
        if is_smart_money and self.notify_smart_money:
            return True
        
        if is_suspicious and self.notify_suspicious:
            return True
        
        return category != 'below_threshold'
    
    def get_enrichment_options(self) -> Dict[str, bool]:
        """
        Получение опций обогащения данных
        
        Returns:
            Dict: Словарь опций обогащения
        """
        return {
            'labels': self.enrich_with_labels,
            'balance': self.enrich_with_balance,
            'history': self.enrich_with_history,
            'ens_names': self.lookup_ens_names
        }
    
    def get_tracking_categories(self) -> Dict[str, bool]:
        """
        Получение отслеживаемых категорий
        
        Returns:
            Dict: Словарь категорий
        """
        return {
            'exchanges': self.track_exchanges,
            'defi': self.track_defi,
            'nft': self.track_nft,
            'staking': self.track_staking,
            'bridge': self.track_bridge
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Конвертация в словарь
        
        Returns:
            Dict: Конфигурация whale мониторинга
        """
        return {
            'enabled': self.enabled,
            'min_usd_threshold': self.min_usd_threshold,
            'mega_threshold': self.mega_threshold,
            'ultra_threshold': self.ultra_threshold,
            'legendary_threshold': self.legendary_threshold,
            'monitored_chains': self.monitored_chains,
            'posts_per_hour': self.posts_per_hour,
            'min_confidence': self.min_confidence,
            'check_interval': self.check_interval,
            'tracking_categories': self.get_tracking_categories(),
            'enrichment_options': self.get_enrichment_options(),
            'smart_money_enabled': self.smart_money_enabled,
            'notifications': {
                'mega_whales': self.notify_mega_whales,
                'smart_money': self.notify_smart_money,
                'suspicious': self.notify_suspicious
            }
        }


__all__ = ['WhaleFeatures']