"""
Database Configuration Validation Helpers
Вспомогательные функции для валидации конфигураций
"""

import logging
from typing import List, Dict, Any

from .database_base import DatabaseConfigBase
from .exceptions import ValidationError, DatabaseValidationError

logger = logging.getLogger(__name__)


# ============================================================================
# SINGLE CONFIG VALIDATION
# ============================================================================

def validate_config(config: DatabaseConfigBase, raise_on_error: bool = True) -> bool:
    """
    Валидация конфигурации БД
    
    Args:
        config: Конфигурация для валидации
        raise_on_error: Выбрасывать исключение при ошибке
        
    Returns:
        True если конфигурация валидна
        
    Raises:
        ValidationError: При ошибках валидации (если raise_on_error=True)
    """
    try:
        result = config.validate()
        logger.info(f"Configuration validation passed for {config.database}")
        return result
    except ValidationError as e:
        logger.error(f"Configuration validation failed: {e}")
        if raise_on_error:
            raise
        return False
    except Exception as e:
        logger.error(f"Unexpected error during validation: {e}")
        if raise_on_error:
            raise ValidationError(
                message=f"Validation failed with unexpected error",
                field='config',
                value=config,
                reason=str(e)
            )
        return False


# ============================================================================
# MULTIPLE CONFIGS VALIDATION
# ============================================================================

def validate_multiple_configs(
    configs: List[DatabaseConfigBase],
    stop_on_first_error: bool = False
) -> Dict[str, Any]:
    """
    Валидация нескольких конфигураций
    
    Args:
        configs: Список конфигураций для валидации
        stop_on_first_error: Остановиться при первой ошибке
        
    Returns:
        Словарь с результатами валидации для каждой конфигурации
        
    Example:
        >>> configs = [config1, config2, config3]
        >>> results = validate_multiple_configs(configs)
        >>> print(results)
        {
            'config_0_mydb': {'valid': True, 'errors': []},
            'config_1_testdb': {'valid': False, 'errors': ['...']},
            'config_2_proddb': {'valid': True, 'errors': []}
        }
    """
    results = {
        'total': len(configs),
        'valid_count': 0,
        'invalid_count': 0,
        'configs': {}
    }
    
    for i, config in enumerate(configs):
        config_id = f"config_{i}_{config.database}"
        
        try:
            is_valid = validate_config(config, raise_on_error=True)
            results['configs'][config_id] = {
                'valid': is_valid,
                'errors': []
            }
            results['valid_count'] += 1
            
        except ValidationError as e:
            results['configs'][config_id] = {
                'valid': False,
                'errors': [str(e)]
            }
            results['invalid_count'] += 1
            
            logger.error(f"Config {config_id} validation failed: {e}")
            
            if stop_on_first_error:
                logger.warning("Stopping validation on first error")
                break
        
        except Exception as e:
            results['configs'][config_id] = {
                'valid': False,
                'errors': [f"Unexpected error: {str(e)}"]
            }
            results['invalid_count'] += 1
            
            logger.error(f"Config {config_id} validation failed with unexpected error: {e}")
            
            if stop_on_first_error:
                logger.warning("Stopping validation on first error")
                break
    
    results['all_valid'] = results['invalid_count'] == 0
    
    logger.info(
        f"Validated {results['total']} configs: "
        f"{results['valid_count']} valid, {results['invalid_count']} invalid"
    )
    
    return results


# ============================================================================
# CONFIG COMPATIBILITY
# ============================================================================

