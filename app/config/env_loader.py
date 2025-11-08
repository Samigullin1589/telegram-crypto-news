"""
Environment Loader
Загрузка переменных окружения из .env файла

Этот модуль отвечает ТОЛЬКО за загрузку переменных окружения.
Никакой дополнительной логики здесь быть не должно.
"""

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def find_env_file() -> Optional[Path]:
    """
    Поиск .env файла в проекте
    
    Ищет файл в следующих местах (по порядку):
    1. Текущая директория
    2. Родительская директория (для запуска из поддиректорий)
    3. Корень проекта (2 уровня вверх)
    
    Returns:
        Path к .env файлу или None если не найден
    """
    # Текущая директория
    current_dir = Path.cwd()
    
    # Возможные расположения .env файла
    possible_locations = [
        current_dir / '.env',
        current_dir.parent / '.env',
        current_dir.parent.parent / '.env',
    ]
    
    for env_path in possible_locations:
        if env_path.exists() and env_path.is_file():
            logger.debug(f"Найден .env файл: {env_path}")
            return env_path
    
    logger.debug(".env файл не найден")
    return None


def load_environment() -> bool:
    """
    Загрузка переменных окружения из .env файла
    
    Использует python-dotenv если доступен, иначе загружает вручную.
    
    Returns:
        True если файл успешно загружен, False иначе
    """
    env_file = find_env_file()
    
    if not env_file:
        logger.info("Файл .env не найден, используются переменные окружения системы")
        return False
    
    try:
        # Попытка использовать python-dotenv
        try:
            from dotenv import load_dotenv
            success = load_dotenv(env_file, override=False)
            if success:
                logger.info(f"✓ Переменные окружения загружены из {env_file}")
                return True
            else:
                logger.warning(f"load_dotenv вернул False для {env_file}")
                return False
                
        except ImportError:
            # Если dotenv не установлен, загружаем вручную
            logger.debug("python-dotenv не установлен, загрузка вручную")
            return _load_env_manually(env_file)
            
    except Exception as e:
        logger.error(f"Ошибка загрузки .env файла: {e}", exc_info=True)
        return False


def _load_env_manually(env_file: Path) -> bool:
    """
    Ручная загрузка .env файла
    
    Используется как fallback если python-dotenv не установлен.
    
    Args:
        env_file: Path к .env файлу
        
    Returns:
        True если успешно загружено
    """
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        loaded_count = 0
        
        for line_num, line in enumerate(lines, 1):
            # Убираем пробелы
            line = line.strip()
            
            # Пропускаем пустые строки и комментарии
            if not line or line.startswith('#'):
                continue
            
            # Парсим строку KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Убираем кавычки если есть
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                # Устанавливаем переменную только если её еще нет
                if key and key not in os.environ:
                    os.environ[key] = value
                    loaded_count += 1
                    logger.debug(f"Загружена переменная: {key}")
        
        logger.info(f"✓ Вручную загружено {loaded_count} переменных из {env_file}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка ручной загрузки .env: {e}", exc_info=True)
        return False


def get_env_info() -> dict:
    """
    Получение информации о загруженных переменных окружения
    
    Returns:
        Словарь с информацией о переменных
    """
    env_file = find_env_file()
    
    # Подсчет переменных по префиксам
    prefixes = ['TELEGRAM_', 'API_', 'ENABLED_', 'WHALE_', 'NEWS_']
    counts = {}
    
    for prefix in prefixes:
        count = sum(1 for key in os.environ.keys() if key.startswith(prefix))
        if count > 0:
            counts[prefix.rstrip('_')] = count
    
    return {
        'env_file_path': str(env_file) if env_file else None,
        'env_file_exists': env_file is not None,
        'total_env_vars': len(os.environ),
        'crypto_bot_vars': counts,
    }


# Автоматическая загрузка при импорте модуля
if __name__ != '__main__':
    # Загружаем только если это не прямой запуск модуля
    load_environment()