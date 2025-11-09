# app/config/database/protocols/database.py
"""
Database Operation Protocols
Протоколы для работы с базой данных
"""

from typing import Protocol, Any, Optional, AsyncIterator, runtime_checkable
from collections.abc import AsyncContextManager  # ИСПРАВЛЕНО: было from contextlib


@runtime_checkable
class DatabaseConnectionProtocol(Protocol):
    """Протокол для подключения к БД"""
    
    async def connect(self) -> None:
        """Установка подключения"""
        ...
    
    async def disconnect(self) -> None:
        """Закрытие подключения"""
        ...
    
    async def execute(self, query: str, *args: Any) -> Any:
        """
        Выполнение запроса
        
        Args:
            query: SQL запрос
            *args: Параметры запроса
            
        Returns:
            Результат выполнения
        """
        ...
    
    async def executemany(self, query: str, params: list[tuple]) -> Any:
        """
        Выполнение запроса с множеством параметров
        
        Args:
            query: SQL запрос
            params: Список параметров
            
        Returns:
            Результат выполнения
        """
        ...
    
    async def fetchone(self, query: str, *args: Any) -> Optional[tuple]:
        """
        Получение одной строки
        
        Args:
            query: SQL запрос
            *args: Параметры запроса
            
        Returns:
            Кортеж с данными или None
        """
        ...
    
    async def fetchall(self, query: str, *args: Any) -> list[tuple]:
        """
        Получение всех строк
        
        Args:
            query: SQL запрос
            *args: Параметры запроса
            
        Returns:
            Список кортежей с данными
        """
        ...
    
    async def fetchmany(self, 
                        query: str, 
                        size: int, 
                        *args: Any) -> list[tuple]:
        """
        Получение нескольких строк
        
        Args:
            query: SQL запрос
            size: Количество строк
            *args: Параметры запроса
            
        Returns:
            Список кортежей с данными
        """
        ...
    
    def is_connected(self) -> bool:
        """
        Проверка активности подключения
        
        Returns:
            True если подключение активно
        """
        ...
    
    async def ping(self) -> bool:
        """
        Проверка доступности БД
        
        Returns:
            True если БД отвечает
        """
        ...


@runtime_checkable
class DatabaseTransactionProtocol(Protocol):
    """Протокол для транзакций"""
    
    async def begin(self) -> None:
        """Начало транзакции"""
        ...
    
    async def commit(self) -> None:
        """Фиксация транзакции"""
        ...
    
    async def rollback(self) -> None:
        """Откат транзакции"""
        ...
    
    async def savepoint(self, name: str) -> None:
        """
        Создание точки сохранения
        
        Args:
            name: Имя точки сохранения
        """
        ...
    
    async def release_savepoint(self, name: str) -> None:
        """
        Освобождение точки сохранения
        
        Args:
            name: Имя точки сохранения
        """
        ...
    
    async def rollback_to_savepoint(self, name: str) -> None:
        """
        Откат к точке сохранения
        
        Args:
            name: Имя точки сохранения
        """
        ...
    
    def in_transaction(self) -> bool:
        """
        Проверка активной транзакции
        
        Returns:
            True если транзакция активна
        """
        ...


@runtime_checkable
class DatabaseCursorProtocol(Protocol):
    """Протокол для курсора БД"""
    
    async def execute(self, query: str, *args: Any) -> None:
        """Выполнение запроса"""
        ...
    
    async def executemany(self, query: str, params: list[tuple]) -> None:
        """Выполнение запроса с множеством параметров"""
        ...
    
    async def fetchone(self) -> Optional[tuple]:
        """Получение одной строки"""
        ...
    
    async def fetchall(self) -> list[tuple]:
        """Получение всех строк"""
        ...
    
    async def fetchmany(self, size: int) -> list[tuple]:
        """Получение нескольких строк"""
        ...
    
    async def close(self) -> None:
        """Закрытие курсора"""
        ...
    
    @property
    def rowcount(self) -> int:
        """Количество затронутых строк"""
        ...
    
    @property
    def description(self) -> Optional[list[tuple]]:
        """Описание колонок результата"""
        ...


@runtime_checkable
class DatabasePoolProtocol(Protocol):
    """Протокол для пула соединений"""
    
    async def acquire(self) -> DatabaseConnectionProtocol:
        """
        Получение соединения из пула
        
        Returns:
            Соединение с БД
        """
        ...
    
    async def release(self, connection: DatabaseConnectionProtocol) -> None:
        """
        Возврат соединения в пул
        
        Args:
            connection: Соединение для возврата
        """
        ...
    
    def connection(self) -> AsyncContextManager[DatabaseConnectionProtocol]:
        """
        Контекстный менеджер для соединения
        
        Returns:
            Async context manager для соединения
        """
        ...
    
    async def close(self) -> None:
        """Закрытие пула и всех соединений"""
        ...
    
    def get_size(self) -> int:
        """
        Получение текущего размера пула
        
        Returns:
            Количество соединений в пуле
        """
        ...
    
    def get_free_size(self) -> int:
        """
        Получение количества свободных соединений
        
        Returns:
            Количество свободных соединений
        """
        ...
    
    def is_full(self) -> bool:
        """
        Проверка заполненности пула
        
        Returns:
            True если пул полон
        """
        ...


@runtime_checkable
class DatabaseEngineProtocol(Protocol):
    """Протокол для движка БД"""
    
    def get_name(self) -> str:
        """Название движка"""
        ...
    
    def get_version(self) -> str:
        """Версия движка"""
        ...
    
    def supports_transactions(self) -> bool:
        """Поддержка транзакций"""
        ...
    
    def supports_savepoints(self) -> bool:
        """Поддержка точек сохранения"""
        ...
    
    def supports_async(self) -> bool:
        """Поддержка асинхронных операций"""
        ...
    
    def get_placeholder_style(self) -> str:
        """
        Стиль плейсхолдеров
        
        Returns:
            Стиль (qmark, numeric, named, format, pyformat)
        """
        ...
    
    def get_max_query_size(self) -> Optional[int]:
        """
        Максимальный размер запроса
        
        Returns:
            Размер в байтах или None
        """
        ...