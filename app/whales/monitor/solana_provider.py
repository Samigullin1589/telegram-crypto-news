# app/whales/monitor/solana_provider.py
"""
Solana Chain Provider v4.0
Главный координатор для работы с Solana блокчейном
Модульная архитектура с полной функциональностью
"""

import logging
from typing import List, Optional
from datetime import datetime

from app.whales.normalize import WhaleEvent
from app.whales.monitor.dex_detector import DEXDetector

from .solana_components import (
    SolanaRPCClient,
    SolanaTransactionParser,
    SolanaPriceProvider,
    SolanaEventFilter,
    SolanaConfig
)

from .solana_components.solana_signature_fetcher import SolanaSignatureFetcher
from .solana_components.solana_transaction_processor import SolanaTransactionProcessor
from .solana_components.solana_spl_monitor import SolanaSPLMonitor
from .solana_components.solana_api_health import SolanaAPIHealth

logger = logging.getLogger(__name__)


class SolanaProvider:
    """
    Главный провайдер для Solana блокчейна
    
    Features:
    - Мониторинг SOL и SPL токен переводов
    - Параллельная обработка транзакций
    - Health monitoring для RPC endpoints
    - Умное кэширование и rate limiting
    - Поддержка множественных токенов
    """
    
    def __init__(
        self,
        session,
        rate_limiter,
        tx_cache,
        dex_detector: DEXDetector = None
    ):
        """
        Args:
            session: aiohttp ClientSession
            rate_limiter: Rate limiter для контроля частоты запросов
            tx_cache: Кэш обработанных транзакций
            dex_detector: Детектор DEX адресов (опционально)
        """
        self.session = session
        self.rate_limiter = rate_limiter
        self.tx_cache = tx_cache
        self.dex_detector = dex_detector or DEXDetector()
        
        self.rpc_client = SolanaRPCClient(session, rate_limiter)
        
        self.price_provider = SolanaPriceProvider(session)
        
        self.transaction_parser = SolanaTransactionParser(
            dex_detector=self.dex_detector,
            price_provider=self.price_provider
        )
        
        self.event_filter = SolanaEventFilter()
        
        self.signature_fetcher = SolanaSignatureFetcher(self.rpc_client)
        
        self.transaction_processor = SolanaTransactionProcessor(
            rpc_client=self.rpc_client,
            transaction_parser=self.transaction_parser,
            event_filter=self.event_filter,
            tx_cache=self.tx_cache
        )
        
        self.spl_monitor = SolanaSPLMonitor(
            signature_fetcher=self.signature_fetcher,
            transaction_parser=self.transaction_parser,
            price_provider=self.price_provider,
            event_filter=self.event_filter
        )
        
        self.health_monitor = SolanaAPIHealth(self.rpc_client)
        
        self.stats = {
            "sol_events": 0,
            "spl_events": 0,
            "total_processed": 0,
            "errors": 0
        }
        
        logger.info("🔧 [SOLANA] Провайдер инициализирован")
        
        self.health_monitor.check_api_key_status()
    
    async def fetch_events(
        self,
        chain: str,
        start_time: datetime,
        assets: Optional[List[str]] = None
    ) -> List[WhaleEvent]:
        """
        Получение whale событий для Solana
        
        Args:
            chain: Название блокчейна (должно быть "solana")
            start_time: Время начала периода мониторинга
            assets: Список активов для мониторинга (опционально)
            
        Returns:
            Список обнаруженных whale событий
        """
        if chain != "solana":
            logger.error(f"❌ [SOLANA] Неподдерживаемый chain: {chain}")
            return []
        
        is_healthy = await self.health_monitor.check_health()
        if not is_healthy:
            logger.warning("⚠️ [SOLANA] RPC недоступен, пропускаем сканирование")
            return []
        
        logger.info(f"🔍 [SOLANA] Начинаю сканирование с {start_time}")
        
        self._reset_stats()
        
        events = []
        
        try:
            sol_events = await self._fetch_sol_transfers(start_time)
            events.extend(sol_events)
            self.stats["sol_events"] = len(sol_events)
            
            spl_events = await self._fetch_spl_transfers(start_time, assets)
            events.extend(spl_events)
            self.stats["spl_events"] = len(spl_events)
            
            self._log_scan_results(events)
        
        except Exception as e:
            logger.error(
                f"❌ [SOLANA] Критическая ошибка при сканировании: {e}",
                exc_info=True
            )
            self.stats["errors"] += 1
        
        return events
    
    async def _fetch_sol_transfers(
        self,
        start_time: datetime
    ) -> List[WhaleEvent]:
        """
        Получение крупных SOL переводов
        
        Args:
            start_time: Время начала периода
            
        Returns:
            Список SOL whale событий
        """
        try:
            signatures = await self.signature_fetcher.get_recent_signatures(
                start_time=start_time,
                limit=100
            )
            
            if not signatures:
                logger.info("👍 [SOLANA] Нет новых SOL подписей")
                return []
            
            logger.info(f"📥 [SOLANA] Получено {len(signatures)} SOL подписей")
            
            events = await self.transaction_processor.process_signatures(signatures)
            
            self.stats["total_processed"] += self.transaction_processor.stats["processed"]
            
            logger.info(f"✅ [SOLANA] Найдено {len(events)} SOL событий")
            
            return events
        
        except Exception as e:
            logger.error(f"❌ [SOLANA] Ошибка получения SOL переводов: {e}")
            self.stats["errors"] += 1
            return []
    
    async def _fetch_spl_transfers(
        self,
        start_time: datetime,
        assets: Optional[List[str]] = None
    ) -> List[WhaleEvent]:
        """
        Получение крупных SPL токен переводов
        
        Args:
            start_time: Время начала периода
            assets: Список токенов для мониторинга
            
        Returns:
            Список SPL whale событий
        """
        try:
            events = await self.spl_monitor.fetch_spl_events(
                start_time=start_time,
                assets=assets
            )
            
            logger.info(f"✅ [SOLANA] Найдено {len(events)} SPL событий")
            
            return events
        
        except Exception as e:
            logger.error(f"❌ [SOLANA] Ошибка получения SPL переводов: {e}")
            self.stats["errors"] += 1
            return []
    
    def _reset_stats(self) -> None:
        """Сброс статистики"""
        self.stats = {
            "sol_events": 0,
            "spl_events": 0,
            "total_processed": 0,
            "errors": 0
        }
        self.transaction_processor.reset_stats()
    
    def _log_scan_results(self, events: List[WhaleEvent]) -> None:
        """
        Логирование результатов сканирования
        
        Args:
            events: Список найденных событий
        """
        processor_stats = self.transaction_processor.get_stats()
        spl_stats = self.spl_monitor.get_stats()
        
        logger.info(
            f"📊 [SOLANA] Результаты сканирования:\n"
            f"  • SOL события: {self.stats['sol_events']}\n"
            f"  • SPL события: {self.stats['spl_events']}\n"
            f"  • Обработано транзакций: {processor_stats['processed']}\n"
            f"  • Кэш hits: {processor_stats['cached_hits']}\n"
            f"  • SPL токенов проверено: {spl_stats['tokens_checked']}\n"
            f"  • Всего событий: {len(events)}\n"
            f"  • Ошибок: {self.stats['errors']}"
        )
    
    def get_stats(self) -> dict:
        """
        Получение статистики провайдера
        
        Returns:
            Dict со статистикой
        """
        return {
            "provider": self.stats.copy(),
            "processor": self.transaction_processor.get_stats(),
            "spl_monitor": self.spl_monitor.get_stats(),
            "health": self.health_monitor.get_status()
        }
    
    async def health_check(self) -> Dict:
        """
        Проверка здоровья провайдера
        
        Returns:
            Статус здоровья
        """
        is_healthy = await self.health_monitor.check_health()
        
        return {
            "is_healthy": is_healthy,
            "details": self.health_monitor.get_status()
        }