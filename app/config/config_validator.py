"""
Configuration Validator v3.0
Главный валидатор конфигурации с модульной архитектурой

Координирует работу всех модульных валидаторов и предоставляет
единый интерфейс для комплексной валидации конфигурации системы.
"""

import logging
from typing import List, Dict, Any, TYPE_CHECKING

from .validators import (
    APIValidator,
    BlockchainValidator,
    FeaturesValidator,
    SystemValidator
)

if TYPE_CHECKING:
    from . import Config

logger = logging.getLogger(__name__)


class ConfigValidator:
    """
    Главный валидатор конфигурации
    
    Использует модульную архитектуру для валидации различных
    частей конфигурации. Каждый модуль валидирует свою область:
    - SystemValidator: базовые настройки, пути, telegram, feeds, database, rate limiting
    - APIValidator: все API ключи
    - BlockchainValidator: блокчейны и whale thresholds
    - FeaturesValidator: функциональные модули и их зависимости
    
    Attributes:
        config: Экземпляр главной конфигурации
        api_validator: Валидатор API ключей
        blockchain_validator: Валидатор блокчейнов
        features_validator: Валидатор функциональных модулей
        system_validator: Валидатор системных настроек
    """
    
    def __init__(self, config: 'Config'):
        """
        Инициализация главного валидатора
        
        Args:
            config: Экземпляр главной конфигурации для валидации
        """
        self.config = config
        
        # Инициализация модульных валидаторов
        logger.debug("Инициализация модульных валидаторов...")
        
        self.system_validator = SystemValidator(config)
        self.api_validator = APIValidator(config)
        self.blockchain_validator = BlockchainValidator(config)
        self.features_validator = FeaturesValidator(config)
        
        logger.debug("Все модульные валидаторы инициализированы")
    
    def validate(self) -> List[str]:
        """
        Комплексная валидация конфигурации
        
        Выполняет валидацию всех модулей в правильном порядке
        и собирает все результаты.
        
        Порядок валидации важен:
        1. System (базовые настройки) - без них ничего не работает
        2. API (ключи) - нужны для работы модулей
        3. Blockchain (сети) - проверяем доступность мониторинга
        4. Features (модули) - проверяем что модули могут работать
        
        Returns:
            Список всех сообщений валидации (ошибки, предупреждения, инфо)
        """
        logger.info("=" * 80)
        logger.info("🔍 Начало комплексной валидации конфигурации")
        logger.info("=" * 80)
        
        all_results = []
        
        try:
            # ================================================================
            # ШАГ 1: СИСТЕМНЫЕ НАСТРОЙКИ
            # ================================================================
            logger.info("📋 Шаг 1/4: Валидация системных настроек...")
            system_results = self.system_validator.validate()
            all_results.extend(system_results)
            
            # Если есть критические ошибки в системе, останавливаемся
            if self.system_validator.has_errors():
                logger.error(
                    f"❌ Найдены критические ошибки в системных настройках ({len(self.system_validator.errors)}). "
                    f"Дальнейшая валидация может быть некорректной"
                )
                # Но продолжаем для полного отчета
            
            # ================================================================
            # ШАГ 2: API КЛЮЧИ
            # ================================================================
            logger.info("📋 Шаг 2/4: Валидация API ключей...")
            api_results = self.api_validator.validate()
            all_results.extend(api_results)
            
            # ================================================================
            # ШАГ 3: БЛОКЧЕЙНЫ
            # ================================================================
            logger.info("📋 Шаг 3/4: Валидация блокчейнов...")
            blockchain_results = self.blockchain_validator.validate()
            all_results.extend(blockchain_results)
            
            # ================================================================
            # ШАГ 4: ФУНКЦИОНАЛЬНЫЕ МОДУЛИ
            # ================================================================
            logger.info("📋 Шаг 4/4: Валидация функциональных модулей...")
            features_results = self.features_validator.validate()
            all_results.extend(features_results)
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка во время валидации: {e}", exc_info=True)
            all_results.append(f"❌ Критическая ошибка валидации: {e}")
        
        # Вывод финальной статистики
        self._print_validation_summary(all_results)
        
        logger.info("=" * 80)
        logger.info("✅ Валидация конфигурации завершена")
        logger.info("=" * 80)
        
        return all_results
    
    def _print_validation_summary(self, results: List[str]) -> None:
        """
        Вывод статистики валидации
        
        Подсчитывает и выводит количество ошибок, предупреждений
        и информационных сообщений.
        
        Args:
            results: Список всех сообщений валидации
        """
        errors = [r for r in results if r.startswith('❌')]
        warnings = [r for r in results if r.startswith('⚠️')]
        info = [r for r in results if r.startswith('ℹ️')]
        
        print()  # Пустая строка для читаемости
        print("=" * 80)
        print("📊 ИТОГИ ВАЛИДАЦИИ КОНФИГУРАЦИИ")
        print("=" * 80)
        
        if errors:
            print(f"❌ Критических ошибок: {len(errors)}")
            logger.error(f"Найдено критических ошибок: {len(errors)}")
            # Выводим первые 5 ошибок для быстрой диагностики
            print("\nПервые ошибки:")
            for i, error in enumerate(errors[:5], 1):
                print(f"  {i}. {error}")
            if len(errors) > 5:
                print(f"  ... и ещё {len(errors) - 5} ошибок")
        
        if warnings:
            print(f"⚠️  Предупреждений: {len(warnings)}")
            logger.warning(f"Найдено предупреждений: {len(warnings)}")
        
        if info:
            print(f"ℹ️  Информационных сообщений: {len(info)}")
            logger.info(f"Информационных сообщений: {len(info)}")
        
        print()
        
        # Итоговая оценка
        if not errors and not warnings:
            print("✨ ОТЛИЧНО! Конфигурация прошла валидацию без ошибок и предупреждений")
            logger.info("✨ Конфигурация валидна")
        elif not errors:
            print("✅ ХОРОШО. Конфигурация рабочая, но есть предупреждения")
            logger.info("✅ Конфигурация рабочая с предупреждениями")
        else:
            print("❌ ВНИМАНИЕ! Найдены критические ошибки. Система может работать нестабильно")
            logger.error("❌ Конфигурация содержит критические ошибки")
        
        print("=" * 80)
    
    def has_critical_errors(self) -> bool:
        """
        Проверка наличия критических ошибок
        
        Критические ошибки - это ошибки которые могут привести
        к неработоспособности системы.
        
        Returns:
            True если есть критические ошибки хотя бы в одном валидаторе
        """
        return (
            self.system_validator.has_errors() or
            self.api_validator.has_errors() or
            self.blockchain_validator.has_errors() or
            self.features_validator.has_errors()
        )
    
    def has_warnings(self) -> bool:
        """
        Проверка наличия предупреждений
        
        Returns:
            True если есть предупреждения хотя бы в одном валидаторе
        """
        return (
            self.system_validator.has_warnings() or
            self.api_validator.has_warnings() or
            self.blockchain_validator.has_warnings() or
            self.features_validator.has_warnings()
        )
    
    def get_error_count(self) -> int:
        """
        Получить общее количество ошибок
        
        Returns:
            Суммарное количество ошибок во всех валидаторах
        """
        return (
            len(self.system_validator.errors) +
            len(self.api_validator.errors) +
            len(self.blockchain_validator.errors) +
            len(self.features_validator.errors)
        )
    
    def get_warning_count(self) -> int:
        """
        Получить общее количество предупреждений
        
        Returns:
            Суммарное количество предупреждений во всех валидаторах
        """
        return (
            len(self.system_validator.warnings) +
            len(self.api_validator.warnings) +
            len(self.blockchain_validator.warnings) +
            len(self.features_validator.warnings)
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Получить полную сводку валидации
        
        Объединяет сводки всех модульных валидаторов
        в единый отчет.
        
        Returns:
            Словарь со статистикой и деталями валидации
        """
        return {
            'total_errors': self.get_error_count(),
            'total_warnings': self.get_warning_count(),
            'has_critical_errors': self.has_critical_errors(),
            'has_warnings': self.has_warnings(),
            'system': self.system_validator.get_summary() if hasattr(self.system_validator, 'get_summary') else {},
            'api': self.api_validator.get_summary() if hasattr(self.api_validator, 'get_summary') else {},
            'blockchain': self.blockchain_validator.get_summary() if hasattr(self.blockchain_validator, 'get_summary') else {},
            'features': self.features_validator.get_summary() if hasattr(self.features_validator, 'get_summary') else {},
        }
    
    def validate_and_raise(self) -> None:
        """
        Валидация с выбросом исключения при критических ошибках
        
        Удобный метод для использования при старте приложения,
        когда нужно остановить запуск при некорректной конфигурации.
        
        Raises:
            ValueError: Если обнаружены критические ошибки конфигурации
        """
        results = self.validate()
        
        if self.has_critical_errors():
            error_messages = [r for r in results if r.startswith('❌')]
            error_text = '\n'.join(error_messages)
            raise ValueError(
                f"Конфигурация содержит критические ошибки:\n{error_text}"
            )
    
    def __repr__(self) -> str:
        """Строковое представление валидатора"""
        return (
            f"ConfigValidator("
            f"errors={self.get_error_count()}, "
            f"warnings={self.get_warning_count()}"
            f")"
        )