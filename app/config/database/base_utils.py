"""
Database Configuration Utility Functions
Утилитарные функции для работы с конфигурациями
"""

import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

from .database_base import DatabaseConfigBase
from .enums import DatabaseEngine, HealthStatus
from .exceptions import DatabaseConfigError

logger = logging.getLogger(__name__)


# ============================================================================
# ENVIRONMENT-SPECIFIC CONFIGS
# ============================================================================

def get_default_config_for_environment(
    environment: str = "development",
    **kwargs: Any
) -> DatabaseConfigBase:
    """
    Получение конфигурации по умолчанию для окружения
    
    Args:
        environment: Название окружения (development/testing/production/staging)
        **kwargs: Дополнительные параметры для переопределения defaults
        
    Returns:
        Конфигурация с настройками для окружения
        
    Example:
        >>> dev_config = get_default_config_for_environment('development')
        >>> prod_config = get_default_config_for_environment('production',
        ...                                                   host='prod.db.com')
    """
    environment = environment.lower()
    
    # Базовые настройки для каждого окружения
    env_configs = {
        'development': {
            'echo_queries': True,
            'log_slow_queries': True,
            'log_slow_query_threshold': 1.0,
        },
        'testing': {
            'echo_queries': False,
            'log_slow_queries': False,
        },
        'staging': {
            'echo_queries': False,
            'log_slow_queries': True,
            'log_slow_query_threshold': 2.0,
        },
        'production': {
            'echo_queries': False,
            'log_slow_queries': True,
            'log_slow_query_threshold': 5.0,
        }
    }
    
    config_params = env_configs.get(environment, env_configs['development'])
    
    # Объединяем с переданными параметрами
    config_params.update(kwargs)
    
    # Загружаем базовую конфигурацию из env
    try:
        config = DatabaseConfigBase.from_env()
        
        # Обновляем параметрами окружения
        config.update_from_dict(config_params, validate=True)
        
        logger.info(f"Created config for environment: {environment}")
        return config
        
    except Exception as e:
        logger.error(f"Failed to create config for environment {environment}: {e}")
        raise DatabaseConfigError(
            f"Failed to create config for environment: {environment}",
            details={'environment': environment, 'error': str(e)}
        )


# ============================================================================
# CONFIG COMPARISON
# ============================================================================

