# app/whales/monitor/core.py
"""
Blockchain Monitor Core
Главный координатор мониторинга всех блокчейнов
"""

import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import aiohttp

from app.config import config
from app.whales.normalize import WhaleEvent
from app.whales.monitor.evm_provider import EVMProvider
from app.whales.monitor.solana_provider import SolanaProvider
from app.whales.monitor.dex_detector import DEXDetector
from app.whales.monitor.components import (
    TransactionCache,
    RateLimiter,
    MonitorStats
)

logger = logging.getLogger(__name__)


class BlockchainMonitor:
    """
    Главный монитор блокчейнов
    Координирует работу провайдеров для всех поддерживаемых сетей
    """
    
    SUPPORTED_CHAINS = {
        'evm': ['ethereum', 'bsc', 'base', 'arbitrum', 'polygon'],
        'solana': ['solana']
    }
    
    def __init__(self):
        """Инициализация монитора"""
        self.session: Optional[aiohttp.ClientSession] = None
        self.tx_cache = TransactionCache(max_size=10000)
        self.rate_limiter = RateLimiter(requests_per_second=10)
        self.dex_detector = DEXDetector()
        self.stats = MonitorStats()
        
        # Провайдеры (инициализируются при старте)
        self.evm_provider: Optional[EVMProvider] = None
        self.solana_provider: Optional[SolanaProvider] = None
        
        self._initialized = False
        
        logger.info("🔧 [MONITOR] Инициализация BlockchainMonitor")
    
    async def __aenter__(self):
        """Вход в async context manager"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Выход из async context manager"""
        await self.close()
    
    async def initialize(self):
        """Инициализация всех компонентов"""
        if self._initialized:
            logger.debug("⚠️ [MONITOR] Уже инициализирован")
            return
        
        try:
            # Создание HTTP сессии
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
            # Инициализация провайдеров
            self.evm_provider = EVMProvider(
                session=self.session,
                rate_limiter=self.rate_limiter,
                tx_cache=self.tx_cache,
                dex_detector=self.dex_detector
            )
            
            self.solana_provider = SolanaProvider(
                session=self.session,
                rate_limiter=self.rate_limiter,
                tx_cache=self.tx_cache
            )
            
            self._initialized = True
            logger.info("✅ [MONITOR] BlockchainMonitor инициализирован")
            logger.info(f"🔗 [MONITOR] Поддерживаемые chains: {self._get_all_chains()}")
        
        except Exception as e:
            logger.error(f"❌ [MONITOR] Ошибка инициализации: {e}", exc_info=True)
            await self.close()
            raise
    
    async def close(self):
        """Закрытие всех ресурсов"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("✅ [MONITOR] Сессия закрыта")
        
        self._initialized = False
    
    async def fetch_events(
        self,
        start_time: datetime,
        chains: Optional[List[str]] = None,
        assets: Optional[List[str]] = None
    ) -> List[WhaleEvent]:
        """
        Получение whale событий из всех указанных блокчейнов
        
        Args:
            start_time: Время начала периода мониторинга
            chains: Список блокчейнов (None = все)
            assets: Список активов для мониторинга (None = все)
            
        Returns:
            Список обнаруженных whale событий
        """
        if not self._initialized:
            logger.error("❌ [MONITOR] Монитор не инициализирован")
            return []
        
        # Определение chains для сканирования
        chains_to_scan = self._resolve_chains(chains)
        
        if not chains_to_scan:
            logger.warning("⚠️ [MONITOR] Нет chains для сканирования")
            return []
        
        logger.info(
            f"🔍 [MONITOR] Начинаю сканирование {len(chains_to_scan)} chains: "
            f"{', '.join(chains_to_scan)}"
        )
        logger.info(f"⏰ [MONITOR] Период: с {start_time} до сейчас")
        
        # Сброс статистики
        self.stats.reset()
        
        # Получение событий из всех chains параллельно
        all_events = await self._fetch_from_all_chains(
            chains_to_scan, 
            start_time, 
            assets
        )
        
        # Дедупликация
        unique_events = self._deduplicate_events(all_events)
        
        # Логирование результатов
        self._log_scan_summary(chains_to_scan, unique_events)
        
        return unique_events
    
    async def _fetch_from_all_chains(
        self,
        chains: List[str],
        start_time: datetime,
        assets: Optional[List[str]]
    ) -> List[WhaleEvent]:
        """
        Параллельное получение событий из всех chains
        
        Args:
            chains: Список блокчейнов
            start_time: Время начала
            assets: Список активов
            
        Returns:
            Объединённый список событий
        """
        # Группировка chains по типу провайдера
        evm_chains = [c for c in chains if c in self.SUPPORTED_CHAINS['evm']]
        solana_chains = [c for c in chains if c in self.SUPPORTED_CHAINS['solana']]
        
        # Создание задач для каждого chain
        tasks = []
        
        for chain in evm_chains:
            task = self._fetch_from_chain(
                provider=self.evm_provider,
                chain=chain,
                start_time=start_time,
                assets=assets
            )
            tasks.append(task)
        
        for chain in solana_chains:
            task = self._fetch_from_chain(
                provider=self.solana_provider,
                chain=chain,
                start_time=start_time,
                assets=assets
            )
            tasks.append(task)
        
        # Выполнение всех задач параллельно
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Объединение результатов
        all_events = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"❌ [MONITOR] Ошибка в chain {i}: {result}")
                self.stats.increment_errors()
                continue
            
            if isinstance(result, list):
                all_events.extend(result)
                self.stats.add_events(len(result))
        
        return all_events
    
    async def _fetch_from_chain(
        self,
        provider,
        chain: str,
        start_time: datetime,
        assets: Optional[List[str]]
    ) -> List[WhaleEvent]:
        """
        Получение событий из одного chain
        
        Args:
            provider: Провайдер (EVM или Solana)
            chain: Название блокчейна
            start_time: Время начала
            assets: Список активов
            
        Returns:
            Список событий из этого chain
        """
        try:
            logger.info(f"🔍 [MONITOR] Сканирую {chain}...")
            
            events = await provider.fetch_events(
                chain=chain,
                start_time=start_time,
                assets=assets
            )
            
            logger.info(f"✅ [MONITOR] {chain}: найдено {len(events)} событий")
            
            return events
        
        except Exception as e:
            logger.error(f"❌ [MONITOR] Ошибка сканирования {chain}: {e}", exc_info=True)
            return []
    
    def _resolve_chains(self, chains: Optional[List[str]]) -> List[str]:
        """
        Определение списка chains для сканирования
        
        Args:
            chains: Запрошенные chains или None
            
        Returns:
            Список валидных chains
        """
        if chains is None:
            # Все поддерживаемые chains
            return self._get_all_chains()
        
        # Валидация запрошенных chains
        valid_chains = []
        all_supported = self._get_all_chains()
        
        for chain in chains:
            if chain in all_supported:
                valid_chains.append(chain)
            else:
                logger.warning(f"⚠️ [MONITOR] Неподдерживаемый chain: {chain}")
        
        return valid_chains
    
    def _get_all_chains(self) -> List[str]:
        """
        Получение списка всех поддерживаемых chains
        
        Returns:
            Список всех chains
        """
        all_chains = []
        for chain_list in self.SUPPORTED_CHAINS.values():
            all_chains.extend(chain_list)
        return all_chains
    
    def _deduplicate_events(self, events: List[WhaleEvent]) -> List[WhaleEvent]:
        """
        Удаление дубликатов событий
        
        Args:
            events: Список событий (может содержать дубликаты)
            
        Returns:
            Уникальные события
        """
        seen_keys = set()
        unique_events = []
        
        for event in events:
            key = event.get_dedup_key()
            
            if key not in seen_keys:
                seen_keys.add(key)
                unique_events.append(event)
        
        if len(events) != len(unique_events):
            logger.info(
                f"🔄 [MONITOR] Дедупликация: {len(events)} → {len(unique_events)} "
                f"(удалено {len(events) - len(unique_events)} дубликатов)"
            )
        
        return unique_events
    
    def _log_scan_summary(self, chains: List[str], events: List[WhaleEvent]):
        """
        Логирование итоговой статистики сканирования
        
        Args:
            chains: Список отсканированных chains
            events: Найденные события
        """
        logger.info("=" * 60)
        logger.info("📊 [MONITOR] ИТОГИ СКАНИРОВАНИЯ")
        logger.info(f"🔗 Chains: {', '.join(chains)}")
        logger.info(f"🎯 Всего уникальных событий: {len(events)}")
        
        # Разбивка по chains
        events_by_chain = {}
        for event in events:
            if event.chain not in events_by_chain:
                events_by_chain[event.chain] = 0
            events_by_chain[event.chain] += 1
        
        for chain, count in sorted(events_by_chain.items()):
            logger.info(f"  • {chain}: {count} событий")
        
        # Разбивка по активам
        events_by_asset = {}
        total_usd = 0
        
        for event in events:
            if event.asset not in events_by_asset:
                events_by_asset[event.asset] = {'count': 0, 'volume': 0}
            
            events_by_asset[event.asset]['count'] += 1
            events_by_asset[event.asset]['volume'] += event.amount_usd
            total_usd += event.amount_usd
        
        if events_by_asset:
            logger.info(f"💰 Общий объём: ${total_usd:,.0f}")
            logger.info("📈 По активам:")
            
            for asset, data in sorted(
                events_by_asset.items(), 
                key=lambda x: x[1]['volume'], 
                reverse=True
            ):
                logger.info(
                    f"  • {asset}: {data['count']} событий, "
                    f"${data['volume']:,.0f}"
                )
        
        # Статистика провайдеров
        stats_summary = self.stats.get_summary()
        logger.info(f"📊 Ошибок: {stats_summary.get('total_errors', 0)}")
        logger.info("=" * 60)
    
    def get_chain_stats(self) -> Dict:
        """
        Получение статистики по chains
        
        Returns:
            Dict со статистикой каждого chain
        """
        stats = {}
        
        if self.evm_provider:
            evm_stats = self.evm_provider.get_stats()
            stats['evm'] = evm_stats
        
        if self.solana_provider:
            solana_stats = self.solana_provider.get_stats()
            stats['solana'] = solana_stats
        
        return stats
    
    def clear_cache(self):
        """Очистка кэша транзакций"""
        self.tx_cache.clear()
        logger.info("🗑️ [MONITOR] Кэш транзакций очищен")