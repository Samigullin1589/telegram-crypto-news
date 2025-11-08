# app/whales/monitor/solana_components/solana_signature_fetcher.py
"""
Solana Signature Fetcher
Получение и фильтрация подписей транзакций
"""

import logging
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SolanaSignatureFetcher:
    """
    Компонент для получения подписей транзакций Solana
    Поддерживает фильтрацию по времени и лимитам
    """
    
    SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"
    
    def __init__(self, rpc_client):
        """
        Args:
            rpc_client: SolanaRPCClient для взаимодействия с RPC
        """
        self.rpc_client = rpc_client
        self.max_signatures_per_request = 1000
    
    async def get_recent_signatures(
        self,
        start_time: datetime,
        limit: int = 100,
        address: Optional[str] = None
    ) -> List[dict]:
        """
        Получение недавних подписей транзакций
        
        Args:
            start_time: Время начала периода
            limit: Максимальное количество подписей
            address: Адрес для мониторинга (если None - используется system program)
            
        Returns:
            Список подписей с метаданными
        """
        target_address = address or self.SYSTEM_PROGRAM_ID
        
        try:
            signatures = await self.rpc_client.get_signatures_for_address(
                address=target_address,
                limit=min(limit, self.max_signatures_per_request)
            )
            
            if not signatures:
                logger.debug(f"[SIGNATURE] Нет подписей для {target_address[:8]}...")
                return []
            
            filtered = self._filter_by_time(signatures, start_time)
            
            logger.info(
                f"📊 [SIGNATURE] Отфильтровано {len(filtered)}/{len(signatures)} "
                f"подписей по времени"
            )
            
            return filtered
        
        except Exception as e:
            logger.error(f"❌ [SIGNATURE] Ошибка получения подписей: {e}")
            return []
    
    async def get_signatures_for_token(
        self,
        token_mint: str,
        start_time: datetime,
        limit: int = 100
    ) -> List[dict]:
        """
        Получение подписей для конкретного SPL токена
        
        Args:
            token_mint: Адрес mint токена
            start_time: Время начала периода
            limit: Максимальное количество подписей
            
        Returns:
            Список подписей
        """
        try:
            signatures = await self.rpc_client.get_signatures_for_address(
                address=token_mint,
                limit=min(limit, self.max_signatures_per_request)
            )
            
            if not signatures:
                return []
            
            return self._filter_by_time(signatures, start_time)
        
        except Exception as e:
            logger.debug(f"⚠️ [SIGNATURE] Ошибка для токена {token_mint[:8]}...: {e}")
            return []
    
    def _filter_by_time(
        self,
        signatures: List[dict],
        start_time: datetime
    ) -> List[dict]:
        """
        Фильтрация подписей по времени
        
        Args:
            signatures: Список подписей
            start_time: Минимальное время
            
        Returns:
            Отфильтрованный список
        """
        start_timestamp = start_time.timestamp()
        
        filtered = []
        for sig in signatures:
            block_time = sig.get("blockTime")
            
            if block_time and block_time >= start_timestamp:
                filtered.append(sig)
        
        return filtered
    
    async def get_signatures_batch(
        self,
        addresses: List[str],
        start_time: datetime,
        limit_per_address: int = 50
    ) -> dict:
        """
        Получение подписей для нескольких адресов
        
        Args:
            addresses: Список адресов
            start_time: Время начала периода
            limit_per_address: Лимит на каждый адрес
            
        Returns:
            Dict {address: [signatures]}
        """
        results = {}
        
        for address in addresses:
            signatures = await self.get_recent_signatures(
                start_time=start_time,
                limit=limit_per_address,
                address=address
            )
            
            if signatures:
                results[address] = signatures
        
        return results