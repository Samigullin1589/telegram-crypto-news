# app/whales/monitor/solana_components/solana_spl_monitor.py
"""
Solana SPL Token Monitor
Мониторинг переводов SPL токенов
"""

import logging
from typing import List, Optional
from datetime import datetime

from app.whales.normalize import WhaleEvent

logger = logging.getLogger(__name__)


class SolanaSPLMonitor:
    """
    Монитор для отслеживания крупных переводов SPL токенов
    """
    
    POPULAR_TOKENS = {
        "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
        "SOL": "So11111111111111111111111111111111111111112",
        "RAY": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
        "SRM": "SRMuApVNdxXokk5GT7XD5cUUgXMBCoAz2LHeuAoKWRt",
        "COPE": "8HGyAAB1yoM1ttS7pXjHMa3dukTFGQggnFFH3hJZgzQh",
        "STEP": "StepAscQoEioFxxWGnh2sLBDFp9d8rvKz2Yp39iDpyT",
        "MNGO": "MangoCzJ36AjZyKwVj3VnYU4GTonjfVEnJmvvWaxLac",
        "ORCA": "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",
    }
    
    MIN_AMOUNT_USD = {
        "USDC": 50000.0,
        "USDT": 50000.0,
        "SOL": 25000.0,
        "RAY": 10000.0,
        "SRM": 5000.0,
        "default": 10000.0
    }
    
    def __init__(
        self,
        signature_fetcher,
        transaction_parser,
        price_provider,
        event_filter
    ):
        """
        Args:
            signature_fetcher: SolanaSignatureFetcher
            transaction_parser: SolanaTransactionParser
            price_provider: SolanaPriceProvider
            event_filter: SolanaEventFilter
        """
        self.signature_fetcher = signature_fetcher
        self.transaction_parser = transaction_parser
        self.price_provider = price_provider
        self.event_filter = event_filter
        
        self.monitored_tokens = list(self.POPULAR_TOKENS.keys())
        
        self.stats = {
            "tokens_checked": 0,
            "signatures_fetched": 0,
            "events_found": 0
        }
    
    async def fetch_spl_events(
        self,
        start_time: datetime,
        assets: Optional[List[str]] = None
    ) -> List[WhaleEvent]:
        """
        Получение событий переводов SPL токенов
        
        Args:
            start_time: Время начала периода
            assets: Список токенов для мониторинга (если None - все популярные)
            
        Returns:
            Список найденных событий
        """
        tokens_to_monitor = assets if assets else self.monitored_tokens
        
        logger.info(
            f"🔍 [SPL] Мониторинг {len(tokens_to_monitor)} токенов: "
            f"{', '.join(tokens_to_monitor[:5])}..."
        )
        
        events = []
        
        for token_symbol in tokens_to_monitor:
            token_events = await self._monitor_token(token_symbol, start_time)
            events.extend(token_events)
            self.stats["tokens_checked"] += 1
        
        logger.info(
            f"✅ [SPL] Проверено {self.stats['tokens_checked']} токенов, "
            f"найдено {len(events)} событий"
        )
        
        return events
    
    async def _monitor_token(
        self,
        token_symbol: str,
        start_time: datetime
    ) -> List[WhaleEvent]:
        """
        Мониторинг конкретного токена
        
        Args:
            token_symbol: Символ токена (USDC, USDT, etc)
            start_time: Время начала периода
            
        Returns:
            Список событий для этого токена
        """
        mint_address = self.POPULAR_TOKENS.get(token_symbol)
        
        if not mint_address:
            logger.debug(f"⚠️ [SPL] Неизвестный токен: {token_symbol}")
            return []
        
        try:
            signatures = await self.signature_fetcher.get_signatures_for_token(
                token_mint=mint_address,
                start_time=start_time,
                limit=100
            )
            
            if not signatures:
                return []
            
            self.stats["signatures_fetched"] += len(signatures)
            
            events = await self._process_token_signatures(
                signatures,
                token_symbol,
                mint_address
            )
            
            return events
        
        except Exception as e:
            logger.error(f"❌ [SPL] Ошибка мониторинга {token_symbol}: {e}")
            return []
    
    async def _process_token_signatures(
        self,
        signatures: List[dict],
        token_symbol: str,
        mint_address: str
    ) -> List[WhaleEvent]:
        """
        Обработка подписей для токена
        
        Args:
            signatures: Список подписей
            token_symbol: Символ токена
            mint_address: Адрес mint
            
        Returns:
            Список событий
        """
        events = []
        threshold = self.MIN_AMOUNT_USD.get(
            token_symbol,
            self.MIN_AMOUNT_USD["default"]
        )
        
        for sig_data in signatures:
            try:
                event = await self._process_token_signature(
                    sig_data,
                    token_symbol,
                    mint_address,
                    threshold
                )
                
                if event:
                    events.append(event)
                    self.stats["events_found"] += 1
            
            except Exception as e:
                logger.debug(f"⚠️ [SPL] Ошибка обработки подписи: {e}")
                continue
        
        return events
    
    async def _process_token_signature(
        self,
        sig_data: dict,
        token_symbol: str,
        mint_address: str,
        threshold: float
    ) -> Optional[WhaleEvent]:
        """
        Обработка одной подписи токена
        
        Args:
            sig_data: Данные подписи
            token_symbol: Символ токена
            mint_address: Адрес mint
            threshold: Минимальная сумма в USD
            
        Returns:
            WhaleEvent или None
        """
        signature = sig_data.get("signature")
        
        if not signature:
            return None
        
        event = await self.transaction_parser.parse_spl_transfer(
            signature=signature,
            token_symbol=token_symbol,
            mint_address=mint_address
        )
        
        if not event:
            return None
        
        if event.amount_usd < threshold:
            return None
        
        if self.event_filter.should_process(event):
            logger.info(
                f"💰 [SPL] {token_symbol} перевод: ${event.amount_usd:,.0f}"
            )
            return event
        
        return None
    
    def get_stats(self) -> dict:
        """Статистика мониторинга SPL"""
        return self.stats.copy()