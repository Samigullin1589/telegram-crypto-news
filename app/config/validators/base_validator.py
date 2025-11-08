"""
Base Validator
Базовый класс для всех валидаторов конфигурации

Предоставляет общие методы и интерфейс для валидации
различных частей конфигурации системы.
"""

import logging
from typing import List, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from .. import Config

logger = logging.getLogger(__name__)


class BaseValidator:
    """
    Базовый класс валидатора конфигурации
    
    Предоставляет общие методы для всех валидаторов:
    - Сбор ошибок, предупреждений и информационных сообщений
    - Валидация форматов (URL, порты, ключи API)
    - Проверка файловой системы (права доступа)
    - Валидация диапазонов значений
    
    Attributes:
        config: Экземпляр главной конфигурации
        errors: Список критических ошибок
        warnings: Список предупреждений
        info: Список информационных сообщений
    """
    
    def __init__(self, config: 'Config'):
        """
        Инициализация валидатора
        
        Args:
            config: Экземпляр главной конфигурации для валидации
        """
        self.config = config
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
    
    def validate(self) -> List[str]:
        """
        Выполнить валидацию
        
        Этот метод должен быть переопределен в подклассах
        для реализации специфичной логики валидации.
        
        Returns:
            Список всех сообщений валидации
            
        Raises:
            NotImplementedError: Если метод не переопределен в подклассе
        """
        raise NotImplementedError(
            f"Subclass {self.__class__.__name__} must implement validate() method"
        )
    
    # ========================================================================
    # МЕТОДЫ ДЛЯ ДОБАВЛЕНИЯ СООБЩЕНИЙ
    # ========================================================================
    
    def _add_error(self, message: str) -> None:
        """
        Добавить критическую ошибку
        
        Критические ошибки указывают на проблемы, которые
        могут привести к неработоспособности системы.
        
        Args:
            message: Текст сообщения об ошибке
        """
        full_message = f"❌ {message}"
        self.errors.append(full_message)
        logger.error(message)
    
    def _add_warning(self, message: str) -> None:
        """
        Добавить предупреждение
        
        Предупреждения указывают на потенциальные проблемы
        или неоптимальные настройки конфигурации.
        
        Args:
            message: Текст предупреждения
        """
        full_message = f"⚠️  {message}"
        self.warnings.append(full_message)
        logger.warning(message)
    
    def _add_info(self, message: str) -> None:
        """
        Добавить информационное сообщение
        
        Информационные сообщения показывают успешно
        настроенные параметры конфигурации.
        
        Args:
            message: Текст информационного сообщения
        """
        full_message = f"ℹ️  {message}"
        self.info.append(full_message)
        logger.info(message)
    
    def get_all_messages(self) -> List[str]:
        """
        Получить все сообщения валидации
        
        Returns:
            Список всех сообщений в порядке: ошибки, предупреждения, инфо
        """
        return self.errors + self.warnings + self.info
    
    def has_errors(self) -> bool:
        """
        Проверка наличия критических ошибок
        
        Returns:
            True если есть хотя бы одна критическая ошибка
        """
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """
        Проверка наличия предупреждений
        
        Returns:
            True если есть хотя бы одно предупреждение
        """
        return len(self.warnings) > 0
    
    def clear_messages(self) -> None:
        """Очистить все накопленные сообщения"""
        self.errors.clear()
        self.warnings.clear()
        self.info.clear()
    
    # ========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ДЛЯ ВАЛИДАЦИИ
    # ========================================================================
    
    def _validate_key_format(
        self,
        name: str,
        key: str,
        min_length: int = 20,
        prefix: str = None
    ) -> bool:
        """
        Валидация формата API ключа
        
        Проверяет длину ключа и наличие ожидаемого префикса.
        
        Args:
            name: Название сервиса (для сообщений)
            key: API ключ для проверки
            min_length: Минимальная длина ключа
            prefix: Ожидаемый префикс (опционально)
            
        Returns:
            True если ключ валиден, False если есть проблемы
        """
        if not key:
            return False
        
        is_valid = True
        
        # Проверка длины
        if len(key) < min_length:
            self._add_warning(
                f"{name} API ключ короткий (< {min_length} символов, текущая длина: {len(key)})"
            )
            is_valid = False
        
        # Проверка префикса
        if prefix and not key.startswith(prefix):
            self._add_warning(
                f"{name} API ключ не начинается с ожидаемого префикса '{prefix}'"
            )
            is_valid = False
        
        return is_valid
    
    def _can_write_to_directory(self, directory: Path) -> bool:
        """
        Проверка прав на запись в директорию
        
        Args:
            directory: Путь к директории
            
        Returns:
            True если есть права на запись
        """
        if not directory.exists():
            return False
        
        try:
            test_file = directory / '.write_test_temp'
            test_file.touch()
            test_file.unlink()
            return True
        except (PermissionError, OSError) as e:
            logger.debug(f"Cannot write to directory {directory}: {e}")
            return False
    
    def _can_write_to_file(self, file_path: Path) -> bool:
        """
        Проверка прав на запись в файл
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            True если есть права на запись
        """
        if not file_path.exists():
            # Проверяем родительскую директорию
            return self._can_write_to_directory(file_path.parent)
        
        try:
            with open(file_path, 'a') as f:
                pass
            return True
        except (PermissionError, OSError) as e:
            logger.debug(f"Cannot write to file {file_path}: {e}")
            return False
    
    def _validate_port(
        self,
        port: int,
        allow_privileged: bool = False,
        name: str = "Port"
    ) -> bool:
        """
        Валидация номера порта
        
        Args:
            port: Номер порта для проверки
            allow_privileged: Разрешить привилегированные порты (< 1024)
            name: Название параметра (для сообщений)
            
        Returns:
            True если порт валиден
        """
        min_port = 1 if allow_privileged else 1024
        
        if not min_port <= port <= 65535:
            self._add_error(
                f"{name}: некорректное значение {port}. "
                f"Допустимый диапазон: {min_port}-65535"
            )
            return False
        
        if not allow_privileged and port < 1024:
            self._add_warning(
                f"{name}: использование привилегированного порта {port} "
                f"может требовать дополнительных прав"
            )
        
        return True
    
    def _validate_url(
        self,
        url: str,
        name: str = "URL",
        require_https: bool = False
    ) -> bool:
        """
        Валидация URL
        
        Args:
            url: URL для проверки
            name: Название параметра (для сообщений)
            require_https: Требовать обязательно HTTPS
            
        Returns:
            True если URL валиден
        """
        if not url:
            return False
        
        # Проверка протокола
        if not url.startswith(('http://', 'https://')):
            self._add_warning(
                f"{name}: должен начинаться с http:// или https://. Текущее значение: {url}"
            )
            return False
        
        # Проверка HTTPS если требуется
        if require_https and not url.startswith('https://'):
            self._add_warning(
                f"{name}: рекомендуется использовать HTTPS. Текущее значение: {url}"
            )
            return False
        
        return True
    
    def _validate_range(
        self,
        value: float,
        min_val: float,
        max_val: float,
        name: str,
        inclusive: bool = True
    ) -> bool:
        """
        Валидация значения в диапазоне
        
        Args:
            value: Значение для проверки
            min_val: Минимальное значение
            max_val: Максимальное значение
            name: Название параметра
            inclusive: Включать границы диапазона
            
        Returns:
            True если значение в допустимом диапазоне
        """
        if inclusive:
            is_valid = min_val <= value <= max_val
        else:
            is_valid = min_val < value < max_val
        
        if not is_valid:
            operator = "<=" if inclusive else "<"
            self._add_error(
                f"{name}: значение {value} вне допустимого диапазона. "
                f"Ожидается: {min_val} {operator} значение {operator} {max_val}"
            )
            return False
        
        return True
    
    def _validate_positive(
        self,
        value: float,
        name: str,
        allow_zero: bool = False
    ) -> bool:
        """
        Валидация положительного числа
        
        Args:
            value: Значение для проверки
            name: Название параметра
            allow_zero: Разрешить ноль
            
        Returns:
            True если значение положительное (или ноль если разрешено)
        """
        if allow_zero:
            is_valid = value >= 0
            condition = ">= 0"
        else:
            is_valid = value > 0
            condition = "> 0"
        
        if not is_valid:
            self._add_error(
                f"{name}: значение должно быть {condition}. Текущее значение: {value}"
            )
            return False
        
        return True
    
    def _validate_string_not_empty(
        self,
        value: str,
        name: str
    ) -> bool:
        """
        Валидация непустой строки
        
        Args:
            value: Строка для проверки
            name: Название параметра
            
        Returns:
            True если строка не пустая
        """
        if not value or not value.strip():
            self._add_error(f"{name}: не может быть пустым")
            return False
        
        return True
    
    def __repr__(self) -> str:
        """Строковое представление валидатора"""
        return (
            f"{self.__class__.__name__}("
            f"errors={len(self.errors)}, "
            f"warnings={len(self.warnings)}, "
            f"info={len(self.info)}"
            f")"
        )