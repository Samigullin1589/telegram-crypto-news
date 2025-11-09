"""
Database Configuration Migration Helpers
Помощники для миграции конфигураций между форматами
"""

import logging
from typing import Dict, Any, Optional

from .database_base import DatabaseConfigBase
from .enums import DatabaseEngine
from .exceptions import DatabaseConfigError, ValidationError

logger = logging.getLogger(__name__)


# ============================================================================
# LEGACY FORMAT MIGRATION
# ============================================================================

def migrate_from_dict(
    old_config: Dict[str, Any],
    strict: bool = False
) -> DatabaseConfigBase:
    """
    Миграция из старого формата словаря в новую конфигурацию
    
    Args:
        old_config: Словарь со старой конфигурацией
        strict: Строгий режим - выбрасывать исключения при неизвестных ключах
        
    Returns:
        Новая конфигурация DatabaseConfigBase
        
    Raises:
        DatabaseConfigError: При ошибках миграции
        
    Example:
        >>> old = {
        ...     'db_host': 'localhost',
        ...     'db_port': 5432,
        ...     'db_name': 'myapp',
        ...     'db_user': 'admin',
        ...     'db_password': 'secret'
        ... }
        >>> config = migrate_from_dict(old)
    """
    logger.info("Migrating configuration from dict format")
    
    # Mapping старых ключей на новые
    key_mapping = {
        # Connection
        'db_host': 'host',
        'db_port': 'port',
        'db_name': 'database',
        'db_database': 'database',
        'db_user': 'user',
        'db_username': 'user',
        'db_password': 'password',
        'db_pass': 'password',
        'db_engine': 'engine',
        'db_driver': 'engine',
        'db_schema': 'schema',
        
        # Pool
        'pool_min': 'pool.min_size',
        'pool_max': 'pool.max_size',
        'pool_size': 'pool.max_size',
        'min_pool_size': 'pool.min_size',
        'max_pool_size': 'pool.max_size',
        
        # Timeouts
        'timeout': 'timeouts.query_timeout',
        'connection_timeout': 'timeouts.connection_timeout',
        'query_timeout': 'timeouts.query_timeout',
        
        # SSL
        'ssl': 'ssl.enabled',
        'ssl_mode': 'ssl.mode',
        'ssl_cert': 'ssl.cert_file',
        'ssl_key': 'ssl.key_file',
        'ssl_ca': 'ssl.ca_file',
        
        # Logging
        'echo': 'echo_queries',
        'echo_queries': 'echo_queries',
        'log_queries': 'echo_queries',
        'log_slow_queries': 'log_slow_queries',
        
        # Charset
        'charset': 'charset',
        'encoding': 'charset'
    }
    
    # Преобразуем ключи
    new_config = {}
    unknown_keys = []
    
    for old_key, value in old_config.items():
        new_key = key_mapping.get(old_key, old_key)
        
        # Обработка вложенных ключей (например, 'pool.min_size')
        if '.' in new_key:
            parts = new_key.split('.')
            if parts[0] not in new_config:
                new_config[parts[0]] = {}
            
            # Рекурсивно создаем вложенную структуру
            current = new_config[parts[0]]
            for part in parts[1:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
        else:
            new_config[new_key] = value
        
        # Отслеживаем неизвестные ключи
        if old_key not in key_mapping and old_key not in new_config:
            unknown_keys.append(old_key)
    
    # Обработка unknown keys
    if unknown_keys:
        logger.warning(f"Unknown keys in migration: {unknown_keys}")
        if strict:
            raise DatabaseConfigError(
                "Unknown keys found during migration",
                details={'unknown_keys': unknown_keys}
            )
    
    # Преобразуем engine если это строка
    if 'engine' in new_config and isinstance(new_config['engine'], str):
        try:
            new_config['engine'] = DatabaseEngine(new_config['engine'].lower())
        except ValueError:
            logger.error(f"Invalid engine value: {new_config['engine']}")
            raise DatabaseConfigError(
                f"Invalid engine value: {new_config['engine']}",
                details={'engine': new_config['engine']}
            )
    
    # Создаем конфигурацию
    try:
        config = DatabaseConfigBase(**new_config)
        logger.info("Migration completed successfully")
        return config
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise DatabaseConfigError(
            "Failed to create config from migrated data",
            details={'error': str(e), 'config': new_config}
        )


# ============================================================================
# EXPORT TO LEGACY FORMAT
# ============================================================================

def export_to_legacy_format(
    config: DatabaseConfigBase,
    include_private: bool = False
) -> Dict[str, Any]:
    """
    Экспорт конфигурации в legacy формат для обратной совместимости
    
    Args:
        config: Современная конфигурация
        include_private: Включить приватные/внутренние поля
        
    Returns:
        Словарь в старом формате
        
    Example:
        >>> config = DatabaseConfigBase.from_env()
        >>> legacy = export_to_legacy_format(config)
        >>> print(legacy['db_host'])
        'localhost'
    """
    logger.info("Exporting config to legacy format")
    
    legacy = {
        # Connection
        'db_engine': config.engine.value,
        'db_host': config.host,
        'db_port': config.port,
        'db_name': config.database,
        'db_user': config.user,
        'db_password': config.password,
        'db_schema': config.schema,
        
        # Pool
        'pool_min': config.pool.min_size,
        'pool_max': config.pool.max_size,
        
        # Timeouts
        'timeout': config.timeouts.query_timeout,
        'connection_timeout': config.timeouts.connection_timeout,
        
        # SSL
        'ssl': config.ssl.enabled,
        'ssl_mode': config.ssl.mode.value if config.ssl.enabled else None,
        
        # Logging
        'echo': config.echo_queries,
        'log_slow_queries': config.log_slow_queries,
        
        # Charset
        'charset': getattr(config, 'charset', 'utf8mb4')
    }
    
    # Добавляем приватные поля если требуется
    if include_private:
        legacy.update({
            'pool_strategy': config.pool.strategy.value,
            'pool_overflow': config.pool.overflow,
            'pool_timeout': config.pool.timeout,
            'query_timeout': config.timeouts.query_timeout,
            'idle_timeout': config.timeouts.idle_in_transaction_session_timeout
        })
    
    logger.info("Export to legacy format completed")
    
    return legacy


# ============================================================================
# URL MIGRATION
# ============================================================================

def migrate_from_url(
    url: str,
    additional_params: Optional[Dict[str, Any]] = None
) -> DatabaseConfigBase:
    """
    Миграция из URL формата
    
    Args:
        url: URL подключения к БД
        additional_params: Дополнительные параметры
        
    Returns:
        Новая конфигурация
        
    Example:
        >>> url = 'postgresql://user:pass@localhost:5432/mydb'
        >>> config = migrate_from_url(url)
    """
    logger.info(f"Migrating from URL format")
    
    try:
        config = DatabaseConfigBase.from_url(url)
        
        # Добавляем дополнительные параметры если есть
        if additional_params:
            config.update_from_dict(additional_params, validate=True)
        
        logger.info("Migration from URL completed successfully")
        return config
        
    except Exception as e:
        logger.error(f"Migration from URL failed: {e}")
        raise DatabaseConfigError(
            "Failed to migrate from URL",
            details={'url': url[:50], 'error': str(e)}  # Обрезаем URL для безопасности
        )


# ============================================================================
# ENVIRONMENT VARIABLES MIGRATION
# ============================================================================

def migrate_from_env_vars(
    env_mapping: Dict[str, str],
    prefix: str = ""
) -> DatabaseConfigBase:
    """
    Миграция из кастомных переменных окружения
    
    Args:
        env_mapping: Маппинг переменных окружения на параметры конфигурации
        prefix: Префикс для переменных окружения
        
    Returns:
        Новая конфигурация
        
    Example:
        >>> mapping = {
        ...     'CUSTOM_DB_HOST': 'host',
        ...     'CUSTOM_DB_PORT': 'port',
        ...     'CUSTOM_DB_NAME': 'database'
        ... }
        >>> config = migrate_from_env_vars(mapping)
    """
    import os
    
    logger.info("Migrating from custom environment variables")
    
    config_dict = {}
    
    for env_var, config_key in env_mapping.items():
        # Добавляем префикс если указан
        full_env_var = f"{prefix}{env_var}" if prefix else env_var
        
        value = os.environ.get(full_env_var)
        if value is not None:
            # Обработка вложенных ключей
            if '.' in config_key:
                parts = config_key.split('.')
                current = config_dict
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = value
            else:
                config_dict[config_key] = value
    
    if not config_dict:
        logger.warning("No environment variables found for migration")
        raise DatabaseConfigError(
            "No configuration found in environment variables",
            details={'mapping': env_mapping, 'prefix': prefix}
        )
    
    try:
        return migrate_from_dict(config_dict)
    except Exception as e:
        logger.error(f"Migration from env vars failed: {e}")
        raise


# ============================================================================
# VERSION MIGRATION
# ============================================================================

def migrate_config_version(
    config: DatabaseConfigBase,
    from_version: str,
    to_version: str
) -> DatabaseConfigBase:
    """
    Миграция конфигурации между версиями
    
    Args:
        config: Исходная конфигурация
        from_version: Версия исходной конфигурации
        to_version: Целевая версия
        
    Returns:
        Мигрированная конфигурация
        
    Note:
        В данный момент поддерживается только v1 -> v2
    """
    logger.info(f"Migrating config from v{from_version} to v{to_version}")
    
    # Определяем путь миграции
    migration_path = f"{from_version}_{to_version}"
    
    migrations = {
        '1_2': _migrate_v1_to_v2,
        '2_3': _migrate_v2_to_v3,
    }
    
    migration_func = migrations.get(migration_path)
    if not migration_func:
        raise DatabaseConfigError(
            f"No migration path available from v{from_version} to v{to_version}",
            details={'from': from_version, 'to': to_version}
        )
    
    return migration_func(config)


def _migrate_v1_to_v2(config: DatabaseConfigBase) -> DatabaseConfigBase:
    """Миграция с версии 1 на версию 2"""
    logger.info("Performing v1 -> v2 migration")
    
    # В v2 добавлены новые поля для мониторинга
    config_dict = config.to_dict(mask_sensitive=False)
    
    # Добавляем новые поля с defaults
    config_dict.setdefault('monitoring', {
        'enabled': True,
        'collect_metrics': True,
        'metrics_interval': 60
    })
    
    return DatabaseConfigBase(**config_dict)


def _migrate_v2_to_v3(config: DatabaseConfigBase) -> DatabaseConfigBase:
    """Миграция с версии 2 на версию 3"""
    logger.info("Performing v2 -> v3 migration")
    
    # В v3 изменена структура retry конфигурации
    config_dict = config.to_dict(mask_sensitive=False)
    
    # Обновляем retry конфигурацию
    if 'retry' in config_dict:
        old_retry = config_dict['retry']
        config_dict['retry'] = {
            'enabled': old_retry.get('enabled', True),
            'max_attempts': old_retry.get('max_retries', 3) + 1,  # v3 считает все попытки
            'initial_delay': old_retry.get('delay', 1.0),
            'max_delay': old_retry.get('max_delay', 60.0),
            'exponential_base': old_retry.get('backoff_factor', 2.0)
        }
    
    return DatabaseConfigBase(**config_dict)


# ============================================================================
# BACKUP AND RESTORE
# ============================================================================

def backup_config(
    config: DatabaseConfigBase,
    filepath: str,
    format: str = 'json'
) -> None:
    """
    Создание бэкапа конфигурации
    
    Args:
        config: Конфигурация для бэкапа
        filepath: Путь к файлу бэкапа
        format: Формат файла ('json' или 'yaml')
    """
    import json
    from datetime import datetime
    
    logger.info(f"Creating config backup: {filepath}")
    
    backup_data = {
        'version': '2.0',
        'timestamp': datetime.utcnow().isoformat(),
        'config': config.to_dict(mask_sensitive=False)
    }
    
    format = format.lower()
    
    if format == 'json':
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, default=str)
    elif format == 'yaml':
        try:
            import yaml
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(backup_data, f, default_flow_style=False)
        except ImportError:
            raise DatabaseConfigError("PyYAML is required for YAML format")
    else:
        raise ValueError(f"Unsupported format: {format}")
    
    logger.info(f"Config backup created: {filepath}")


def restore_config(
    filepath: str,
    format: Optional[str] = None
) -> DatabaseConfigBase:
    """
    Восстановление конфигурации из бэкапа
    
    Args:
        filepath: Путь к файлу бэкапа
        format: Формат файла ('json' или 'yaml'), auto-detect если None
        
    Returns:
        Восстановленная конфигурация
    """
    import json
    
    logger.info(f"Restoring config from backup: {filepath}")
    
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
        if format == 'json':
            backup_data = json.load(f)
        elif format == 'yaml':
            try:
                import yaml
                backup_data = yaml.safe_load(f)
            except ImportError:
                raise DatabaseConfigError("PyYAML is required for YAML format")
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    # Проверяем версию
    version = backup_data.get('version', '1.0')
    logger.info(f"Backup version: {version}")
    
    # Извлекаем конфигурацию
    config_data = backup_data.get('config', {})
    
    # Создаем конфигурацию
    config = DatabaseConfigBase(**config_data)
    
    logger.info("Config restored from backup successfully")
    
    return config


__all__ = [
    'migrate_from_dict',
    'export_to_legacy_format',
    'migrate_from_url',
    'migrate_from_env_vars',
    'migrate_config_version',
    'backup_config',
    'restore_config'
]