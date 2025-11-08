# app/whales/monitor/solana_components/solana_transaction_processor.py
"""
Solana Transaction Processor
Обработка и парсинг транзакций Solana
"""

import asyncio
import logging
from typing import List, Optional

from app.whales.normalize import WhaleEvent

logger = logging.getLogger(__name__)


class SolanaTransactionProcessor:
    """
    Процессор для обработки батчей транзакций Solana
    Поддерживает параллельную обработку и error handling
    """
    
    def __init__(
        self,
        rpc_client,
        transaction_parser,
        event_filter,
        tx_cache
    ):
        """
        Args:
            rpc_client: SolanaRPCClient
            transaction_parser: SolanaTransactionParser
            event_filter: SolanaEventFilter
            tx_cache: Кэш обработанных транзакций
        """
        self.rpc_client = rpc_client
        self.transaction_parser = transaction_parser
        self.event_filter = event_filter
        self.tx_cache = tx_cache
        
        self.batch_size = 20
        self.batch_delay = 0.5
        
        self.stats = {
            "processed": 0,
            "cached_hits": 0,
            "events_found": 0,
            "errors": 0
        }
    
    async def process_signatures(
        self,
        signatures: List[dict]
    ) -> List[WhaleEvent]:
        """
        Обработка списка подписей
        
        Args:
            signatures: Список подписей для обработки
            
        Returns:
            Список найденных событий
        """
        if not signatures:
            return []
        
        logger.info(f"🔄 [PROCESSOR] Обработка {len(signatures)} подписей...")
        
        events = []
        
        for i in range(0, len(signatures), self.batch_size):
            batch = signatures[i:i + self.batch_size]
            batch_events = await self._process_batch(batch)
            events.extend(batch_events)
            
            if i + self.batch_size < len(signatures):
                await asyncio.sleep(self.batch_delay)
        
        logger.info(
            f"✅ [PROCESSOR] Обработано {self.stats['processed']} транзакций, "
            f"найдено {len(events)} событий"
        )
        
        return events
    
    async def _process_batch(self, signatures: List[dict]) -> List[WhaleEvent]:
        """
        Обработка батча подписей
        
        Args:
            signatures: Батч подписей
            
        Returns:
            Список событий из батча
        """
        tasks = [
            self._process_single_signature(sig)
            for sig in signatures
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        events = []
        for result in results:
            if isinstance(result, Exception):
                logger.debug(f"⚠️ [PROCESSOR] Ошибка: {result}")
                self.stats["errors"] += 1
                continue
            
            if result:
                events.append(result)
                self.stats["events_found"] += 1
        
        return events
    
    async def _process_single_signature(
        self,
        signature_data: dict
    ) -> Optional[WhaleEvent]:
        """
        Обработка одной подписи
        
        Args:
            signature_data: Данные подписи
            
        Returns:
            WhaleEvent или None
        """
        signature = signature_data.get("signature")
        
        if not signature:
            return None
        
        if self.tx_cache.contains(signature):
            self.stats["cached_hits"] += 1
            return None
        
        try:
            tx_data = await self.rpc_client.get_transaction(signature)
            
            if not tx_data:
                return None
            
            self.stats["processed"] += 1
            
            event = await self.transaction_parser.parse_transaction(tx_data)
            
            if not event:
                return None
            
            if not self.event_filter.should_process(event):
                return None
            
            self.tx_cache.add(signature)
            
            logger.info(
                f"💰 [PROCESSOR] Событие: {event.asset} ${event.amount_usd:,.0f}"
            )
            
            return event
        
        except Exception as e:
            logger.debug(f"⚠️ [PROCESSOR] Ошибка {signature[:16]}...: {e}")
            return None
    
    def get_stats(self) -> dict:
        """Статистика обработки"""
        return self.stats.copy()
    
    def reset_stats(self) -> None:
        """Сброс статистики"""
        self.stats = {
            "processed": 0,
            "cached_hits": 0,
            "events_found": 0,
            "errors": 0
        }