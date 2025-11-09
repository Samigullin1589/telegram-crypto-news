"""
Multi-Database Configuration Management
Управление конфигурациями для множественных баз данных
"""

import logging
from typing import Dict, List, Optional, Any

from .database_base import DatabaseConfigBase
from .base_validators import validate_multiple_configs, check_multiple_configs_compatibility
from .exceptions import DatabaseConfigError

logger = logging.getLogger(__name__)


# ============================================================================
# MULTI DATABASE CONFIG
# ============================================================================

class MultiDatabaseConfig:
    """
    Менеджер конфигураций для множественных баз данных
    
    Используется когда приложение работает с несколькими БД одновременно.
    Позволяет управлять несколькими конфигурациями централизованно.
    
    Features:
        - Хранение нескольких конфигураций с именами
        - Конфигурация по умолчанию
        - Валидация всех конфигураций
        - Проверка совместимости
        - Группировка конфигураций
    
    Example:
        >>> multi = MultiDatabaseConfig()
        >>> 
        >>> # Добавление конфигураций
        >>> multi.add('primary', create_postgresql_config(...))
        >>> multi.add('cache', create_sqlite_config(...))
        >>> multi.add('analytics', create_postgresql_config(...))
        >>> 
        >>> # Получение конфигурации
        >>> primary = multi.get('primary')
        >>> 
        >>> # Валидация всех
        >>> results = multi.validate_all()
    """
    
    def __init__(self):
        """Инициализация менеджера конфигураций"""
        self._configs: Dict[str, DatabaseConfigBase] = {}
        self._default_name: Optional[str] = None
        self._groups: Dict[str, List[str]] = {}
        self._tags: Dict[str, List[str]] = {}
        
        logger.debug("MultiDatabaseConfig initialized")
    
    # ========================================================================
    # CONFIG MANAGEMENT
    # ========================================================================
    
    def add(
        self,
        name: str,
        config: DatabaseConfigBase,
        set_as_default: bool = False,
        group: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> None:
        """
        Добавление конфигурации
        
        Args:
            name: Имя конфигурации
            config: Конфигурация БД
            set_as_default: Установить как конфигурацию по умолчанию
            group: Группа конфигурации (например, 'production', 'development')
            tags: Теги для конфигурации
        """
        if name in self._configs:
            logger.warning(f"Overwriting existing config: {name}")
        
        self._configs[name] = config
        logger.info(f"Added database config: {name}")
        
        # Устанавливаем как default
        if set_as_default or self._default_name is None:
            self._default_name = name
            logger.info(f"Set default database config: {name}")
        
        # Добавляем в группу
        if group:
            if group not in self._groups:
                self._groups[group] = []
            self._groups[group].append(name)
            logger.debug(f"Added config '{name}' to group '{group}'")
        
        # Добавляем теги
        if tags:
            self._tags[name] = tags
            logger.debug(f"Added tags to config '{name}': {tags}")
    
    def get(self, name: Optional[str] = None) -> DatabaseConfigBase:
        """
        Получение конфигурации по имени
        
        Args:
            name: Имя конфигурации (None = default)
            
        Returns:
            Конфигурация БД
            
        Raises:
            KeyError: Если конфигурация не найдена
        """
        if name is None:
            if self._default_name is None:
                raise KeyError("No default database config set")
            name = self._default_name
        
        if name not in self._configs:
            available = ', '.join(self._configs.keys())
            raise KeyError(
                f"Database config not found: {name}. Available: {available}"
            )
        
        return self._configs[name]
    
    def remove(self, name: str) -> None:
        """
        Удаление конфигурации
        
        Args:
            name: Имя конфигурации для удаления
        """
        if name not in self._configs:
            logger.warning(f"Config not found: {name}")
            return
        
        del self._configs[name]
        logger.info(f"Removed database config: {name}")
        
        # Обновляем default
        if self._default_name == name:
            self._default_name = None
            logger.warning("Removed default config, no default set now")
        
        # Удаляем из групп
        for group, configs in self._groups.items():
            if name in configs:
                configs.remove(name)
        
        # Удаляем теги
        if name in self._tags:
            del self._tags[name]
    
    def rename(self, old_name: str, new_name: str) -> None:
        """
        Переименование конфигурации
        
        Args:
            old_name: Старое имя
            new_name: Новое имя
        """
        if old_name not in self._configs:
            raise KeyError(f"Config not found: {old_name}")
        
        if new_name in self._configs:
            raise KeyError(f"Config already exists: {new_name}")
        
        config = self._configs[old_name]
        del self._configs[old_name]
        self._configs[new_name] = config
        
        # Обновляем default
        if self._default_name == old_name:
            self._default_name = new_name
        
        # Обновляем группы
        for group, configs in self._groups.items():
            if old_name in configs:
                configs.remove(old_name)
                configs.append(new_name)
        
        # Обновляем теги
        if old_name in self._tags:
            self._tags[new_name] = self._tags[old_name]
            del self._tags[old_name]
        
        logger.info(f"Renamed config: {old_name} -> {new_name}")
    
    # ========================================================================
    # QUERY OPERATIONS
    # ========================================================================
    
    def list_configs(self) -> List[str]:
        """
        Получение списка всех конфигураций
        
        Returns:
            Список имён конфигураций
        """
        return list(self._configs.keys())
    
    def get_all(self) -> Dict[str, DatabaseConfigBase]:
        """
        Получение всех конфигураций
        
        Returns:
            Словарь всех конфигураций
        """
        return self._configs.copy()
    
    def get_by_group(self, group: str) -> Dict[str, DatabaseConfigBase]:
        """
        Получение конфигураций по группе
        
        Args:
            group: Имя группы
            
        Returns:
            Словарь конфигураций в группе
        """
        if group not in self._groups:
            return {}
        
        return {
            name: self._configs[name]
            for name in self._groups[group]
            if name in self._configs
        }
    
    def get_by_tag(self, tag: str) -> Dict[str, DatabaseConfigBase]:
        """
        Получение конфигураций по тегу
        
        Args:
            tag: Тег для поиска
            
        Returns:
            Словарь конфигураций с указанным тегом
        """
        return {
            name: config
            for name, config in self._configs.items()
            if name in self._tags and tag in self._tags[name]
        }
    
    def get_default(self) -> Optional[DatabaseConfigBase]:
        """
        Получение конфигурации по умолчанию
        
        Returns:
            Конфигурация по умолчанию или None
        """
        if self._default_name is None:
            return None
        return self._configs.get(self._default_name)
    
    def set_default(self, name: str) -> None:
        """
        Установка конфигурации по умолчанию
        
        Args:
            name: Имя конфигурации
        """
        if name not in self._configs:
            raise KeyError(f"Config not found: {name}")
        
        self._default_name = name
        logger.info(f"Set default config: {name}")
    
    # ========================================================================
    # VALIDATION AND COMPATIBILITY
    # ========================================================================
    
    def validate_all(self, stop_on_first_error: bool = False) -> Dict[str, Any]:
        """
        Валидация всех конфигураций
        
        Args:
            stop_on_first_error: Остановиться при первой ошибке
            
        Returns:
            Словарь с результатами валидации
        """
        configs_list = list(self._configs.values())
        results = validate_multiple_configs(configs_list, stop_on_first_error)
        
        logger.info(
            f"Validated {len(self._configs)} configs: "
            f"{results['valid_count']} valid, {results['invalid_count']} invalid"
        )
        
        return results
    
    def check_compatibility(self) -> Dict[str, Any]:
        """
        Проверка совместимости всех конфигураций
        
        Returns:
            Словарь с результатами проверки совместимости
        """
        configs_list = list(self._configs.values())
        results = check_multiple_configs_compatibility(configs_list)
        
        logger.info(
            f"Checked compatibility: "
            f"{results['compatible_pairs']} compatible, "
            f"{results['incompatible_pairs']} incompatible"
        )
        
        return results
    
    # ========================================================================
    # STATISTICS AND INFO
    # ========================================================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Получение статистики по всем конфигурациям
        
        Returns:
            Словарь со статистикой
        """
        from collections import Counter
        
        engines = Counter(config.engine for config in self._configs.values())
        
        return {
            'total_configs': len(self._configs),
            'default_config': self._default_name,
            'engines': dict(engines),
            'groups': {
                group: len(configs)
                for group, configs in self._groups.items()
            },
            'tagged_configs': len(self._tags)
        }
    
    def get_info(self) -> Dict[str, Any]:
        """
        Получение подробной информации
        
        Returns:
            Словарь с информацией
        """
        return {
            'configs': {
                name: {
                    'engine': config.engine.value,
                    'host': config.host,
                    'database': config.database,
                    'is_default': name == self._default_name,
                    'groups': [
                        group for group, configs in self._groups.items()
                        if name in configs
                    ],
                    'tags': self._tags.get(name, [])
                }
                for name, config in self._configs.items()
            },
            'statistics': self.get_statistics()
        }
    
    # ========================================================================
    # MAGIC METHODS
    # ========================================================================
    
    def __len__(self) -> int:
        """Количество конфигураций"""
        return len(self._configs)
    
    def __contains__(self, name: str) -> bool:
        """Проверка наличия конфигурации"""
        return name in self._configs
    
    def __iter__(self):
        """Итерация по именам конфигураций"""
        return iter(self._configs)
    
    def __getitem__(self, name: str) -> DatabaseConfigBase:
        """Получение конфигурации через []"""
        return self.get(name)
    
    def __repr__(self) -> str:
        """Строковое представление"""
        return (
            f"MultiDatabaseConfig("
            f"configs={len(self._configs)}, "
            f"default='{self._default_name}', "
            f"groups={len(self._groups)}"
            f")"
        )


__all__ = ['MultiDatabaseConfig']