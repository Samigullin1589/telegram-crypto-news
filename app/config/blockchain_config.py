# app/config/blockchain_config.py
"""
Blockchain Configuration Module v2.0
Конфигурация блокчейнов, whale мониторинга и параметров сетей
"""

import os
import logging
from typing import Dict, List, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)


class BlockchainConfig:
    """
    Конфигурация блокчейнов и параметров мониторинга
    
    Управляет:
    - Списком активных блокчейнов
    - Порогами для whale транзакций
    - URL эксплореров
    - Нативными символами валют
    - Визуальными параметрами (цвета, emoji)
    """
    
    def __init__(self):
        """Инициализация конфигурации блокчейнов"""
        logger.debug("Инициализация BlockchainConfig...")
        
        # Загрузка списка активных блокчейнов
        self.enabled_chains = self._parse_enabled_chains()
        
        # Глобальный минимальный порог в USD
        self.min_usd = float(os.getenv('MIN_USD', '100000'))
        
        # Инициализация всех конфигураций
        self._initialize_whale_thresholds()
        self._initialize_blockchain_explorers()
        self._initialize_chain_metadata()
        
        logger.info(
            f"✅ [BLOCKCHAIN] Инициализировано chains: {len(self.enabled_chains)} "
            f"({', '.join(self.enabled_chains)})"
        )
    
    # ========================================================================
    # ИНИЦИАЛИЗАЦИЯ
    # ========================================================================
    
    @staticmethod
    def _parse_enabled_chains() -> List[str]:
        """
        Парсинг списка включенных блокчейнов из переменных окружения
        
        Returns:
            Список названий блокчейнов в нижнем регистре
        """
        chains_str = os.getenv(
            'ENABLED_CHAINS',
            'ethereum,solana,bsc,polygon,arbitrum,base,optimism,avalanche'
        )
        
        chains = [chain.strip().lower() for chain in chains_str.split(',') if chain.strip()]
        
        logger.debug(f"Parsed enabled chains: {chains}")
        return chains
    
    def _initialize_whale_thresholds(self) -> None:
        """
        Инициализация порогов для whale транзакций
        
        Каждый блокчейн имеет свои пороги:
        - min_native_value: Минимум нативной валюты для обработки
        - min_usd_value: Минимальная сумма в USD для обработки
        - whale_threshold_usd: Порог для обычного whale
        - mega_whale_threshold_usd: Порог для mega whale
        """
        self.whale_thresholds: Dict[str, Dict[str, float]] = {
            'ethereum': {
                'min_native_value': 50.0,
                'min_usd_value': 100000.0,
                'whale_threshold_usd': 1000000.0,
                'mega_whale_threshold_usd': 10000000.0
            },
            'bsc': {
                'min_native_value': 100.0,
                'min_usd_value': 50000.0,
                'whale_threshold_usd': 500000.0,
                'mega_whale_threshold_usd': 5000000.0
            },
            'polygon': {
                'min_native_value': 50000.0,
                'min_usd_value': 25000.0,
                'whale_threshold_usd': 250000.0,
                'mega_whale_threshold_usd': 2500000.0
            },
            'arbitrum': {
                'min_native_value': 50.0,
                'min_usd_value': 100000.0,
                'whale_threshold_usd': 1000000.0,
                'mega_whale_threshold_usd': 10000000.0
            },
            'optimism': {
                'min_native_value': 50.0,
                'min_usd_value': 100000.0,
                'whale_threshold_usd': 1000000.0,
                'mega_whale_threshold_usd': 10000000.0
            },
            'base': {
                'min_native_value': 50.0,
                'min_usd_value': 100000.0,
                'whale_threshold_usd': 1000000.0,
                'mega_whale_threshold_usd': 10000000.0
            },
            'avalanche': {
                'min_native_value': 500.0,
                'min_usd_value': 15000.0,
                'whale_threshold_usd': 150000.0,
                'mega_whale_threshold_usd': 1500000.0
            },
            'solana': {
                'min_native_value': 100.0,
                'min_usd_value': 10000.0,
                'whale_threshold_usd': 100000.0,
                'mega_whale_threshold_usd': 1000000.0
            },
            'fantom': {
                'min_native_value': 10000.0,
                'min_usd_value': 5000.0,
                'whale_threshold_usd': 50000.0,
                'mega_whale_threshold_usd': 500000.0
            },
            'tron': {
                'min_native_value': 1000000.0,
                'min_usd_value': 100000.0,
                'whale_threshold_usd': 1000000.0,
                'mega_whale_threshold_usd': 10000000.0
            }
        }
        
        logger.debug(f"Whale thresholds initialized for {len(self.whale_thresholds)} chains")
    
    def _initialize_blockchain_explorers(self) -> None:
        """
        Инициализация URL блокчейн эксплореров
        
        Эксплореры используются для создания ссылок на транзакции и адреса
        """
        self.blockchain_explorers: Dict[str, str] = {
            'ethereum': 'https://etherscan.io',
            'bsc': 'https://bscscan.com',
            'polygon': 'https://polygonscan.com',
            'arbitrum': 'https://arbiscan.io',
            'optimism': 'https://optimistic.etherscan.io',
            'base': 'https://basescan.org',
            'avalanche': 'https://snowtrace.io',
            'solana': 'https://solscan.io',
            'fantom': 'https://ftmscan.com',
            'tron': 'https://tronscan.org'
        }
        
        logger.debug(f"Blockchain explorers initialized for {len(self.blockchain_explorers)} chains")
    
    def _initialize_chain_metadata(self) -> None:
        """
        Инициализация метаданных блокчейнов
        
        Включает:
        - Нативные символы валют
        - Полные названия сетей
        - Цвета для UI
        - Emoji для визуального отображения
        """
        # Нативные символы
        self.chain_native_symbols: Dict[str, str] = {
            'ethereum': 'ETH',
            'bsc': 'BNB',
            'polygon': 'MATIC',
            'arbitrum': 'ETH',
            'optimism': 'ETH',
            'base': 'ETH',
            'avalanche': 'AVAX',
            'solana': 'SOL',
            'fantom': 'FTM',
            'tron': 'TRX'
        }
        
        # Полные названия
        self.chain_names: Dict[str, str] = {
            'ethereum': 'Ethereum',
            'bsc': 'BNB Chain',
            'polygon': 'Polygon',
            'arbitrum': 'Arbitrum',
            'optimism': 'Optimism',
            'base': 'Base',
            'avalanche': 'Avalanche',
            'solana': 'Solana',
            'fantom': 'Fantom',
            'tron': 'Tron'
        }
        
        # Цвета (для графиков и UI)
        self.chain_colors: Dict[str, str] = {
            'ethereum': '#627EEA',
            'bsc': '#F3BA2F',
            'polygon': '#8247E5',
            'arbitrum': '#28A0F0',
            'optimism': '#FF0420',
            'base': '#0052FF',
            'avalanche': '#E84142',
            'solana': '#14F195',
            'fantom': '#1969FF',
            'tron': '#FF0013'
        }
        
        # Emoji для Telegram
        self.chain_emojis: Dict[str, str] = {
            'ethereum': '🔷',
            'bsc': '🟡',
            'polygon': '🟣',
            'arbitrum': '🔵',
            'optimism': '🔴',
            'base': '🔵',
            'avalanche': '🔺',
            'solana': '🌅',
            'fantom': '👻',
            'tron': '🔶'
        }
        
        logger.debug("Chain metadata initialized")
    
    # ========================================================================
    # ПРОВЕРКА БЛОКЧЕЙНОВ
    # ========================================================================
    
    def is_chain_enabled(self, chain: str) -> bool:
        """
        Проверка включен ли блокчейн
        
        Args:
            chain: Название блокчейна
            
        Returns:
            True если блокчейн включен
        """
        return chain.lower() in self.enabled_chains
    
    def is_chain_supported(self, chain: str) -> bool:
        """
        Проверка поддерживается ли блокчейн системой
        
        Args:
            chain: Название блокчейна
            
        Returns:
            True если блокчейн поддерживается (есть в конфигурации)
        """
        return chain.lower() in self.whale_thresholds
    
    def get_all_supported_chains(self) -> List[str]:
        """
        Получение списка всех поддерживаемых блокчейнов
        
        Returns:
            Список названий блокчейнов
        """
        return list(self.whale_thresholds.keys())
    
    # ========================================================================
    # WHALE THRESHOLDS
    # ========================================================================
    
    def get_whale_threshold(self, chain: str) -> Dict[str, float]:
        """
        Получение порогов для блокчейна
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Словарь с порогами:
            - min_native_value: минимум нативной валюты
            - min_usd_value: минимум в USD
            - whale_threshold_usd: порог whale в USD
            - mega_whale_threshold_usd: порог mega whale в USD
        """
        chain_lower = chain.lower()
        
        # Возвращаем настройки для конкретного chain или дефолтные
        return self.whale_thresholds.get(chain_lower, {
            'min_native_value': 10.0,
            'min_usd_value': 10000.0,
            'whale_threshold_usd': 100000.0,
            'mega_whale_threshold_usd': 1000000.0
        })
    
    def get_min_usd_value(self, chain: str) -> float:
        """
        Получение минимального порога в USD для блокчейна
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Минимальная сумма в USD
        """
        thresholds = self.get_whale_threshold(chain)
        return thresholds.get('min_usd_value', self.min_usd)
    
    def get_min_native_value(self, chain: str) -> float:
        """
        Получение минимального количества нативной валюты
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Минимальное количество нативной валюты
        """
        thresholds = self.get_whale_threshold(chain)
        return thresholds.get('min_native_value', 1.0)
    
    # ========================================================================
    # КЛАССИФИКАЦИЯ ТРАНЗАКЦИЙ
    # ========================================================================
    
    def is_whale_transaction(self, chain: str, usd_value: float) -> bool:
        """
        Проверка является ли транзакция whale
        
        Args:
            chain: Название блокчейна
            usd_value: Сумма транзакции в USD
            
        Returns:
            True если транзакция превышает whale порог
        """
        thresholds = self.get_whale_threshold(chain)
        whale_threshold = thresholds.get('whale_threshold_usd', 1000000.0)
        return usd_value >= whale_threshold
    
    def is_mega_whale_transaction(self, chain: str, usd_value: float) -> bool:
        """
        Проверка является ли транзакция mega whale
        
        Args:
            chain: Название блокчейна
            usd_value: Сумма транзакции в USD
            
        Returns:
            True если транзакция превышает mega whale порог
        """
        thresholds = self.get_whale_threshold(chain)
        mega_whale_threshold = thresholds.get('mega_whale_threshold_usd', 10000000.0)
        return usd_value >= mega_whale_threshold
    
    def get_transaction_category(self, chain: str, usd_value: float) -> str:
        """
        Определение категории транзакции по сумме
        
        Args:
            chain: Название блокчейна
            usd_value: Сумма транзакции в USD
            
        Returns:
            Категория: 'mega_whale', 'whale', 'large', или 'normal'
        """
        if self.is_mega_whale_transaction(chain, usd_value):
            return 'mega_whale'
        elif self.is_whale_transaction(chain, usd_value):
            return 'whale'
        elif usd_value >= self.get_min_usd_value(chain):
            return 'large'
        else:
            return 'normal'
    
    def should_process_transaction(self, chain: str, usd_value: float) -> bool:
        """
        Проверка нужно ли обрабатывать транзакцию
        
        Args:
            chain: Название блокчейна
            usd_value: Сумма транзакции в USD
            
        Returns:
            True если транзакция превышает минимальный порог
        """
        min_usd = self.get_min_usd_value(chain)
        return usd_value >= min_usd
    
    # ========================================================================
    # EXPLORERS
    # ========================================================================
    
    def get_explorer_url(
        self,
        chain: str,
        address: Optional[str] = None,
        tx_hash: Optional[str] = None
    ) -> str:
        """
        Получение URL эксплорера
        
        Args:
            chain: Название блокчейна
            address: Адрес кошелька (опционально)
            tx_hash: Хэш транзакции (опционально)
            
        Returns:
            URL эксплорера с параметрами или пустая строка
        """
        chain_lower = chain.lower()
        base_url = self.blockchain_explorers.get(chain_lower, '')
        
        if not base_url:
            logger.warning(f"Explorer URL not found for chain: {chain}")
            return ''
        
        # Формирование URL в зависимости от параметров
        if tx_hash:
            return self._format_transaction_url(chain_lower, base_url, tx_hash)
        elif address:
            return self._format_address_url(chain_lower, base_url, address)
        else:
            return base_url
    
    def _format_transaction_url(self, chain: str, base_url: str, tx_hash: str) -> str:
        """
        Форматирование URL транзакции
        
        Args:
            chain: Название блокчейна
            base_url: Базовый URL эксплорера
            tx_hash: Хэш транзакции
            
        Returns:
            Полный URL транзакции
        """
        # Solana использует другой формат URL
        if chain == 'solana':
            return f"{base_url}/tx/{tx_hash}"
        # Tron тоже может иметь специфичный формат
        elif chain == 'tron':
            return f"{base_url}/#/transaction/{tx_hash}"
        else:
            # Стандартный формат для EVM chains
            return f"{base_url}/tx/{tx_hash}"
    
    def _format_address_url(self, chain: str, base_url: str, address: str) -> str:
        """
        Форматирование URL адреса
        
        Args:
            chain: Название блокчейна
            base_url: Базовый URL эксплорера
            address: Адрес кошелька
            
        Returns:
            Полный URL адреса
        """
        # Tron может использовать другой формат
        if chain == 'tron':
            return f"{base_url}/#/address/{address}"
        else:
            # Стандартный формат
            return f"{base_url}/address/{address}"
    
    # ========================================================================
    # МЕТАДАННЫЕ
    # ========================================================================
    
    def get_chain_symbol(self, chain: str) -> str:
        """
        Получение нативного символа блокчейна
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Символ валюты (ETH, BNB, SOL и т.д.)
        """
        chain_lower = chain.lower()
        return self.chain_native_symbols.get(chain_lower, 'UNKNOWN')
    
    def get_chain_name(self, chain: str) -> str:
        """
        Получение полного имени блокчейна
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Полное название (Ethereum, BNB Chain и т.д.)
        """
        chain_lower = chain.lower()
        return self.chain_names.get(chain_lower, chain.capitalize())
    
    def get_chain_emoji(self, chain: str) -> str:
        """
        Получение emoji блокчейна
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Emoji для визуального отображения
        """
        chain_lower = chain.lower()
        return self.chain_emojis.get(chain_lower, '⛓️')
    
    def get_chain_color(self, chain: str) -> str:
        """
        Получение цвета блокчейна
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Hex код цвета
        """
        chain_lower = chain.lower()
        return self.chain_colors.get(chain_lower, '#000000')
    
    # ========================================================================
    # ДОПОЛНИТЕЛЬНЫЕ МЕТОДЫ
    # ========================================================================
    
    def get_chain_info(self, chain: str) -> Dict[str, Any]:
        """
        Получение полной информации о блокчейне
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Словарь с полной информацией о блокчейне
        """
        chain_lower = chain.lower()
        thresholds = self.get_whale_threshold(chain_lower)
        
        return {
            'chain': chain_lower,
            'name': self.get_chain_name(chain_lower),
            'symbol': self.get_chain_symbol(chain_lower),
            'emoji': self.get_chain_emoji(chain_lower),
            'color': self.get_chain_color(chain_lower),
            'explorer': self.blockchain_explorers.get(chain_lower, ''),
            'enabled': self.is_chain_enabled(chain_lower),
            'thresholds': thresholds
        }
    
    def get_enabled_chains_info(self) -> List[Dict[str, Any]]:
        """
        Получение информации о всех включенных блокчейнах
        
        Returns:
            Список словарей с информацией о каждом включенном блокчейне
        """
        return [
            self.get_chain_info(chain)
            for chain in self.enabled_chains
        ]
    
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
        formatted_amount = f"{amount:,.{decimals}f}"
        
        if include_symbol:
            symbol = self.get_chain_symbol(chain)
            return f"{formatted_amount} {symbol}"
        else:
            return formatted_amount
    
    # ========================================================================
    # СЕРИАЛИЗАЦИЯ
    # ========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Конвертация конфигурации в словарь
        
        Returns:
            Словарь со всеми настройками
        """
        return {
            'enabled_chains': self.enabled_chains,
            'min_usd': self.min_usd,
            'total_supported': len(self.whale_thresholds),
            'thresholds': {
                chain: thresh
                for chain, thresh in self.whale_thresholds.items()
                if chain in self.enabled_chains
            },
            'explorers': {
                chain: url
                for chain, url in self.blockchain_explorers.items()
                if chain in self.enabled_chains
            },
            'metadata': {
                chain: {
                    'name': self.get_chain_name(chain),
                    'symbol': self.get_chain_symbol(chain),
                    'emoji': self.get_chain_emoji(chain),
                    'color': self.get_chain_color(chain)
                }
                for chain in self.enabled_chains
            }
        }
    
    def __repr__(self) -> str:
        """Строковое представление конфигурации"""
        return (
            f"BlockchainConfig("
            f"enabled={len(self.enabled_chains)}, "
            f"supported={len(self.whale_thresholds)}, "
            f"chains={', '.join(self.enabled_chains)}"
            f")"
        )