def compare_configs(
    config1: DatabaseConfigBase,
    config2: DatabaseConfigBase,
    ignore_fields: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Сравнение двух конфигураций и получение различий
    
    Args:
        config1: Первая конфигурация
        config2: Вторая конфигурация
        ignore_fields: Поля для игнорирования при сравнении
        
    Returns:
        Словарь с различиями
        
    Example:
        >>> diff = compare_configs(config1, config2)
        >>> if not diff['equal']:
        ...     print(f"Found {len(diff['differences'])} differences")
        ...     for field, values in diff['differences'].items():
        ...         print(f"{field}: {values['config1']} -> {values['config2']}")
    """
    ignore_fields = ignore_fields or []
    
    dict1 = config1.to_dict(mask_sensitive=False)
    dict2 = config2.to_dict(mask_sensitive=False)
    
    differences = {
        'equal': config1 == config2,
        'differences': {},
        'only_in_config1': [],
        'only_in_config2': [],
        'ignored_fields': ignore_fields
    }
    
    # Находим все ключи
    all_keys = set(dict1.keys()) | set(dict2.keys())
    
    for key in all_keys:
        # Пропускаем игнорируемые поля
        if key in ignore_fields:
            continue
        
        val1 = dict1.get(key)
        val2 = dict2.get(key)
        
        # Поле только в config1
        if key not in dict2:
            differences['only_in_config1'].append(key)
            continue
        
        # Поле только в config2
        if key not in dict1:
            differences['only_in_config2'].append(key)
            continue
        
        # Значения различаются
        if val1 != val2:
            differences['differences'][key] = {
                'config1': val1,
                'config2': val2,
                'type1': type(val1).__name__,
                'type2': type(val2).__name__
            }
    
    differences['total_differences'] = (
        len(differences['differences']) +
        len(differences['only_in_config1']) +
        len(differences['only_in_config2'])
    )
    
    logger.info(
        f"Config comparison: {differences['total_differences']} differences found"
    )
    
    return differences


def get_config_diff_summary(
    config1: DatabaseConfigBase,
    config2: DatabaseConfigBase
) -> str:
    """
    Получение краткого текстового описания различий
    
    Args:
        config1: Первая конфигурация
        config2: Вторая конфигурация
        
    Returns:
        Текстовое описание различий
    """
    diff = compare_configs(config1, config2)
    
    if diff['equal']:
        return "Configurations are identical"
    
    lines = [
        f"Configuration Differences ({diff['total_differences']} found):",
        ""
    ]
    
    if diff['differences']:
        lines.append("Changed fields:")
        for field, values in diff['differences'].items():
            lines.append(f"  - {field}: {values['config1']} -> {values['config2']}")
        lines.append("")
    
    if diff['only_in_config1']:
        lines.append("Only in config1:")
        for field in diff['only_in_config1']:
            lines.append(f"  - {field}")
        lines.append("")
    
    if diff['only_in_config2']:
        lines.append("Only in config2:")
        for field in diff['only_in_config2']:
            lines.append(f"  - {field}")
    
    return "\n".join(lines)


# ============================================================================
# CONFIG DIAGNOSTICS
# ============================================================================

def diagnose_config(config: DatabaseConfigBase) -> Dict[str, Any]:
    """
    Диагностика конфигурации с проверками и рекомендациями
    
    Args:
        config: Конфигурация для диагностики
        
    Returns:
        Словарь с результатами диагностики
    """
    diagnostics = {
        'timestamp': datetime.utcnow().isoformat(),
        'engine': config.engine.value,
        'database': config.database,
        'issues': [],
        'warnings': [],
        'recommendations': [],
        'health': 'unknown'
    }
    
    # Проверка пула соединений
    if config.pool.max_size < 5:
        diagnostics['warnings'].append(
            f"Small pool size ({config.pool.max_size}), may cause bottlenecks under load"
        )
    elif config.pool.max_size > 100:
        diagnostics['warnings'].append(
            f"Large pool size ({config.pool.max_size}), may consume excessive resources"
        )
    
    if config.pool.min_size > config.pool.max_size / 2:
        diagnostics['recommendations'].append(
            "Consider reducing min_size to save resources during low traffic"
        )
    
    # Проверка таймаутов
    if config.timeouts.connection_timeout < 5:
        diagnostics['warnings'].append(
            f"Very short connection timeout ({config.timeouts.connection_timeout}s)"
        )
    elif config.timeouts.connection_timeout > 60:
        diagnostics['warnings'].append(
            f"Very long connection timeout ({config.timeouts.connection_timeout}s)"
        )
    
    if config.timeouts.query_timeout < 10:
        diagnostics['warnings'].append(
            f"Short query timeout ({config.timeouts.query_timeout}s), may interrupt long queries"
        )
    
    # Проверка SSL
    if not config.ssl.enabled and config.engine != DatabaseEngine.SQLITE:
        diagnostics['recommendations'].append(
            "Consider enabling SSL for secure connections"
        )
    
    # Проверка мониторинга
    if not config.monitoring.enabled:
        diagnostics['recommendations'].append(
            "Consider enabling monitoring for better observability"
        )
    
    # Проверка retry
    if not config.retry.enabled:
        diagnostics['recommendations'].append(
            "Consider enabling retry logic for resilience"
        )
    
    # Проверка специфичных настроек для движка
    if config.engine == DatabaseEngine.POSTGRESQL:
        if not config.schema:
            diagnostics['warnings'].append(
                "No schema specified, will use 'public' by default"
            )
    
    if config.engine == DatabaseEngine.SQLITE:
        if config.database == ':memory:':
            diagnostics['warnings'].append(
                "Using in-memory database, data will be lost on restart"
            )
    
    # Определение общего health статуса
    if diagnostics['issues']:
        diagnostics['health'] = 'critical'
    elif len(diagnostics['warnings']) > 3:
        diagnostics['health'] = 'warning'
    elif diagnostics['warnings']:
        diagnostics['health'] = 'acceptable'
    else:
        diagnostics['health'] = 'good'
    
    logger.info(f"Config diagnostics completed: {diagnostics['health']}")
    
    return diagnostics


def print_diagnostics(config: DatabaseConfigBase) -> None:
    """
    Печать диагностической информации в читаемом формате
    
    Args:
        config: Конфигурация для диагностики
    """
    diag = diagnose_config(config)
    
    print(f"\n{'='*60}")
    print(f"DATABASE CONFIGURATION DIAGNOSTICS")
    print(f"{'='*60}")
    print(f"Engine: {diag['engine']}")
    print(f"Database: {diag['database']}")
    print(f"Health: {diag['health'].upper()}")
    print(f"Timestamp: {diag['timestamp']}")
    print(f"{'='*60}\n")
    
    if diag['issues']:
        print("ISSUES:")
        for issue in diag['issues']:
            print(f"  ❌ {issue}")
        print()
    
    if diag['warnings']:
        print("WARNINGS:")
        for warning in diag['warnings']:
            print(f"  ⚠️  {warning}")
        print()
    
    if diag['recommendations']:
        print("RECOMMENDATIONS:")
        for rec in diag['recommendations']:
            print(f"  💡 {rec}")
        print()
    
    if not diag['issues'] and not diag['warnings'] and not diag['recommendations']:
        print("✅ No issues found - configuration looks good!\n")


# ============================================================================
# CONFIG CLONING AND MERGING
# ============================================================================

def clone_config(
    config: DatabaseConfigBase,
    **overrides: Any
) -> DatabaseConfigBase:
    """
    Клонирование конфигурации с возможностью переопределения параметров
    
    Args:
        config: Исходная конфигурация
        **overrides: Параметры для переопределения
        
    Returns:
        Новая конфигурация
        
    Example:
        >>> prod_config = DatabaseConfigBase.from_env()
        >>> test_config = clone_config(prod_config, database='test_db')
    """
    config_dict = config.to_dict(mask_sensitive=False)
    config_dict.update(overrides)
    
    return DatabaseConfigBase(**config_dict)


def merge_configs(
    base_config: DatabaseConfigBase,
    override_config: DatabaseConfigBase,
    prefer_override: bool = True
) -> DatabaseConfigBase:
    """
    Слияние двух конфигураций
    
    Args:
        base_config: Базовая конфигурация
        override_config: Конфигурация для переопределения
        prefer_override: Предпочитать значения из override_config при конфликтах
        
    Returns:
        Объединённая конфигурация
    """
    base_dict = base_config.to_dict(mask_sensitive=False)
    override_dict = override_config.to_dict(mask_sensitive=False)
    
    if prefer_override:
        merged = {**base_dict, **override_dict}
    else:
        merged = {**override_dict, **base_dict}
    
    return DatabaseConfigBase(**merged)


# ============================================================================
# CONFIG DISCOVERY
# ============================================================================

def discover_configs_in_directory(
    directory: str,
    recursive: bool = False
) -> Dict[str, DatabaseConfigBase]:
    """
    Поиск конфигурационных файлов в директории
    
    Args:
        directory: Путь к директории
        recursive: Рекурсивный поиск в поддиректориях
        
    Returns:
        Словарь найденных конфигураций {filename: config}
    """
    import json
    from pathlib import Path
    
    configs = {}
    path = Path(directory)
    
    if not path.exists():
        logger.warning(f"Directory does not exist: {directory}")
        return configs
    
    # Паттерны файлов конфигурации
    patterns = ['*.json', '*.yaml', '*.yml']
    
    for pattern in patterns:
        if recursive:
            files = path.rglob(pattern)
        else:
            files = path.glob(pattern)
        
        for filepath in files:
            try:
                # Пытаемся загрузить конфигурацию
                with open(filepath, 'r', encoding='utf-8') as f:
                    if filepath.suffix == '.json':
                        data = json.load(f)
                    else:
                        try:
                            import yaml
                            data = yaml.safe_load(f)
                        except ImportError:
                            logger.warning(f"PyYAML not installed, skipping {filepath}")
                            continue
                
                # Проверяем, что это похоже на конфигурацию БД
                if 'engine' in data or 'database' in data:
                    config = DatabaseConfigBase(**data)
                    configs[filepath.name] = config
                    logger.info(f"Discovered config: {filepath.name}")
                    
            except Exception as e:
                logger.warning(f"Failed to load config from {filepath}: {e}")
                continue
    
    logger.info(f"Discovered {len(configs)} configs in {directory}")
    
    return configs


# ============================================================================
# CONFIG EXPORT
# ============================================================================

def export_config_to_env_file(
    config: DatabaseConfigBase,
    filepath: str,
    prefix: str = "DATABASE_",
    mask_sensitive: bool = False
) -> None:
    """
    Экспорт конфигурации в .env файл
    
    Args:
        config: Конфигурация для экспорта
        filepath: Путь к .env файлу
        prefix: Префикс для переменных
        mask_sensitive: Маскировать чувствительные данные
    """
    config_dict = config.to_dict(mask_sensitive=mask_sensitive)
    
    lines = [
        f"# Database Configuration",
        f"# Generated at {datetime.utcnow().isoformat()}",
        f"",
        f"{prefix}ENGINE={config.engine.value}",
        f"{prefix}HOST={config.host}",
        f"{prefix}PORT={config.port}",
        f"{prefix}DATABASE={config.database}",
        f"{prefix}USER={config.user}",
        f"{prefix}PASSWORD={config.password if not mask_sensitive else '***'}",
        f"{prefix}SCHEMA={config.schema}",
        f"",
        f"# Pool Configuration",
        f"{prefix}POOL_MIN_SIZE={config.pool.min_size}",
        f"{prefix}POOL_MAX_SIZE={config.pool.max_size}",
        f"",
        f"# Timeout Configuration",
        f"{prefix}CONNECTION_TIMEOUT={config.timeouts.connection_timeout}",
        f"{prefix}QUERY_TIMEOUT={config.timeouts.query_timeout}",
        f"",
        f"# SSL Configuration",
        f"{prefix}SSL_ENABLED={str(config.ssl.enabled).lower()}",
        f"",
        f"# Monitoring Configuration",
        f"{prefix}MONITORING_ENABLED={str(config.monitoring.enabled).lower()}",
        f"",
    ]
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    logger.info(f"Config exported to env file: {filepath}")


def generate_config_documentation(config: DatabaseConfigBase) -> str:
    """
    Генерация документации по конфигурации
    
    Args:
        config: Конфигурация для документирования
        
    Returns:
        Markdown документация
    """
    doc = [
        f"# Database Configuration Documentation",
        f"",
        f"Generated: {datetime.utcnow().isoformat()}",
        f"",
        f"## Connection",
        f"",
        f"- **Engine**: {config.engine.value}",
        f"- **Host**: {config.host}",
        f"- **Port**: {config.port}",
        f"- **Database**: {config.database}",
        f"- **User**: {config.user}",
        f"- **Schema**: {config.schema or 'default'}",
        f"",
        f"## Pool Configuration",
        f"",
        f"- **Min Size**: {config.pool.min_size}",
        f"- **Max Size**: {config.pool.max_size}",
        f"- **Overflow**: {config.pool.overflow}",
        f"- **Timeout**: {config.pool.timeout}s",
        f"- **Strategy**: {config.pool.strategy.value}",
        f"",
        f"## Timeouts",
        f"",
        f"- **Connection**: {config.timeouts.connection_timeout}s",
        f"- **Query**: {config.timeouts.query_timeout}s",
        f"",
        f"## SSL",
        f"",
        f"- **Enabled**: {config.ssl.enabled}",
        f"- **Mode**: {config.ssl.mode.value if config.ssl.enabled else 'N/A'}",
        f"",
        f"## Monitoring",
        f"",
        f"- **Enabled**: {config.monitoring.enabled}",
        f"- **Collect Metrics**: {config.monitoring.collect_metrics}",
        f"",
        f"## Retry Configuration",
        f"",
        f"- **Enabled**: {config.retry.enabled}",
        f"- **Max Attempts**: {config.retry.max_attempts}",
        f"",
    ]
    
    return '\n'.join(doc)


__all__ = [
    'get_default_config_for_environment',
    'compare_configs',
    'get_config_diff_summary',
    'diagnose_config',
    'print_diagnostics',
    'clone_config',
    'merge_configs',
    'discover_configs_in_directory',
    'export_config_to_env_file',
    'generate_config_documentation'
]