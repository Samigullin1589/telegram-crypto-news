# app/config/api_config.py
"""
API Configuration Module
Конфигурация API ключей и внешних сервисов
"""

import os
import logging
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class APIConfig:
    """
    Конфигурация API ключей для внешних сервисов
    Поддержка множественных провайдеров с fallback
    """
    
    def __init__(self):
        """Инициализация API конфигурации"""
        
        self.gemini_api_key = os.getenv('GEMINI_API_KEY', '')
        self.openai_api_key = os.getenv('OPENAI_API_KEY', '')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY', '')
        self.cheapvibecode_api_key = os.getenv('CHEAPVIBECODE_API_KEY', '')
        
        self.gemini_model = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
        self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.anthropic_model = os.getenv(
            'ANTHROPIC_MODEL',
            'claude-3-5-sonnet-20241022'
        )
        self.cheapvibecode_base_url = os.getenv(
            'CHEAPVIBECODE_BASE_URL',
            'https://cheapvibecode.ru/v1'
        ).rstrip('/')
        self.cheapvibecode_model = os.getenv(
            'CHEAPVIBECODE_MODEL',
            'qwen3.8-max'
        )
        
        self.ai_max_retries = self._get_int_env('AI_MAX_RETRIES', 3, minimum=1)
        self.ai_backoff_factor = self._get_float_env(
            'AI_BACKOFF_FACTOR',
            2.0,
            minimum=0.1
        )
        self.ai_timeout = self._get_float_env('AI_TIMEOUT', 60.0, minimum=1.0)
        self.ai_max_tokens = self._get_int_env(
            'AI_MAX_TOKENS',
            500,
            minimum=1
        )
        self.ai_translation_max_tokens = self._get_int_env(
            'AI_TRANSLATION_MAX_TOKENS',
            800,
            minimum=1
        )
        self.ai_temperature = self._get_float_env(
            'AI_TEMPERATURE',
            0.3,
            minimum=0.0,
            maximum=2.0
        )
        
        self.etherscan_api_key = os.getenv('ETHERSCAN_API_KEY', '')
        self.bscscan_api_key = os.getenv('BSCSCAN_API_KEY', '')
        self.polygonscan_api_key = os.getenv('POLYGONSCAN_API_KEY', '')
        self.arbiscan_api_key = os.getenv('ARBISCAN_API_KEY', '')
        self.basescan_api_key = os.getenv('BASESCAN_API_KEY', '')
        self.snowtrace_api_key = os.getenv('SNOWTRACE_API_KEY', '')
        self.optimism_etherscan_api_key = os.getenv('OPTIMISM_ETHERSCAN_API_KEY', '')
        self.ftmscan_api_key = os.getenv('FTMSCAN_API_KEY', '')
        
        self.helius_api_key = os.getenv('HELIUS_API_KEY', '')
        self.solscan_api_key = os.getenv('SOLSCAN_API_KEY', '')
        
        self.coingecko_api_key = os.getenv('COINGECKO_API_KEY', '')
        self.alchemy_api_key = os.getenv('ALCHEMY_API_KEY', '')
        self.coinmarketcap_api_key = os.getenv('COINMARKETCAP_API_KEY', '')
        self.cryptopanic_api_key = os.getenv('CRYPTOPANIC_API_KEY', '')
        self.newsapi_key = os.getenv('NEWSAPI_KEY', '')
        self.dexscreener_api_key = os.getenv('DEXSCREENER_API_KEY', '')
        self.birdeye_api_key = os.getenv('BIRDEYE_API_KEY', '')
        
        self.scanner_keys_map = {
            'ethereum': self.etherscan_api_key,
            'bsc': self.bscscan_api_key,
            'polygon': self.polygonscan_api_key,
            'arbitrum': self.arbiscan_api_key,
            'base': self.basescan_api_key,
            'avalanche': self.snowtrace_api_key,
            'optimism': self.optimism_etherscan_api_key,
            'fantom': self.ftmscan_api_key,
            'solana': self.helius_api_key or self.solscan_api_key
        }

    @staticmethod
    def _get_int_env(
        name: str,
        default: int,
        minimum: Optional[int] = None,
        maximum: Optional[int] = None
    ) -> int:
        try:
            value = int(os.getenv(name, str(default)))
        except (TypeError, ValueError):
            value = default

        if minimum is not None:
            value = max(minimum, value)
        if maximum is not None:
            value = min(maximum, value)
        return value

    @staticmethod
    def _get_float_env(
        name: str,
        default: float,
        minimum: Optional[float] = None,
        maximum: Optional[float] = None
    ) -> float:
        try:
            value = float(os.getenv(name, str(default)))
        except (TypeError, ValueError):
            value = default

        if minimum is not None:
            value = max(minimum, value)
        if maximum is not None:
            value = min(maximum, value)
        return value

    def has_cheapvibecode_provider(self) -> bool:
        """CheapVibeCode активен только с ключом и точным model ID."""
        return bool(self.cheapvibecode_api_key and self.cheapvibecode_model)
    
    def has_ai_provider(self) -> bool:
        """Проверка наличия хотя бы одного AI провайдера"""
        return bool(
            self.has_cheapvibecode_provider() or
            self.openai_api_key or
            self.anthropic_api_key or
            self.gemini_api_key
        )
    
    def get_ai_provider(self) -> Optional[str]:
        """
        Получение доступного AI провайдера
        
        Returns:
            Название провайдера или None
        """
        if self.has_cheapvibecode_provider():
            return 'cheapvibecode'
        if self.openai_api_key:
            return 'openai'
        elif self.anthropic_api_key:
            return 'anthropic'
        elif self.gemini_api_key:
            return 'gemini'
        return None
    
    def get_ai_config(self) -> Dict:
        """Получение конфигурации AI"""
        provider = self.get_ai_provider()
        
        config = {
            'provider': provider,
            'max_retries': self.ai_max_retries,
            'timeout': self.ai_timeout,
            'max_tokens': self.ai_max_tokens,
            'translation_max_tokens': self.ai_translation_max_tokens,
            'temperature': self.ai_temperature
        }
        
        if provider == 'cheapvibecode':
            config['api_key'] = self.cheapvibecode_api_key
            config['base_url'] = self.cheapvibecode_base_url
            config['model'] = self.cheapvibecode_model
        elif provider == 'openai':
            config['api_key'] = self.openai_api_key
            config['model'] = self.openai_model
        elif provider == 'anthropic':
            config['api_key'] = self.anthropic_api_key
            config['model'] = self.anthropic_model
        elif provider == 'gemini':
            config['api_key'] = self.gemini_api_key
            config['model'] = self.gemini_model
        
        return config
    
    def has_scanner_key(self, chain: str) -> bool:
        """
        Проверка наличия API ключа для блокчейн сканера
        
        Args:
            chain: Название блокчейна
            
        Returns:
            True если ключ настроен
        """
        return bool(self.scanner_keys_map.get(chain, ''))
    
    def get_scanner_key(self, chain: str) -> Optional[str]:
        """
        Получение API ключа для блокчейн сканера
        
        Args:
            chain: Название блокчейна
            
        Returns:
            API ключ или None
        """
        return self.scanner_keys_map.get(chain)
    
    def get_missing_scanner_keys(self, enabled_chains: List[str]) -> List[str]:
        """
        Получение списка блокчейнов без API ключей
        
        Args:
            enabled_chains: Список включенных блокчейнов
            
        Returns:
            Список блокчейнов без ключей
        """
        return [
            chain for chain in enabled_chains
            if not self.has_scanner_key(chain)
        ]
    
    def has_price_provider(self) -> bool:
        """Проверка наличия провайдера цен"""
        return bool(
            self.coingecko_api_key or
            self.coinmarketcap_api_key or
            self.alchemy_api_key
        )
    
    def get_configured_services(self) -> Dict[str, bool]:
        """Получение статуса всех сервисов"""
        return {
            'ai': {
                'cheapvibecode': self.has_cheapvibecode_provider(),
                'openai': bool(self.openai_api_key),
                'anthropic': bool(self.anthropic_api_key),
                'gemini': bool(self.gemini_api_key)
            },
            'scanners': {
                chain: bool(key)
                for chain, key in self.scanner_keys_map.items()
            },
            'prices': {
                'coingecko': bool(self.coingecko_api_key),
                'coinmarketcap': bool(self.coinmarketcap_api_key),
                'alchemy': bool(self.alchemy_api_key)
            },
            'news': {
                'cryptopanic': bool(self.cryptopanic_api_key),
                'newsapi': bool(self.newsapi_key)
            },
            'dex': {
                'dexscreener': bool(self.dexscreener_api_key),
                'birdeye': bool(self.birdeye_api_key)
            }
        }
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь (без секретов)"""
        return {
            'ai_provider': self.get_ai_provider(),
            'has_ai': self.has_ai_provider(),
            'has_price_provider': self.has_price_provider(),
            'configured_services': self.get_configured_services()
        }