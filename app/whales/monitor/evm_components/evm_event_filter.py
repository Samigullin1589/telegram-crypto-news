# app/whales/monitor/evm_components/evm_event_filter.py
"""
EVM Event Filter v2.0
Интеллектуальная фильтрация whale событий с учётом chain-specific порогов
"""

import logging
from typing import Optional, Dict, Set

from app.config import config
from app.whales.normalize import WhaleEvent

logger = logging.getLogger(__name__)


class EVMEventFilter:
    """
    Главный фильтр whale событий для EVM chains
    Использует chain-specific пороги и множественные критерии фильтрации
    """
    
    def __init__(self):
        """Инициализация фильтра с загрузкой конфигурации"""
        self.base_threshold = getattr(config.whale, 'min_usd_threshold', 10000)
        self.chain_thresholds = getattr(config.whale, 'chain_thresholds', {})
        
        # Инициализация подфильтров
        self.amount_filter = AmountFilter(self.base_threshold, self.chain_thresholds)
        self.type_filter = TypeFilter()
        self.address_filter = AddressFilter()
        
        # Статистика фильтрации
        self.stats = {
            'total_checked': 0,
            'passed': 0,
            'filtered_by_amount': 0,
            'filtered_by_type': 0,
            'filtered_by_address': 0
        }
        
        logger.info("🔧 [FILTER] EVMEventFilter инициализирован")
        logger.info(f"💰 [FILTER] Базовый порог: ${self.base_threshold:,.0f}")
        
        if self.chain_thresholds:
            logger.info("💰 [FILTER] Chain-specific пороги:")
            for chain, threshold in self.chain_thresholds.items():
                logger.info(f"  • {chain}: ${threshold:,.0f}")
    
    def should_process(self, event: WhaleEvent) -> bool:
        """
        Комплексная проверка необходимости обработки события
        
        Args:
            event: Whale событие для проверки
            
        Returns:
            True если событие должно быть обработано
        """
        self.stats['total_checked'] += 1
        
        # Фильтр 1: Проверка суммы с учётом chain-specific порога
        if not self.amount_filter.check(event):
            self.stats['filtered_by_amount'] += 1
            return False
        
        # Фильтр 2: Проверка типа события
        if not self.type_filter.check(event):
            self.stats['filtered_by_type'] += 1
            return False
        
        # Фильтр 3: Проверка адресов
        if not self.address_filter.check(event):
            self.stats['filtered_by_address'] += 1
            return False
        
        # Все проверки пройдены
        self.stats['passed'] += 1
        
        logger.info(
            f"✅ [FILTER] Событие ПРОШЛО фильтр: {event.chain} {event.asset} "
            f"${event.amount_usd:,.0f} (порог: ${self.amount_filter.get_threshold(event.chain):,.0f})"
        )
        
        return True
    
    def get_stats(self) -> Dict:
        """
        Получение статистики фильтрации
        
        Returns:
            Dict со статистикой
        """
        total = self.stats['total_checked']
        
        if total > 0:
            pass_rate = (self.stats['passed'] / total) * 100
        else:
            pass_rate = 0
        
        return {
            'total_checked': total,
            'passed': self.stats['passed'],
            'pass_rate_percent': round(pass_rate, 2),
            'filtered_by_amount': self.stats['filtered_by_amount'],
            'filtered_by_type': self.stats['filtered_by_type'],
            'filtered_by_address': self.stats['filtered_by_address']
        }
    
    def reset_stats(self):
        """Сброс статистики"""
        self.stats = {
            'total_checked': 0,
            'passed': 0,
            'filtered_by_amount': 0,
            'filtered_by_type': 0,
            'filtered_by_address': 0
        }
    
    def log_stats(self):
        """Вывод статистики в лог"""
        stats = self.get_stats()
        
        logger.info("📊 [FILTER] Статистика фильтрации:")
        logger.info(f"  • Проверено: {stats['total_checked']}")
        logger.info(f"  • Прошло: {stats['passed']} ({stats['pass_rate_percent']}%)")
        logger.info(f"  • Отфильтровано по сумме: {stats['filtered_by_amount']}")
        logger.info(f"  • Отфильтровано по типу: {stats['filtered_by_type']}")
        logger.info(f"  • Отфильтровано по адресу: {stats['filtered_by_address']}")


