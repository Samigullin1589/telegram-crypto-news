# app/config/validators.py
"""
Configuration validators
"""

from typing import List, Tuple


class ConfigValidator:
    """Валидация конфигурации"""
    
    @staticmethod
    def validate_memory_limits(max_memory_mb: int) -> Tuple[List[str], List[str]]:
        """Валидация лимитов памяти"""
        errors = []
        warnings = []
        
        if max_memory_mb < 100:
            errors.append('MAX_MEMORY_MB слишком мало (минимум 100MB)')
        
        if max_memory_mb > 512:
            warnings.append('MAX_MEMORY_MB больше 512MB - может не подойти для Render Free Tier')
        
        return errors, warnings
    
    @staticmethod
    def validate_chains(enabled_chains: List[str], rpc_urls: dict) -> Tuple[List[str], List[str]]:
        """Валидация блокчейнов"""
        errors = []
        warnings = []
        
        if not enabled_chains:
            errors.append('Нет активных блокчейнов (ENABLED_CHAINS)')
        
        for chain in enabled_chains:
            if chain not in rpc_urls:
                errors.append(f'Нет RPC URL для chain: {chain}')
        
        return errors, warnings
    
    @staticmethod
    def validate_whale_config(min_usd: float, posts_per_hour: int) -> Tuple[List[str], List[str]]:
        """Валидация конфигурации whale detection"""
        errors = []
        warnings = []
        
        if min_usd < 1000:
            warnings.append('WHALE_MIN_VALUE_USD очень низкий - может быть много ложных срабатываний')
        
        if posts_per_hour > 10:
            warnings.append('POSTS_PER_HOUR_CAP высокий - может спамить канал')
        
        return errors, warnings
    
    @staticmethod
    def validate_news_config(news_enabled: bool, ai_keys: dict) -> Tuple[List[str], List[str]]:
        """Валидация конфигурации новостей"""
        errors = []
        warnings = []
        
        if news_enabled and not any(ai_keys.values()):
            warnings.append('News enabled но нет AI ключей - AI анализ будет отключен')
        
        return errors, warnings
    
    @staticmethod
    def validate_trading_config(trading_enabled: bool, assets: List[str]) -> Tuple[List[str], List[str]]:
        """Валидация конфигурации трейдинга"""
        errors = []
        warnings = []
        
        if trading_enabled and len(assets) > 20:
            warnings.append('Слишком много активов для мониторинга - может быть медленно')
        
        return errors, warnings
    
    @staticmethod
    def validate_discovery_config(
        min_age_days: int,
        min_volume: float,
        min_market_cap: float
    ) -> Tuple[List[str], List[str]]:
        """Валидация конфигурации discovery"""
        errors = []
        warnings = []
        
        if min_age_days < 1:
            errors.append('MIN_TOKEN_AGE_DAYS должен быть >= 1')
        
        if min_volume < 1000:
            warnings.append('DISCOVERY_MIN_VOLUME_USD очень низкий - может быть много шит-коинов')
        
        if min_market_cap < 100000:
            warnings.append('DISCOVERY_MIN_MARKET_CAP_USD очень низкий - может быть много шит-коинов')
        
        return errors, warnings