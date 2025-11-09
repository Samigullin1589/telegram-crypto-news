"""
Database Configuration Serialization
Сериализация и десериализация конфигурации
"""

import logging
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .database_config_core import DatabaseConfig

logger = logging.getLogger(__name__)


class DatabaseConfigSerialization:
    """Миксин для сериализации конфигурации"""
    
    def to_dict(self: 'DatabaseConfig', mask_sensitive: bool = True) -> Dict[str, Any]:
        """
        Конвертация конфигурации в словарь
        
        Args:
            mask_sensitive: Маскировать чувствительные поля
            
        Returns:
            Словарь с конфигурацией
        """
        # Получаем базовый словарь
        from .database.base import DatabaseConfigBase
        base_dict = DatabaseConfigBase.to_dict(self, mask_sensitive)
        
        # Добавляем расширенные параметры
        base_dict.update({
            'enable_manager': self.enable_manager,
            'auto_initialize': self.auto_initialize,
            'enable_health_checks': self.enable_health_checks,
            'health_check_interval_seconds': self.health_check_interval_seconds,
            'enable_auto_vacuum': self.enable_auto_vacuum,
            'enable_auto_analyze': self.enable_auto_analyze,
            'enable_auto_backup': self.enable_auto_backup,
            'backup_retention_days': self.backup_retention_days,
            'enable_query_logging': self.enable_query_logging,
            'enable_performance_tracking': self.enable_performance_tracking,
            'enable_connection_pooling': self.enable_connection_pooling,
            'is_initialized': self._initialized
        })
        
        return base_dict
    
    def to_json(self: 'DatabaseConfig', indent: int = 2, mask_sensitive: bool = True) -> str:
        """
        Конвертация конфигурации в JSON строку
        
        Args:
            indent: Отступы для форматирования
            mask_sensitive: Маскировать чувствительные поля
            
        Returns:
            JSON строка
        """
        import json
        
        config_dict = self.to_dict(mask_sensitive=mask_sensitive)
        
        # Конвертируем enum значения
        def convert_enums(obj):
            if hasattr(obj, 'value'):
                return obj.value
            elif isinstance(obj, dict):
                return {k: convert_enums(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_enums(item) for item in obj]
            return obj
        
        config_dict = convert_enums(config_dict)
        
        return json.dumps(config_dict, indent=indent, default=str)
    
    def to_yaml(self: 'DatabaseConfig', mask_sensitive: bool = True) -> str:
        """
        Конвертация конфигурации в YAML строку
        
        Args:
            mask_sensitive: Маскировать чувствительные поля
            
        Returns:
            YAML строка
        """
        try:
            import yaml
            
            config_dict = self.to_dict(mask_sensitive=mask_sensitive)
            
            # Конвертируем enum значения
            def convert_enums(obj):
                if hasattr(obj, 'value'):
                    return obj.value
                elif isinstance(obj, dict):
                    return {k: convert_enums(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_enums(item) for item in obj]
                return obj
            
            config_dict = convert_enums(config_dict)
            
            return yaml.dump(config_dict, default_flow_style=False, sort_keys=False)
            
        except ImportError:
            logger.warning("PyYAML not installed, falling back to JSON")
            return self.to_json(mask_sensitive=mask_sensitive)
    
    def export_to_file(
        self: 'DatabaseConfig',
        filepath: str,
        format: str = 'json',
        mask_sensitive: bool = True
    ) -> None:
        """
        Экспорт конфигурации в файл
        
        Args:
            filepath: Путь к файлу
            format: Формат файла ('json' или 'yaml')
            mask_sensitive: Маскировать чувствительные поля
        """
        format = format.lower()
        
        if format == 'json':
            content = self.to_json(mask_sensitive=mask_sensitive)
        elif format == 'yaml':
            content = self.to_yaml(mask_sensitive=mask_sensitive)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Configuration exported to {filepath} ({format})")


__all__ = ['DatabaseConfigSerialization']