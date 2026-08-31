"""
Database Configuration Loader
Загрузка конфигурации из различных источников
"""

import logging
from dataclasses import fields
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..database_config import DatabaseConfig

logger = logging.getLogger(__name__)


class DatabaseConfigLoader:
    """Загрузчик конфигурации из различных источников"""
    
    @staticmethod
    def from_env(prefix: str = "DATABASE_") -> 'DatabaseConfig':
        """
        Создание конфигурации из переменных окружения
        
        Args:
            prefix: Префикс для переменных окружения
            
        Returns:
            Инстанс DatabaseConfig
        """
        from ..database_config import DatabaseConfig
        from .loader import DatabaseConfigLoader as BaseLoader, EnvironmentLoader
        
        logger.info(f"Loading DatabaseConfig from environment (prefix: {prefix})")
        
        # Загружаем базовые параметры через loader
        loader = BaseLoader(prefix)
        base_config = loader.load_from_env()
        
        # Загружаем дополнительные параметры
        env_loader = EnvironmentLoader(prefix)
        
        # Собираем все параметры
        config_dict = {
            field.name: getattr(base_config, field.name)
            for field in fields(base_config)
        }
        
        # Добавляем расширенные параметры
        config_dict.update({
            'enable_manager': env_loader.get_bool('ENABLE_MANAGER', True),
            'auto_initialize': env_loader.get_bool('AUTO_INITIALIZE', False),
            'enable_health_checks': env_loader.get_bool('ENABLE_HEALTH_CHECKS', True),
            'health_check_interval_seconds': env_loader.get_int(
                'HEALTH_CHECK_INTERVAL', 300, min_value=30
            ),
            'enable_auto_vacuum': env_loader.get_bool('ENABLE_AUTO_VACUUM', True),
            'enable_auto_analyze': env_loader.get_bool('ENABLE_AUTO_ANALYZE', True),
            'enable_auto_backup': env_loader.get_bool('ENABLE_AUTO_BACKUP', False),
            'backup_retention_days': env_loader.get_int(
                'BACKUP_RETENTION_DAYS', 7, min_value=1
            ),
            'enable_query_logging': env_loader.get_bool('ENABLE_QUERY_LOGGING', False),
            'enable_performance_tracking': env_loader.get_bool(
                'ENABLE_PERFORMANCE_TRACKING', True
            ),
            'enable_connection_pooling': env_loader.get_bool(
                'ENABLE_CONNECTION_POOLING', True
            )
        })
        
        config = DatabaseConfig(**config_dict)
        
        logger.info("DatabaseConfig loaded from environment successfully")
        
        return config
    
    @staticmethod
    def from_dict(config_dict: Dict[str, Any]) -> 'DatabaseConfig':
        """
        Создание конфигурации из словаря
        
        Args:
            config_dict: Словарь с параметрами конфигурации
            
        Returns:
            Инстанс DatabaseConfig
        """
        from ..database_config import DatabaseConfig
        
        logger.info("Loading DatabaseConfig from dict")
        
        config = DatabaseConfig(**config_dict)
        
        logger.info("DatabaseConfig loaded from dict successfully")
        
        return config
    
    @staticmethod
    def from_url(
        url: str,
        **kwargs
    ) -> 'DatabaseConfig':
        """
        Создание конфигурации из URL подключения
        
        Args:
            url: URL подключения к БД
            **kwargs: Дополнительные параметры
            
        Returns:
            Инстанс DatabaseConfig
        """
        from ..database_config import DatabaseConfig
        from .database_base import DatabaseConfigBase
        
        logger.info(f"Loading DatabaseConfig from URL")
        
        # Парсим URL через базовый класс
        base_config = DatabaseConfigBase.from_url(url)
        
        # Собираем параметры
        config_dict = {
            field.name: getattr(base_config, field.name)
            for field in fields(base_config)
        }
        config_dict.update(kwargs)
        
        config = DatabaseConfig(**config_dict)
        
        logger.info("DatabaseConfig loaded from URL successfully")
        
        return config
    
    @staticmethod
    def from_file(
        filepath: str,
        format: Optional[str] = None
    ) -> 'DatabaseConfig':
        """
        Загрузка конфигурации из файла
        
        Args:
            filepath: Путь к файлу
            format: Формат файла ('json' или 'yaml'), auto-detect если None
            
        Returns:
            Инстанс DatabaseConfig
        """
        from ..database_config import DatabaseConfig
        import json
        
        logger.info(f"Loading DatabaseConfig from file: {filepath}")
        
        # Auto-detect format
        if format is None:
            if filepath.endswith('.json'):
                format = 'json'
            elif filepath.endswith(('.yaml', '.yml')):
                format = 'yaml'
            else:
                raise ValueError(f"Cannot auto-detect format for {filepath}")
        
        format = format.lower()
        
        # Читаем файл
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Парсим содержимое
        if format == 'json':
            config_dict = json.loads(content)
        elif format == 'yaml':
            try:
                import yaml
                config_dict = yaml.safe_load(content)
            except ImportError:
                raise ImportError("PyYAML is required for YAML format")
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        config = DatabaseConfig(**config_dict)
        
        logger.info(f"DatabaseConfig loaded from file successfully")
        
        return config


__all__ = ['DatabaseConfigLoader']