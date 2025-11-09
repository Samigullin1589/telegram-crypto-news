# app/config/database/protocols/lifecycle.py
"""
Lifecycle Protocols
Протоколы жизненного цикла компонентов
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class Initializable(Protocol):
    """Протокол для инициализируемых компонентов"""
    
    async def initialize(self) -> None:
        """
        Инициализация компонента
        
        Raises:
            InitializationError: При ошибке инициализации
        """
        ...
    
    def is_initialized(self) -> bool:
        """
        Проверка инициализации
        
        Returns:
            True если компонент инициализирован
        """
        ...


@runtime_checkable
class Shutdownable(Protocol):
    """Протокол для компонентов с корректным завершением"""
    
    async def shutdown(self, timeout: float = 30.0) -> None:
        """
        Корректное завершение работы
        
        Args:
            timeout: Максимальное время ожидания завершения
            
        Raises:
            ShutdownError: При ошибке завершения
        """
        ...
    
    def is_shutdown(self) -> bool:
        """
        Проверка завершения
        
        Returns:
            True если компонент завершен
        """
        ...


@runtime_checkable
class Restartable(Protocol):
    """Протокол для перезапускаемых компонентов"""
    
    async def restart(self, force: bool = False) -> None:
        """
        Перезапуск компонента
        
        Args:
            force: Принудительный перезапуск без graceful shutdown
            
        Raises:
            RestartError: При ошибке перезапуска
        """
        ...
    
    def can_restart(self) -> bool:
        """
        Проверка возможности перезапуска
        
        Returns:
            True если перезапуск возможен
        """
        ...


@runtime_checkable
class Pauseable(Protocol):
    """Протокол для компонентов с паузой"""
    
    async def pause(self) -> None:
        """
        Приостановка работы компонента
        
        Raises:
            PauseError: При ошибке приостановки
        """
        ...
    
    def is_paused(self) -> bool:
        """
        Проверка приостановки
        
        Returns:
            True если компонент на паузе
        """
        ...


@runtime_checkable
class Resumable(Protocol):
    """Протокол для возобновляемых компонентов"""
    
    async def resume(self) -> None:
        """
        Возобновление работы компонента
        
        Raises:
            ResumeError: При ошибке возобновления
        """
        ...
    
    def can_resume(self) -> bool:
        """
        Проверка возможности возобновления
        
        Returns:
            True если возобновление возможно
        """
        ...


@runtime_checkable
class LifecycleManaged(
    Initializable, 
    Shutdownable, 
    Restartable,
    Pauseable,
    Resumable,
    Protocol
):
    """Полный протокол управления жизненным циклом"""
    
    def get_state(self) -> str:
        """
        Получение текущего состояния
        
        Returns:
            Состояние (initializing, running, paused, shutting_down, stopped)
        """
        ...
    
    def get_uptime(self) -> float:
        """
        Получение времени работы
        
        Returns:
            Время в секундах с момента инициализации
        """
        ...