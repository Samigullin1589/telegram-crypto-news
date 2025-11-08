# app/whales/monitor/solana_components/solana_rpc_client.py
"""
Solana RPC Client
Клиент для взаимодействия с Solana RPC
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any

from app.config import config
from .solana_config import SolanaConfig

logger = logging.getLogger(__name__)


class SolanaRPCClient:
    """RPC клиент для Solana"""
    
    def __init__(self, session, rate_limiter):
        """
        Args:
            session: aiohttp ClientSession
            rate_limiter: Rate limiter
        """
        self.session = session
        self.rate_limiter = rate_limiter
        
        # Получение API ключа
        self.api_key = self._get_api_key()
        
        # Получение endpoints
        self.rpc_endpoints = SolanaConfig.get_rpc_endpoints(self.api_key)
        
        # Настройки
        self.request_timeout = 20
        self.max_retries = 3
        
        logger.debug(
            f"🔧 [SOLANA RPC] Инициализирован с {len(self.rpc_endpoints)} endpoints"
        )
    
    def _get_api_key(self) -> Optional[str]:
        """
        Получение Helius API ключа из конфигурации
        
        Returns:
            API ключ или None
        """
        # Попытка получить из config.chains.api_keys
        if hasattr(config, 'chains') and hasattr(config.chains, 'api_keys'):
            api_key = getattr(config.chains.api_keys, 'helius', None)
            if api_key:
                return api_key
        
        # Попытка получить из прямой переменной
        api_key = getattr(config, 'HELIUS_API_KEY', None)
        if api_key:
            return api_key
        
        return None
    
    def has_api_key(self) -> bool:
        """
        Проверка наличия API ключа
        
        Returns:
            True если API ключ настроен
        """
        return bool(self.api_key)
    
    async def call_rpc(
        self,
        method: str,
        params: List[Any],
        timeout: Optional[int] = None
    ) -> Optional[Any]:
        """
        Выполнение RPC запроса с fallback
        
        Args:
            method: RPC метод
            params: Параметры метода
            timeout: Таймаут запроса
            
        Returns:
            Результат RPC запроса или None
        """
        timeout = timeout or self.request_timeout
        
        for rpc_url in self.rpc_endpoints:
            result = await self._try_rpc_call(
                rpc_url=rpc_url,
                method=method,
                params=params,
                timeout=timeout
            )
            
            if result is not None:
                return result
        
        logger.error(f"❌ [SOLANA RPC] Все endpoints недоступны для метода {method}")
        return None
    
    async def _try_rpc_call(
        self,
        rpc_url: str,
        method: str,
        params: List[Any],
        timeout: int
    ) -> Optional[Any]:
        """
        Попытка выполнения RPC запроса к одному endpoint
        
        Args:
            rpc_url: URL RPC endpoint
            method: RPC метод
            params: Параметры
            timeout: Таймаут
            
        Returns:
            Результат или None
        """
        for attempt in range(self.max_retries):
            try:
                # Rate limiting
                if self.rate_limiter:
                    await self.rate_limiter.acquire()
                
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": method,
                    "params": params
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
                            f"⚠️ [SOLANA RPC] {rpc_url[:50]}...: HTTP {response.status}"
                        )
                        continue
                    
                    data = await response.json()
                    
                    # Проверка на ошибку
                    if "error" in data:
                        error_msg = data["error"].get("message", "Unknown error")
                        logger.debug(f"⚠️ [SOLANA RPC] Ошибка: {error_msg}")
                        continue
                    
                    # Успешный результат
                    if "result" in data:
                        logger.debug(f"✅ [SOLANA RPC] {method} успешно")
                        return data["result"]
            
            except asyncio.TimeoutError:
                logger.debug(
                    f"⏱️ [SOLANA RPC] Timeout (попытка {attempt + 1}/{self.max_retries})"
                )
                await asyncio.sleep(0.5 * (attempt + 1))
                continue
            
            except Exception as e:
                logger.debug(f"⚠️ [SOLANA RPC] {type(e).__name__}: {e}")
                continue
        
        return None
    
    async def get_signatures_for_address(
        self,
        address: str,
        limit: int = 100,
        before: Optional[str] = None,
        until: Optional[str] = None
    ) -> List[Dict]:
        """
        Получение подписей транзакций для адреса
        
        Args:
            address: Solana адрес
            limit: Максимальное количество подписей
            before: Подпись для пагинации (начать перед этой)
            until: Подпись для пагинации (закончить перед этой)
            
        Returns:
            Список подписей с метаданными
        """
        params = [address, {"limit": limit}]
        
        if before:
            params[1]["before"] = before
        
        if until:
            params[1]["until"] = until
        
        result = await self.call_rpc(
            method="getSignaturesForAddress",
            params=params
        )
        
        return result or []
    
    async def get_transaction(
        self,
        signature: str,
        max_supported_transaction_version: int = 0
    ) -> Optional[Dict]:
        """
        Получение данных транзакции
        
        Args:
            signature: Подпись транзакции
            max_supported_transaction_version: Максимальная версия транзакции
            
        Returns:
            Данные транзакции или None
        """
        params = [
            signature,
            {
                "encoding": "jsonParsed",
                "maxSupportedTransactionVersion": max_supported_transaction_version
            }
        ]
        
        result = await self.call_rpc(
            method="getTransaction",
            params=params,
            timeout=25
        )
        
        return result