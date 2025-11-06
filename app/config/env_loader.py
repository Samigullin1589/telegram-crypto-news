# app/config/env_loader.py
"""
Environment variables loader
"""

import os
from typing import List, Dict, Set, Optional
from dotenv import load_dotenv

load_dotenv()


class EnvironmentLoader:
    """Загрузка конфигурации из переменных окружения"""
    
    @staticmethod
    def get_required_env(*keys: str) -> str:
        """Получает обязательную переменную окружения"""
        for key in keys:
            value = os.getenv(key)
            if value:
                return value
        raise ValueError(f'Требуется одна из переменных окружения: {", ".join(keys)}')
    
    @staticmethod
    def get_env(key: str, default: str = '') -> str:
        """Получает переменную окружения с дефолтом"""
        return os.getenv(key, default)
    
    @staticmethod
    def get_int_env(key: str, default: int) -> int:
        """Получает int переменную окружения"""
        try:
            return int(os.getenv(key, str(default)))
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def get_float_env(key: str, default: float) -> float:
        """Получает float переменную окружения"""
        try:
            return float(os.getenv(key, str(default)))
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def get_bool_env(key: str, default: bool = False) -> bool:
        """Получает bool переменную окружения"""
        value = os.getenv(key, '').lower()
        if not value:
            return default
        return value in ('true', '1', 'yes', 'on')
    
    @staticmethod
    def get_list_env(key: str, default: Optional[List[str]] = None, separator: str = ',') -> List[str]:
        """Получает список из переменной окружения"""
        if default is None:
            default = []
        
        value = os.getenv(key, '')
        if not value:
            return default
        
        return [item.strip() for item in value.split(separator) if item.strip()]
    
    @staticmethod
    def get_set_env(key: str, default: Optional[Set[str]] = None, separator: str = ',') -> Set[str]:
        """Получает set из переменной окружения"""
        if default is None:
            default = set()
        
        value = os.getenv(key, '')
        if not value:
            return default
        
        return {item.strip() for item in value.split(separator) if item.strip()}
    
    @staticmethod
    def get_dict_env(key_prefix: str, keys: List[str]) -> Dict[str, str]:
        """Получает словарь из переменных окружения с префиксом"""
        result = {}
        for key in keys:
            env_key = f'{key_prefix}_{key}'.upper()
            value = os.getenv(env_key, '')
            if value:
                result[key] = value
        return result