# app/whales/monitor/evm_components/evm_rpc_client.py
"""
EVM RPC Client
Клиент для взаимодействия с EVM RPC endpoints
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List

from .evm_config import EVMChainConfig

logger = logging.getLogger(__name__)


class EVMRPCClient:
    """RPC клиент для EVM блокчейнов"""
    
    def __init__(self, session):
        """
        Args:
            session: aiohttp ClientSession
        """
        self.session = session
        self.request_timeout = 20
        self.max_retries = 3
    
    async def call_rpc(
        self,
        chain: str,
        method: str,
        params: List[Any],
        timeout: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Выполнение RPC запроса с fallback на другие endpoints
        
        Args:
            chain: Название блокчейна
            method: RPC метод
            params: Параметры метода
            timeout: Таймаут запроса
            
        Returns:
            Результат RPC запроса или None
        """
        rpc_urls = EVMChainConfig.get_rpc_endpoints(chain)
        
        if not rpc_urls:
            logger.error(f"❌ [RPC] Нет RPC endpoints для {chain}")
            return None
        
        timeout = timeout or self.request_timeout
        
        for rpc_url in rpc_urls:
            result = await self._try_rpc_call(
                rpc_url=rpc_url,
                method=method,
                params=params,
                timeout=timeout,
                chain=chain
            )
            
            if result is not None:
                return result
        
        logger.error(f"❌ [RPC] Все endpoints для {chain} недоступны")
        return None
    
    async def _try_rpc_call(
        self,
        rpc_url: str,
        method: str,
        params: List[Any],
        timeout: int,
        chain: str
    ) -> Optional[Dict]:
        """
        Попытка выполнения RPC запроса к одному endpoint
        
        Args:
            rpc_url: URL RPC endpoint
            method: RPC метод
            params: Параметры
            timeout: Таймаут
            chain: Название chain (для логирования)
            
        Returns:
            Результат или None
        """
        for attempt in range(self.max_retries):
            try:
                payload = {
                    "jsonrpc": "2.0",
                    "method": method,
                    "params": params,
                    "id": 1
                }
                
                headers = {"Content-Type": "application/json"}
                
                async with self.session.post(
                    rpc_url,
                    json=payload,
                    headers=headers,
                    timeout=timeout
                ) as response:
                    
                    if response.status != 200:
                        logger.debug(
                            f"⚠️ [RPC] {chain} {rpc_url}: HTTP {response.status}"
                        )
                        continue
                    
                    data = await response.json()
                    
                    # Проверка на ошибку в ответе
                    if "error" in data:
                        error_msg = data["error"].get("message", "Unknown error")
                        logger.debug(
                            f"⚠️ [RPC] {chain} {rpc_url}: {error_msg}"
                        )
                        continue
                    
                    # Успешный результат
                    if "result" in data:
                        logger.debug(f"✅ [RPC] {chain} {method} успешно через {rpc_url}")
                        return data["result"]
            
            except asyncio.TimeoutError:
                logger.debug(
                    f"⏱️ [RPC] {chain} {rpc_url}: timeout (попытка {attempt + 1}/{self.max_retries})"
                )
                await asyncio.sleep(0.5 * (attempt + 1))
                continue
            
            except Exception as e:
                logger.debug(
                    f"⚠️ [RPC] {chain} {rpc_url}: {type(e).__name__}: {e}"
                )
                continue
        
        return None
    
    async def get_block_number(self, chain: str) -> Optional[int]:
        """
        Получение номера последнего блока
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Номер блока или None
        """
        result = await self.call_rpc(
            chain=chain,
            method="eth_blockNumber",
            params=[],
            timeout=15
        )
        
        if result and isinstance(result, str) and result.startswith("0x"):
            try:
                return int(result, 16)
            except ValueError:
                return None
        
        return None
    
    async def get_block_by_number(
        self,
        chain: str,
        block_number: int,
        full_transactions: bool = True
    ) -> Optional[Dict]:
        """
        Получение блока по номеру
        
        Args:
            chain: Название блокчейна
            block_number: Номер блока
            full_transactions: Возвращать полные транзакции или только хэши
            
        Returns:
            Данные блока или None
        """
        result = await self.call_rpc(
            chain=chain,
            method="eth_getBlockByNumber",
            params=[hex(block_number), full_transactions],
            timeout=20
        )
        
        return result