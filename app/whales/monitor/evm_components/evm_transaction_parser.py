# app/whales/monitor/evm_components/evm_transaction_parser.py
"""
EVM Transaction Parser
Парсинг EVM транзакций в whale события
"""

import logging
from typing import Optional
from datetime import datetime

from app.config import config
from app.whales.normalize import WhaleEvent
from app.whales.monitor.dex_detector import DEXDetector
from .evm_config import EVMChainConfig
from .evm_price_provider import EVMPriceProvider

logger = logging.getLogger(__name__)


class EVMTransactionParser:
    """Парсер EVM транзакций"""
    
    def __init__(self, dex_detector: DEXDetector, price_provider: EVMPriceProvider):
        """
        Args:
            dex_detector: Детектор DEX адресов
            price_provider: Провайдер цен
        """
        self.dex_detector = dex_detector
        self.price_provider = price_provider
    
    async def parse_native_transaction(
        self,
        tx: dict,
        chain: str,
        block_time: datetime
    ) -> Optional[WhaleEvent]:
        """
        Парсинг нативной транзакции (ETH, BNB, MATIC)
        
        Args:
            tx: Данные транзакции
            chain: Название блокчейна
            block_time: Время блока
            
        Returns:
            WhaleEvent или None
        """
        try:
            # Извлечение базовых данных
            from_addr = tx.get("from", "").lower()
            to_addr = tx.get("to", "").lower()
            
            if not from_addr or not to_addr:
                return None
            
            # Парсинг value
            value_hex = tx.get("value", "0x0")
            
            if not isinstance(value_hex, str):
                return None
            
            try:
                value_wei = int(value_hex, 16)
            except (ValueError, TypeError):
                return None
            
            # Пропуск нулевых переводов
            if value_wei == 0:
                return None
            
            # Получение конфигурации chain
            decimals = EVMChainConfig.get_decimals(chain)
            native_token = EVMChainConfig.get_native_token(chain)
            
            # Конвертация в нативные единицы
            amount = value_wei / (10 ** decimals)
            
            # Получение реальной цены
            price = await self.price_provider.get_token_price(native_token, chain)
            amount_usd = amount * price
            
            # Первичный фильтр по сумме
            # ИСПРАВЛЕНО: Безопасный доступ к config.features.whale.min_usd_threshold
            _features = getattr(config, 'features', None)
            _whale = getattr(_features, 'whale', None) if _features else None
            min_threshold = getattr(_whale, 'min_usd_threshold', 50000) if _whale else 50000
            if amount_usd < min_threshold * 0.5:  # 50% порог для предварительной фильтрации
                return None
            
            # Детекция DEX
            dex = self.dex_detector.detect_evm_dex(chain, to_addr) or None
            
            # Создание события
            event = WhaleEvent(
                chain=chain,
                asset=native_token,
                from_address=from_addr,
                to_address=to_addr,
                amount_native=amount,
                amount_usd=amount_usd,
                price_usd=price,
                tx_hash=tx.get("hash", ""),
                direction="unknown",
                phase="execution",
                dex=dex,
                is_internal=False,
                is_bridge=False,
                is_reorg=False,
                tx_time_utc=block_time
            )
            
            logger.debug(
                f"✅ [PARSE] {native_token}: {amount:.4f} "
                f"(${amount_usd:,.0f}) от {from_addr[:10]}... к {to_addr[:10]}..."
            )
            
            return event
        
        except Exception as e:
            logger.debug(f"⚠️ [PARSE] Ошибка парсинга транзакции: {e}")
            return None