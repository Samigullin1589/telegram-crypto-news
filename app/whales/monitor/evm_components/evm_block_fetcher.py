# app/whales/monitor/evm_components/evm_block_fetcher.py
"""
EVM Block Fetcher
Получение блоков из EVM блокчейнов
"""

import asyncio
import logging
from typing import List, Optional, Dict

from .evm_rpc_client import EVMRPCClient
from .evm_config import EVMChainConfig

logger = logging.getLogger(__name__)


class EVMBlockFetcher:
    """Получение блоков из EVM chains"""
    
    def __init__(self, rpc_client: EVMRPCClient, rate_limiter):
        """
        Args:
            rpc_client: RPC клиент
            rate_limiter: Rate limiter
        """
        self.rpc_client = rpc_client
        self.rate_limiter = rate_limiter
    
    async def get_latest_block_number(self, chain: str) -> Optional[int]:
        """
        Получение номера последнего блока
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Номер блока или None
        """
        block_number = await self.rpc_client.get_block_number(chain)
        
        if block_number:
            logger.debug(f"🔢 [BLOCK] {chain}: latest block = {block_number}")
        else:
            logger.warning(f"⚠️ [BLOCK] {chain}: не удалось получить latest block")
        
        return block_number
    
    async def fetch_block(
        self,
        chain: str,
        block_number: int
    ) -> Optional[Dict]:
        """
        Получение одного блока с транзакциями
        
        Args:
            chain: Название блокчейна
            block_number: Номер блока
            
        Returns:
            Данные блока или None
        """
        block_data = await self.rpc_client.get_block_by_number(
            chain=chain,
            block_number=block_number,
            full_transactions=True
        )
        
        if block_data:
            tx_count = len(block_data.get("transactions", []))
            logger.debug(
                f"📦 [BLOCK] {chain} блок {block_number}: {tx_count} транзакций"
            )
        
        return block_data
    
    async def fetch_blocks_batch(
        self,
        chain: str,
        start_block: int,
        end_block: int,
        batch_size: int = 10
    ) -> List[Dict]:
        """
        Получение батча блоков
        
        Args:
            chain: Название блокчейна
            start_block: Начальный блок
            end_block: Конечный блок
            batch_size: Размер батча
            
        Returns:
            Список блоков
        """
        all_blocks = []
        
        for block_num in range(start_block, end_block, batch_size):
            actual_batch_size = min(batch_size, end_block - block_num)
            
            # Создание задач для параллельного получения
            tasks = [
                self.fetch_block(chain, block_num + i)
                for i in range(actual_batch_size)
            ]
            
            # Выполнение с обработкой исключений
            blocks = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Фильтрация успешных результатов
            for block_data in blocks:
                if isinstance(block_data, Exception):
                    logger.debug(f"⚠️ [BLOCK] Ошибка получения блока: {block_data}")
                    continue
                
                if block_data:
                    all_blocks.append(block_data)
            
            # Небольшая задержка между батчами
            if block_num + batch_size < end_block:
                await asyncio.sleep(0.2)
        
        logger.info(
            f"📦 [BLOCK] {chain}: получено {len(all_blocks)} блоков "
            f"из диапазона {start_block}-{end_block}"
        )
        
        return all_blocks
    
    def get_block_time(self, chain: str) -> float:
        """
        Получение среднего времени блока
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Время блока в секундах
        """
        return EVMChainConfig.get_block_time(chain)