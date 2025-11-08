# app/config/blockchain/chain_formatters.py
"""
Chain Formatters Module
Форматирование данных блокчейнов
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .chain_metadata import ChainMetadata

logger = logging.getLogger(__name__)


class ChainFormatters:
    """
    Форматирование данных блокчейнов
    
    Включает:
    - Форматирование сумм с символами валют
    - Форматирование адресов
    - Форматирование хэшей
    """
    
    def __init__(self, metadata: 'ChainMetadata'):
        """
        Инициализация форматтеров
        
        Args:
            metadata: Экземпляр ChainMetadata для получения символов
        """
        self._metadata = metadata
        
        logger.debug("Chain formatters initialized")
    
    def format_amount(
        self,
        chain: str,
        amount: float,
        decimals: int = 2,
        include_symbol: bool = True
    ) -> str:
        """
        Форматирование суммы с символом валюты
        
        Args:
            chain: Название блокчейна
            amount: Сумма
            decimals: Количество знаков после запятой
            include_symbol: Включать ли символ валюты
            
        Returns:
            Отформатированная строка
        """
        if amount is None:
            return "0.00"
        
        try:
            formatted_amount = f"{amount:,.{decimals}f}"
            
            if include_symbol:
                symbol = self._metadata.get_symbol(chain)
                return f"{formatted_amount} {symbol}"
            else:
                return formatted_amount
                
        except (ValueError, TypeError) as e:
            logger.error(f"Error formatting amount {amount}: {e}")
            return "0.00"
    
    def format_usd_amount(self, amount: float, decimals: int = 2) -> str:
        """
        Форматирование суммы в USD
        
        Args:
            amount: Сумма в USD
            decimals: Количество знаков после запятой
            
        Returns:
            Отформатированная строка с символом $
        """
        if amount is None:
            return "$0.00"
        
        try:
            formatted_amount = f"{amount:,.{decimals}f}"
            return f"${formatted_amount}"
        except (ValueError, TypeError) as e:
            logger.error(f"Error formatting USD amount {amount}: {e}")
            return "$0.00"
    
    def format_address(self, address: str, short: bool = True) -> str:
        """
        Форматирование адреса кошелька
        
        Args:
            address: Адрес кошелька
            short: Сокращенный формат (0x1234...5678)
            
        Returns:
            Отформатированный адрес
        """
        if not address:
            return "N/A"
        
        if not short:
            return address
        
        if len(address) <= 10:
            return address
        
        return f"{address[:6]}...{address[-4:]}"
    
    def format_hash(self, tx_hash: str, short: bool = True) -> str:
        """
        Форматирование хэша транзакции
        
        Args:
            tx_hash: Хэш транзакции
            short: Сокращенный формат
            
        Returns:
            Отформатированный хэш
        """
        if not tx_hash:
            return "N/A"
        
        if not short:
            return tx_hash
        
        if len(tx_hash) <= 10:
            return tx_hash
        
        return f"{tx_hash[:8]}...{tx_hash[-6:]}"
    
    def format_percentage(self, value: float, decimals: int = 2) -> str:
        """
        Форматирование процента
        
        Args:
            value: Значение (0.15 = 15%)
            decimals: Количество знаков после запятой
            
        Returns:
            Отформатированная строка с символом %
        """
        if value is None:
            return "0.00%"
        
        try:
            percentage = value * 100
            formatted = f"{percentage:.{decimals}f}"
            return f"{formatted}%"
        except (ValueError, TypeError) as e:
            logger.error(f"Error formatting percentage {value}: {e}")
            return "0.00%"
    
    def format_large_number(self, value: float) -> str:
        """
        Форматирование больших чисел с сокращениями (K, M, B)
        
        Args:
            value: Числовое значение
            
        Returns:
            Отформатированная строка (1.5K, 2.3M, 5.1B)
        """
        if value is None:
            return "0"
        
        try:
            abs_value = abs(value)
            sign = "-" if value < 0 else ""
            
            if abs_value >= 1_000_000_000:
                return f"{sign}{abs_value / 1_000_000_000:.1f}B"
            elif abs_value >= 1_000_000:
                return f"{sign}{abs_value / 1_000_000:.1f}M"
            elif abs_value >= 1_000:
                return f"{sign}{abs_value / 1_000:.1f}K"
            else:
                return f"{sign}{abs_value:.0f}"
        except (ValueError, TypeError) as e:
            logger.error(f"Error formatting large number {value}: {e}")
            return "0"