class AmountFilter:
    """
    Фильтр по сумме транзакции
    Использует chain-specific пороги
    """
    
    def __init__(self, base_threshold: float, chain_thresholds: Dict[str, float]):
        """
        Args:
            base_threshold: Базовый порог в USD
            chain_thresholds: Chain-specific пороги
        """
        self.base_threshold = base_threshold
        self.chain_thresholds = chain_thresholds
    
    def get_threshold(self, chain: str) -> float:
        """
        Получение порога для конкретного chain
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Порог в USD
        """
        # Попытка получить chain-specific порог
        threshold = self.chain_thresholds.get(chain)
        
        if threshold is not None:
            return threshold
        
        # Fallback на базовый порог
        return self.base_threshold
    
    def check(self, event: WhaleEvent) -> bool:
        """
        Проверка суммы события
        
        Args:
            event: Whale событие
            
        Returns:
            True если сумма >= порога
        """
        threshold = self.get_threshold(event.chain)
        
        if event.amount_usd < threshold:
            logger.debug(
                f"🚫 [AMOUNT FILTER] {event.chain} {event.asset}: "
                f"${event.amount_usd:,.0f} < ${threshold:,.0f}"
            )
            return False
        
        return True


class TypeFilter:
    """
    Фильтр по типу события
    Отсекает внутренние, bridge и reorg события
    """
    
    def check(self, event: WhaleEvent) -> bool:
        """
        Проверка типа события
        
        Args:
            event: Whale событие
            
        Returns:
            True если тип события валидный
        """
        # Фильтр внутренних переводов
        if event.is_internal:
            logger.debug(
                f"🚫 [TYPE FILTER] {event.chain} {event.asset}: "
                f"internal transfer"
            )
            return False
        
        # Фильтр bridge переводов
        if event.is_bridge:
            logger.debug(
                f"🚫 [TYPE FILTER] {event.chain} {event.asset}: "
                f"bridge transfer"
            )
            return False
        
        # Фильтр reorg событий
        if event.is_reorg:
            logger.debug(
                f"🚫 [TYPE FILTER] {event.chain} {event.asset}: "
                f"reorg event"
            )
            return False
        
        return True


class AddressFilter:
    """
    Фильтр по адресам
    Отсекает события с некорректными или неизвестными адресами
    """
    
    INVALID_ADDRESSES = {
        '0x0000000000000000000000000000000000000000',
        'unknown',
        '',
        None
    }
    
    def check(self, event: WhaleEvent) -> bool:
        """
        Проверка адресов события
        
        Args:
            event: Whale событие
            
        Returns:
            True если адреса валидны
        """
        # Проверка from_address
        if self._is_invalid_address(event.from_address):
            logger.debug(
                f"🚫 [ADDRESS FILTER] {event.chain} {event.asset}: "
                f"invalid from_address: {event.from_address}"
            )
            return False
        
        # Проверка to_address
        if self._is_invalid_address(event.to_address):
            logger.debug(
                f"🚫 [ADDRESS FILTER] {event.chain} {event.asset}: "
                f"invalid to_address: {event.to_address}"
            )
            return False
        
        # Проверка на самоперевод
        if event.from_address.lower() == event.to_address.lower():
            logger.debug(
                f"🚫 [ADDRESS FILTER] {event.chain} {event.asset}: "
                f"self-transfer"
            )
            return False
        
        return True
    
    def _is_invalid_address(self, address: str) -> bool:
        """
        Проверка адреса на валидность
        
        Args:
            address: Адрес для проверки
            
        Returns:
            True если адрес невалидный
        """
        if address in self.INVALID_ADDRESSES:
            return True
        
        # Проверка на минимальную длину
        if address and len(address) < 10:
            return True
        
        return False


class FilterStats:
    """
    Агрегация статистики фильтрации
    Отдельный класс для расширенной аналитики
    """
    
    def __init__(self):
        """Инициализация счётчиков статистики"""
        self.chain_stats = {}
        self.asset_stats = {}
        self.total_volume_usd = 0
        self.total_events = 0
    
    def add_event(self, event: WhaleEvent):
        """
        Добавление события в статистику
        
        Args:
            event: Whale событие
        """
        # Статистика по chains
        if event.chain not in self.chain_stats:
            self.chain_stats[event.chain] = {
                'count': 0,
                'volume_usd': 0
            }
        
        self.chain_stats[event.chain]['count'] += 1
        self.chain_stats[event.chain]['volume_usd'] += event.amount_usd
        
        # Статистика по активам
        if event.asset not in self.asset_stats:
            self.asset_stats[event.asset] = {
                'count': 0,
                'volume_usd': 0
            }
        
        self.asset_stats[event.asset]['count'] += 1
        self.asset_stats[event.asset]['volume_usd'] += event.amount_usd
        
        # Общая статистика
        self.total_events += 1
        self.total_volume_usd += event.amount_usd
    
    def get_summary(self) -> Dict:
        """
        Получение сводной статистики
        
        Returns:
            Dict со статистикой
        """
        return {
            'total_events': self.total_events,
            'total_volume_usd': self.total_volume_usd,
            'chains': self.chain_stats,
            'assets': self.asset_stats
        }
    
    def reset(self):
        """Сброс всей статистики"""
        self.chain_stats = {}
        self.asset_stats = {}
        self.total_volume_usd = 0
        self.total_events = 0