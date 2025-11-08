# app/whales/monitor/solana_provider.py
"""
Solana Chain Provider v3.0
Модульная архитектура для работы с Solana блокчейном
"""

import asyncio
import logging
from typing import List, Optional
from datetime import datetime, timedelta

from app.config import config
from app.whales.normalize import WhaleEvent
from app.whales.monitor.dex_detector import DEXDetector
from .solana_components import (
    SolanaRPCClient,
    SolanaTransactionParser,
    SolanaPriceProvider,
    SolanaEventFilter,
    SolanaConfig
)

logger = logging.getLogger(__name__)


class SolanaProvider:
    """
    Главный провайдер для Solana блокчейна
    Координирует работу всех подкомпонентов
    """
    
    def __init__(self, session, rate_limiter, tx_cache, dex_detector: DEXDetector = None):
        """
        Инициализация провайдера
        
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
        
        # Инициализация компонентов
        self.rpc_client = SolanaRPCClient(session, rate_limiter)
        self.price_provider = SolanaPriceProvider(session)
        self.transaction_parser = SolanaTransactionParser(
            dex_detector=self.dex_detector,
            price_provider=self.price_provider
        )
        self.event_filter = SolanaEventFilter()
        
        # Статистика
        self.stats = {
            "signatures_fetched": 0,
            "transactions_processed": 0,
            "events_found": 0,
            "errors": 0
        }
        
        logger.info("🔧 [SOLANA] Провайдер инициализирован")
        
        # Проверка API ключа
        if not self.rpc_client.has_api_key():
            logger.warning(
                "⚠️ [SOLANA] Helius API ключ не настроен! "
                "Функциональность ограничена публичными endpoints"
            )
    
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
        
        logger.info(f"🔍 [SOLANA] Начинаю сканирование с {start_time}")
        
        # Сброс статистики
        self._reset_stats()
        
        events = []
        
        try:
            # Получение SOL переводов
            sol_events = await self._fetch_sol_transfers(start_time)
            events.extend(sol_events)
            
            # Получение SPL токен переводов
            spl_events = await self._fetch_spl_transfers(start_time, assets)
            events.extend(spl_events)
            
            # Логирование результатов
            self._log_scan_results()
        
        except Exception as e:
            logger.error(f"❌ [SOLANA] Критическая ошибка при сканировании: {e}", exc_info=True)
            self.stats["errors"] += 1
        
        return events
    
    async def _fetch_sol_transfers(self, start_time: datetime) -> List[WhaleEvent]:
        """
        Получение крупных SOL переводов
        
        Args:
            start_time: Время начала периода
            
        Returns:
            Список SOL whale событий
        """
        events = []
        
        try:
            # Получение подписей последних транзакций
            signatures = await self._get_recent_signatures(start_time)
            
            if not signatures:
                logger.info("👍 [SOLANA] Нет новых подписей для обработки")
                return []
            
            logger.info(f"📥 [SOLANA] Получено {len(signatures)} подписей")
            self.stats["signatures_fetched"] = len(signatures)
            
            # Обработка транзакций батчами
            batch_size = 20
            
            for i in range(0, len(signatures), batch_size):
                batch = signatures[i:i + batch_size]
                batch_events = await self._process_signature_batch(batch)
                events.extend(batch_events)
                
                # Задержка между батчами
                if i + batch_size < len(signatures):
                    await asyncio.sleep(0.5)
            
            logger.info(f"✅ [SOLANA] Найдено {len(events)} SOL событий")
        
        except Exception as e:
            logger.error(f"❌ [SOLANA] Ошибка получения SOL переводов: {e}")
            self.stats["errors"] += 1
        
        return events
    
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
        # TODO: Реализация SPL токен мониторинга в следующей версии
        # Требует работу с getSignaturesForAddress для конкретных токен программ
        # и парсинг SPL Transfer инструкций
        return []
    
    async def _get_recent_signatures(
        self,
        start_time: datetime,
        limit: int = 100
    ) -> List[dict]:
        """
        Получение недавних подписей транзакций
        
        Args:
            start_time: Время начала периода
            limit: Максимальное количество подписей
            
        Returns:
            Список подписей с метаданными
        """
        try:
            # Используем системную программу для получения активности
            system_program = SolanaConfig.SYSTEM_PROGRAM_ID
            
            signatures = await self.rpc_client.get_signatures_for_address(
                address=system_program,
                limit=min(limit, 1000)
            )
            
            if not signatures:
                return []
            
            # Фильтрация по времени
            start_timestamp = start_time.timestamp()
            filtered_signatures = []
            
            for sig in signatures:
                block_time = sig.get("blockTime")
                
                if block_time and block_time >= start_timestamp:
                    filtered_signatures.append(sig)
            
            logger.info(
                f"📊 [SOLANA] Отфильтровано {len(filtered_signatures)}/{len(signatures)} "
                f"подписей по времени"
            )
            
            return filtered_signatures
        
        except Exception as e:
            logger.error(f"❌ [SOLANA] Ошибка получения подписей: {e}")
            return []
    
    async def _process_signature_batch(self, signatures: List[dict]) -> List[WhaleEvent]:
        """
        Обработка батча подписей
        
        Args:
            signatures: Список подписей для обработки
            
        Returns:
            Список событий из этого батча
        """
        events = []
        
        # Создание задач для параллельного получения транзакций
        tasks = [
            self._process_signature(sig)
            for sig in signatures
        ]
        
        # Выполнение с обработкой исключений
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Сбор успешных результатов
        for result in results:
            if isinstance(result, Exception):
                logger.debug(f"⚠️ [SOLANA] Ошибка обработки подписи: {result}")
                continue
            
            if result:
                events.append(result)
        
        return events
    
    async def _process_signature(self, signature_data: dict) -> Optional[WhaleEvent]:
        """
        Обработка одной подписи транзакции
        
        Args:
            signature_data: Данные подписи
            
        Returns:
            WhaleEvent или None
        """
        signature = signature_data.get("signature")
        
        if not signature:
            return None
        
        # Проверка кэша
        if self.tx_cache.contains(signature):
            return None
        
        try:
            # Получение полных данных транзакции
            tx_data = await self.rpc_client.get_transaction(signature)
            
            if not tx_data:
                return None
            
            self.stats["transactions_processed"] += 1
            
            # Парсинг транзакции
            event = await self.transaction_parser.parse_transaction(tx_data)
            
            if event:
                # Фильтрация события
                if self.event_filter.should_process(event):
                    self.tx_cache.add(signature)
                    self.stats["events_found"] += 1
                    
                    logger.info(
                        f"💰 [SOLANA] Найдено событие: {event.asset} "
                        f"${event.amount_usd:,.0f}"
                    )
                    
                    return event
        
        except Exception as e:
            logger.debug(f"⚠️ [SOLANA] Ошибка обработки {signature[:16]}...: {e}")
        
        return None
    
    def _reset_stats(self):
        """Сброс статистики"""
        self.stats = {
            "signatures_fetched": 0,
            "transactions_processed": 0,
            "events_found": 0,
            "errors": 0
        }
    
    def _log_scan_results(self):
        """Логирование результатов сканирования"""
        logger.info(
            f"📊 [SOLANA] Результаты: "
            f"подписей={self.stats['signatures_fetched']}, "
            f"обработано={self.stats['transactions_processed']}, "
            f"событий={self.stats['events_found']}, "
            f"ошибок={self.stats['errors']}"
        )
    
    def get_stats(self) -> dict:
        """
        Получение статистики провайдера
        
        Returns:
            Dict со статистикой
        """
        return self.stats.copy()