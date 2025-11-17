# app/config/hyperliquid_config.py
"""
Hyperliquid Configuration Module v1.0
Конфигурация для мониторинга Hyperliquid DEX
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class HyperliquidConfig:
    """
    Конфигурация для мониторинга Hyperliquid DEX

    Управляет:
    - API URL для Hyperliquid
    - Пороговые значения для сделок и ликвидаций
    - Настройки уведомлений
    """

    def __init__(self):
        """Инициализация конфигурации Hyperliquid"""
        logger.debug("Инициализация HyperliquidConfig v1.0...")

        # API URL
        self.api_url: Optional[str] = os.getenv('HYPERLIQUID_API_URL', '')

        # Пороговые значения в USD
        self.min_trade_usd: float = float(os.getenv('HYPERLIQUID_MIN_TRADE_USD', '100000'))
        self.min_liquidation_usd: float = float(os.getenv('HYPERLIQUID_MIN_LIQUIDATION_USD', '50000'))
        self.min_whale_activity_usd: float = float(os.getenv('HYPERLIQUID_MIN_WHALE_ACTIVITY_USD', '500000'))

        # Настройки уведомлений
        self.notify_whale_activity: bool = os.getenv('HYPERLIQUID_NOTIFY_WHALE_ACTIVITY', 'true').lower() == 'true'
        self.notify_liquidations: bool = os.getenv('HYPERLIQUID_NOTIFY_LIQUIDATIONS', 'true').lower() == 'true'

        logger.info(
            f"✅ [HYPERLIQUID] Конфигурация загружена: "
            f"API={'настроен' if self.api_url else 'не настроен'}, "
            f"min_whale=${self.min_whale_activity_usd:,.0f}, "
            f"min_liquidation=${self.min_liquidation_usd:,.0f}"
        )

    def is_configured(self) -> bool:
        """Проверка, настроен ли Hyperliquid"""
        return bool(self.api_url)

    def to_dict(self) -> dict:
        """Конвертация в словарь"""
        return {
            'api_url': self.api_url or 'not configured',
            'min_trade_usd': self.min_trade_usd,
            'min_liquidation_usd': self.min_liquidation_usd,
            'min_whale_activity_usd': self.min_whale_activity_usd,
            'notify_whale_activity': self.notify_whale_activity,
            'notify_liquidations': self.notify_liquidations,
        }

    def __repr__(self) -> str:
        """Строковое представление"""
        return (
            f"HyperliquidConfig("
            f"api_url={'configured' if self.api_url else 'not configured'}, "
            f"min_whale_activity_usd={self.min_whale_activity_usd}, "
            f"min_liquidation_usd={self.min_liquidation_usd}"
            f")"
        )