def check_config_compatibility(
    config1: DatabaseConfigBase,
    config2: DatabaseConfigBase
) -> Dict[str, Any]:
    """
    Проверка совместимости двух конфигураций
    
    Args:
        config1: Первая конфигурация
        config2: Вторая конфигурация
        
    Returns:
        Словарь с результатами проверки совместимости
        
    Example:
        >>> compat = check_config_compatibility(config1, config2)
        >>> if compat['compatible']:
        ...     print("Configs are compatible")
        >>> else:
        ...     print(f"Issues: {compat['issues']}")
    """
    compatibility = {
        'compatible': True,
        'same_engine': config1.engine == config2.engine,
        'same_host': config1.host == config2.host,
        'same_port': config1.port == config2.port,
        'different_database': config1.database != config2.database,
        'issues': [],
        'warnings': []
    }
    
    # Проверка движка
    if config1.engine != config2.engine:
        compatibility['issues'].append(
            f"Different database engines: {config1.engine.value} vs {config2.engine.value}"
        )
    
    # Проверка на идентичные параметры подключения
    if (config1.host == config2.host and 
        config1.port == config2.port and 
        config1.database == config2.database):
        
        compatibility['compatible'] = False
        compatibility['issues'].append(
            "Identical connection parameters - potential conflict"
        )
    
    # Проверка на одинаковый хост но разные базы
    if (config1.host == config2.host and 
        config1.port == config2.port and 
        config1.database != config2.database):
        
        compatibility['warnings'].append(
            "Same host/port but different databases - generally OK"
        )
    
    # Проверка пулов соединений
    if config1.pool.max_size + config2.pool.max_size > 100:
        compatibility['warnings'].append(
            f"Combined pool size ({config1.pool.max_size + config2.pool.max_size}) "
            f"may be too large"
        )
    
    # Проверка таймаутов
    if config1.timeouts.connection_timeout != config2.timeouts.connection_timeout:
        compatibility['warnings'].append(
            "Different connection timeouts may cause inconsistent behavior"
        )
    
    # Окончательное решение
    if compatibility['issues']:
        compatibility['compatible'] = False
    
    logger.info(
        f"Compatibility check: {'compatible' if compatibility['compatible'] else 'incompatible'}"
    )
    
    return compatibility


# ============================================================================
# BATCH COMPATIBILITY CHECK
# ============================================================================

def check_multiple_configs_compatibility(
    configs: List[DatabaseConfigBase]
) -> Dict[str, Any]:
    """
    Проверка совместимости нескольких конфигураций
    
    Args:
        configs: Список конфигураций для проверки
        
    Returns:
        Словарь с результатами проверки
    """
    results = {
        'total_configs': len(configs),
        'total_comparisons': 0,
        'compatible_pairs': 0,
        'incompatible_pairs': 0,
        'comparisons': []
    }
    
    # Проверяем все пары
    for i in range(len(configs)):
        for j in range(i + 1, len(configs)):
            results['total_comparisons'] += 1
            
            compat = check_config_compatibility(configs[i], configs[j])
            
            comparison = {
                'config1_index': i,
                'config2_index': j,
                'config1_database': configs[i].database,
                'config2_database': configs[j].database,
                'compatible': compat['compatible'],
                'issues': compat['issues'],
                'warnings': compat['warnings']
            }
            
            results['comparisons'].append(comparison)
            
            if compat['compatible']:
                results['compatible_pairs'] += 1
            else:
                results['incompatible_pairs'] += 1
    
    results['all_compatible'] = results['incompatible_pairs'] == 0
    
    logger.info(
        f"Checked {results['total_comparisons']} pairs: "
        f"{results['compatible_pairs']} compatible, "
        f"{results['incompatible_pairs']} incompatible"
    )
    
    return results


# ============================================================================
# CONNECTION PARAMETERS TEST
# ============================================================================

def test_connection_params(config: DatabaseConfigBase) -> Dict[str, Any]:
    """
    Тестирование параметров подключения (без фактического подключения)
    
    Args:
        config: Конфигурация для тестирования
        
    Returns:
        Словарь с результатами тестирования
        
    Example:
        >>> results = test_connection_params(config)
        >>> if results['valid']:
        ...     print(f"Connection string: {results['connection_string']}")
        >>> else:
        ...     print(f"Errors: {results['errors']}")
    """
    results = {
        'valid': False,
        'connection_string': None,
        'diagnostic_info': None,
        'errors': [],
        'warnings': []
    }
    
    try:
        # Валидация конфигурации
        config.validate()
        
        # Получение строки подключения
        try:
            results['connection_string'] = config.test_connection_string()
        except Exception as e:
            results['warnings'].append(f"Could not generate connection string: {e}")
        
        # Диагностическая информация
        try:
            results['diagnostic_info'] = config.get_diagnostic_info()
        except Exception as e:
            results['warnings'].append(f"Could not get diagnostic info: {e}")
        
        results['valid'] = True
        logger.info(f"Connection parameters test passed for {config.database}")
        
    except ValidationError as e:
        results['errors'].append(f"Validation error: {e}")
        logger.error(f"Connection parameters test failed: {e}")
        
    except Exception as e:
        results['errors'].append(f"Unexpected error: {e}")
        logger.error(f"Unexpected error during connection test: {e}")
    
    return results


__all__ = [
    'validate_config',
    'validate_multiple_configs',
    'check_config_compatibility',
    'check_multiple_configs_compatibility',
    'test_connection_params'
]