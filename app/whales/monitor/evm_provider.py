# app/whales/monitor/evm_provider.py
"""
EVM Chain Provider v3.0
Модульная архитектура для работы с EVM-совместимыми блокчейнами
"""

import asyncio
import logging
from typing import List, Optional
from datetime import datetime

from app.config import config
from app.whales.normalize import WhaleEvent
from app.whales.monitor.dex_detector import DEXDetector
from .evm_components import (
    EVMBlockFetcher,
    EVMTransactionParser,
    EVMPriceProvider,
    EVMRPCClient,
    EVMEventFilter
)

logger = logging.getLogger(__name__)


class EVMProvider:
    """
    Главный провайдер для EVM-совместимых блокчейнов
    Координирует работу всех подкомпонентов
    """
    
    SUPPORTED_CHAINS = ["ethereum", "bsc", "base", "arbitrum", "polygon"]
    
    def __init__(self, session, rate_limiter, tx_cache, dex_detector: DEXDetector):
        """
        Инициализация провайдера
        
        Args:
            session: aiohttp ClientSession
            rate_limiter: Rate limiter для контроля частоты запросов
            tx_cache: Кэш обработанных транзакций
            dex_detector: Детектор DEX адресов
        """
        self.session = session
        self.rate_limiter = rate_limiter
        self.tx_cache = tx_cache
        self.dex_detector = dex_detector
        
        # Инициализация компонентов
        self.rpc_client = EVMRPCClient(session)
        self.block_fetcher = EVMBlockFetcher(self.rpc_client, rate_limiter)
        self.price_provider = EVMPriceProvider(session)
        self.transaction_parser = EVMTransactionParser(
            dex_detector, 
            self.price_provider
        )
        self.event_filter = EVMEventFilter()
        
        # Статистика
        self.stats = {
            "blocks_scanned": 0,
            "transactions_checked": 0,
            "events_found": 0,
            "errors": 0
        }
        
        logger.info("🔧 [EVM] Провайдер инициализирован для chains: %s", self.SUPPORTED_CHAINS)
    
    async def fetch_events(
        self,
        chain: str,
        start_time: datetime,
        assets: Optional[List[str]] = None
    ) -> List[WhaleEvent]:
        """
        Получение whale событий для указанного EVM chain
        
        Args:
            chain: Название блокчейна
            start_time: Время начала периода мониторинга
            assets: Список активов для мониторинга (опционально)
            
        Returns:
            Список обнаруженных whale событий
        """
        if chain not in self.SUPPORTED_CHAINS:
            logger.error(f"❌ [EVM] Неподдерживаемый chain: {chain}")
            return []
        
        logger.info(f"🔍 [EVM] Начинаю сканирование {chain} с {start_time}")
        
        # Сброс статистики для нового цикла
        self._reset_stats()
        
        events = []
        
        try:
            # Получение нативных переводов
            native_events = await self._fetch_native_transfers(chain, start_time)
            events.extend(native_events)
            
            # Получение ERC20 переводов (если доступно)
            erc20_events = await self._fetch_erc20_transfers(chain, start_time, assets)
            events.extend(erc20_events)
            
            # Логирование результатов
            self._log_scan_results(chain)
            
        except Exception as e:
            logger.error(f"❌ [EVM] Критическая ошибка при сканировании {chain}: {e}", exc_info=True)
            self.stats["errors"] += 1
        
        return events
    
    async def _fetch_native_transfers(
        self,
        chain: str,
        start_time: datetime
    ) -> List[WhaleEvent]:
        """
        Получение крупных нативных переводов (ETH, BNB, MATIC и т.д.)
        
        Args:
            chain: Название блокчейна
            start_time: Время начала периода
            
        Returns:
            Список нативных whale событий
        """
        events = []
        
        try:
            # Определение диапазона блоков для сканирования
            latest_block = await self.block_fetcher.get_latest_block_number(chain)
            
            if latest_block is None:
                logger.warning(f"⚠️ [EVM] Не удалось получить latest block для {chain}")
                return []
            
            blocks_to_scan = self._calculate_blocks_to_scan(chain, start_time, latest_block)
            start_block = max(latest_block - blocks_to_scan, 0)
            
            logger.info(
                f"📊 [EVM] {chain}: будут проверены блоки {start_block}-{latest_block} "
                f"({blocks_to_scan} блоков)"
            )
            
            # Сканирование блоков батчами
            batch_events = await self.block_fetcher.fetch_blocks_batch(
                chain=chain,
                start_block=start_block,
                end_block=latest_block,
                batch_size=10
            )
            
            # Обработка транзакций из блоков
            for block_data in batch_events:
                block_events = await self._process_block(block_data, chain)
                events.extend(block_events)
                self.stats["blocks_scanned"] += 1
            
            logger.info(f"✅ [EVM] {chain}: найдено {len(events)} нативных событий")
        
        except Exception as e:
            logger.error(f"❌ [EVM] Ошибка получения нативных переводов {chain}: {e}")
            self.stats["errors"] += 1
        
        return events
    
    async def _fetch_erc20_transfers(
        self,
        chain: str,
        start_time: datetime,
        assets: Optional[List[str]] = None
    ) -> List[WhaleEvent]:
        """
        Получение крупных ERC20 переводов
        
        Args:
            chain: Название блокчейна
            start_time: Время начала периода
            assets: Список токенов для мониторинга
            
        Returns:
            Список ERC20 whale событий
        """
        # TODO: Реализация ERC20 мониторинга в следующей версии
        # Требует декодирование логов событий Transfer
        return []
    
    async def _process_block(
        self,
        block_data: dict,
        chain: str
    ) -> List[WhaleEvent]:
        """
        Обработка одного блока и его транзакций
        
        Args:
            block_data: Данные блока из RPC
            chain: Название блокчейна
            
        Returns:
            Список событий из этого блока
        """
        events = []
        
        if not block_data:
            return events
        
        # Получение timestamp блока
        block_timestamp = block_data.get("timestamp")
        block_number = block_data.get("number")
        
        if not block_timestamp:
            logger.debug(f"⚠️ [EVM] Блок {block_number} не имеет timestamp")
            return events
        
        # Конвертация timestamp
        try:
            if isinstance(block_timestamp, str):
                timestamp_int = int(block_timestamp, 16)
            else:
                timestamp_int = int(block_timestamp)
            
            block_time = datetime.utcfromtimestamp(timestamp_int)
        except (ValueError, TypeError, OSError) as e:
            logger.warning(f"⚠️ [EVM] Ошибка парсинга timestamp блока {block_number}: {e}")
            block_time = datetime.utcnow()
        
        # Обработка транзакций
        transactions = block_data.get("transactions", [])
        
        logger.debug(f"🔍 [EVM] Блок {block_number}: {len(transactions)} транзакций")
        
        for tx in transactions:
            if not isinstance(tx, dict):
                continue
            
            self.stats["transactions_checked"] += 1
            
            # Проверка кэша
            tx_hash = tx.get("hash", "")
            if self.tx_cache.contains(tx_hash):
                continue
            
            # Парсинг транзакции
            event = await self.transaction_parser.parse_native_transaction(
                tx=tx,
                chain=chain,
                block_time=block_time
            )
            
            if event:
                # Фильтрация события
                if self.event_filter.should_process(event):
                    events.append(event)
                    self.tx_cache.add(tx_hash)
                    self.stats["events_found"] += 1
                    
                    logger.info(
                        f"💰 [EVM] Найдено событие: {event.asset} "
                        f"${event.amount_usd:,.0f} на {chain}"
                    )
        
        return events
    
    def _calculate_blocks_to_scan(
        self,
        chain: str,
        start_time: datetime,
        latest_block: int
    ) -> int:
        """
        Расчёт количества блоков для сканирования
        
        Args:
            chain: Название блокчейна
            start_time: Время начала
            latest_block: Номер последнего блока
            
        Returns:
            Количество блоков для сканирования
        """
        time_window_seconds = (datetime.utcnow() - start_time).total_seconds()
        
        # Получение среднего времени блока
        block_time = self.block_fetcher.get_block_time(chain)
        
        # Расчёт количества блоков
        estimated_blocks = int(time_window_seconds / block_time)
        
        # Ограничение максимального количества блоков
        max_blocks = 100
        blocks_to_scan = min(estimated_blocks, max_blocks)
        
        logger.debug(
            f"📊 [EVM] {chain}: время окна {time_window_seconds}s, "
            f"block_time {block_time}s, сканирую {blocks_to_scan} блоков"
        )
        
        return blocks_to_scan
    
    def _reset_stats(self):
        """Сброс статистики"""
        self.stats = {
            "blocks_scanned": 0,
            "transactions_checked": 0,
            "events_found": 0,
            "errors": 0
        }
    
    def _log_scan_results(self, chain: str):
        """
        Логирование результатов сканирования
        
        Args:
            chain: Название блокчейна
        """
        logger.info(
            f"📊 [EVM] {chain} - Результаты сканирования: "
            f"блоков={self.stats['blocks_scanned']}, "
            f"транзакций={self.stats['transactions_checked']}, "
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