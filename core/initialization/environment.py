# core/initialization/environment.py
"""
Environment Initializer Module
===============================

Модуль валидации окружения и загрузки конфигурации.

Components:
-----------
- EnvironmentInitializer: Валидация окружения и загрузка конфигурации

Architecture:
-------------
Обеспечивает:
- Проверку переменных окружения
- Валидацию зависимостей
- Загрузку конфигурации приложения
- Проверку прав доступа

Production Ready:
-----------------
- Полная обработка ошибок
- Детальное логирование
- Валидация всех критических параметров
"""

import logging
import os
import sys
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class EnvironmentInitializer:
    """
    Валидатор окружения и загрузчик конфигурации
    
    Выполняет комплексную валидацию окружения и загружает
    конфигурацию приложения.
    
    Responsibilities:
    -----------------
    - Проверка переменных окружения
    - Валидация зависимостей
    - Проверка прав доступа
    - Загрузка конфигурации
    
    Attributes:
        validation_errors: Список ошибок валидации
        validation_warnings: Список предупреждений
    """
    
    def __init__(self):
        """Инициализация валидатора окружения"""
        self.validation_errors: List[str] = []
        self.validation_warnings: List[str] = []
        
        logger.debug("EnvironmentInitializer initialized")
    
    def validate_and_load(self) -> Any:
        """
        Валидация окружения и загрузка конфигурации
        
        Основной метод, который:
        1. Выполняет валидацию окружения
        2. Проверяет критические зависимости
        3. Загружает конфигурацию
        4. Валидирует конфигурацию
        
        Returns:
            Config: Объект конфигурации приложения
            
        Raises:
            RuntimeError: Если валидация не прошла
            ImportError: Если не удается загрузить конфигурацию
            
        Example:
            >>> initializer = EnvironmentInitializer()
            >>> config = initializer.validate_and_load()
            >>> print(config.TELEGRAM_BOT_TOKEN)
        """
        logger.info("🔍 Starting environment validation and config loading...")
        
        try:
            # Шаг 1: Валидация окружения
            self._validate_environment()
            
            # Шаг 2: Проверка зависимостей
            self._validate_dependencies()
            
            # Шаг 3: Проверка прав доступа
            self._validate_permissions()
            
            # Шаг 4: Загрузка конфигурации
            config = self._load_configuration()
            
            # Шаг 5: Валидация конфигурации
            self._validate_configuration(config)
            
            # Вывод предупреждений
            if self.validation_warnings:
                logger.warning(f"⚠️  Environment validation completed with {len(self.validation_warnings)} warnings")
                for warning in self.validation_warnings:
                    logger.warning(f"  • {warning}")
            
            logger.info("✅ Environment validation and config loading completed")
            
            return config
        
        except Exception as e:
            logger.error(f"❌ Environment validation failed: {e}", exc_info=True)
            
            # Вывод собранных ошибок
            if self.validation_errors:
                logger.error("Validation errors:")
                for error in self.validation_errors:
                    logger.error(f"  • {error}")
            
            raise
    
    def _validate_environment(self):
        """
        Валидация переменных окружения
        
        Проверяет наличие критических переменных окружения.
        
        Raises:
            RuntimeError: Если критические переменные отсутствуют
        """
        logger.debug("Validating environment variables...")
        
        # Критические переменные окружения
        critical_vars = [
            'TELEGRAM_BOT_TOKEN',
        ]
        
        # Опциональные но важные переменные
        important_vars = [
            'TELEGRAM_CHANNEL_ID',
            'ADMIN_CHAT_ID',
        ]
        
        # Проверка критических переменных
        missing_critical = []
        for var in critical_vars:
            if not os.getenv(var):
                missing_critical.append(var)
                self.validation_errors.append(f"Missing critical environment variable: {var}")
        
        if missing_critical:
            raise RuntimeError(f"Missing critical environment variables: {', '.join(missing_critical)}")
        
        # Проверка важных переменных
        for var in important_vars:
            if not os.getenv(var):
                self.validation_warnings.append(f"Missing important environment variable: {var}")
        
        logger.debug("✅ Environment variables validated")
    
    def _validate_dependencies(self):
        """
        Валидация зависимостей
        
        Проверяет наличие критических Python пакетов.
        
        Raises:
            ImportError: Если критические пакеты отсутствуют
        """
        logger.debug("Validating dependencies...")
        
        # Критические зависимости
        critical_packages = [
            'asyncio',
            'aiohttp',
            'aiogram',
            'sqlalchemy',
        ]
        
        missing_packages = []
        for package in critical_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
                self.validation_errors.append(f"Missing critical package: {package}")
        
        if missing_packages:
            raise ImportError(f"Missing critical packages: {', '.join(missing_packages)}")
        
        logger.debug("✅ Dependencies validated")
    
    def _validate_permissions(self):
        """
        Валидация прав доступа
        
        Проверяет права на запись в критические директории.
        """
        logger.debug("Validating permissions...")
        
        # Критические директории
        data_dir = os.getenv('DATA_DIR', '/app/data')
        
        # Создание директории если не существует
        try:
            os.makedirs(data_dir, exist_ok=True)
        except Exception as e:
            self.validation_errors.append(f"Cannot create data directory: {e}")
            raise RuntimeError(f"Cannot create data directory {data_dir}: {e}")
        
        # Проверка прав на запись
        if not os.access(data_dir, os.W_OK):
            self.validation_errors.append(f"No write permission for data directory: {data_dir}")
            raise RuntimeError(f"No write permission for data directory: {data_dir}")
        
        logger.debug("✅ Permissions validated")
    
    def _load_configuration(self) -> Any:
        """
        Загрузка конфигурации приложения
        
        Загружает и возвращает объект конфигурации.
        
        Returns:
            Config: Объект конфигурации
            
        Raises:
            ImportError: Если не удается импортировать Config
            RuntimeError: Если не удается создать Config
        """
        logger.debug("Loading configuration...")
        
        try:
            # Импорт Config из app.config
            from app.config import Config
            
            # Создание экземпляра Config
            config = Config()
            
            logger.debug("✅ Configuration loaded successfully")
            
            return config
        
        except ImportError as e:
            self.validation_errors.append(f"Cannot import Config: {e}")
            logger.error(f"❌ Cannot import Config: {e}", exc_info=True)
            raise ImportError(f"Cannot import Config: {e}") from e
        
        except Exception as e:
            self.validation_errors.append(f"Cannot create Config: {e}")
            logger.error(f"❌ Cannot create Config: {e}", exc_info=True)
            raise RuntimeError(f"Cannot create Config: {e}") from e
    
    def _validate_configuration(self, config: Any):
        """
        Валидация загруженной конфигурации
        
        Проверяет корректность загруженной конфигурации.
        
        Args:
            config: Объект конфигурации для валидации
            
        Raises:
            RuntimeError: Если конфигурация невалидна
        """
        logger.debug("Validating configuration...")
        
        # Проверка обязательных атрибутов
        required_attrs = [
            'TELEGRAM_BOT_TOKEN',
        ]
        
        missing_attrs = []
        for attr in required_attrs:
            if not hasattr(config, attr) or not getattr(config, attr):
                missing_attrs.append(attr)
                self.validation_errors.append(f"Missing required config attribute: {attr}")
        
        if missing_attrs:
            raise RuntimeError(f"Configuration missing required attributes: {', '.join(missing_attrs)}")
        
        # Проверка типов
        try:
            # Проверка что BOT_TOKEN это строка
            token = config.TELEGRAM_BOT_TOKEN
            if not isinstance(token, str):
                raise TypeError(f"TELEGRAM_BOT_TOKEN must be string, got {type(token)}")
            
            if len(token) < 20:
                raise ValueError("TELEGRAM_BOT_TOKEN seems invalid (too short)")
        
        except AttributeError as e:
            self.validation_errors.append(f"Config validation error: {e}")
            raise RuntimeError(f"Config validation error: {e}") from e
        
        logger.debug("✅ Configuration validated")
    
    def get_validation_report(self) -> Dict[str, Any]:
        """
        Получение отчета о валидации
        
        Возвращает детальный отчет о процессе валидации.
        
        Returns:
            Dict[str, Any]: Отчет с ошибками и предупреждениями
        """
        return {
            'errors': self.validation_errors.copy(),
            'warnings': self.validation_warnings.copy(),
            'has_errors': len(self.validation_errors) > 0,
            'has_warnings': len(self.validation_warnings) > 0
        }


__all__ = ['EnvironmentInitializer']