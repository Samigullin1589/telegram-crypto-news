# core/tasks/trading_runner.py
"""
Trading System Runner Module
=============================

Модуль управления trading системой с полным разделением ответственности.

Components:
-----------
- TradingSystemRunner: Основной класс для запуска trading системы
- TradingCycleExecutor: Выполнение циклов анализа
- TradingErrorHandler: Обработка ошибок с адаптивными задержками
- TradingHeartbeatManager: Управление heartbeat
- Task Management Functions: Функции управления фоновой задачей

Architecture:
-------------
Обеспечивает:
- Выполнение циклов анализа и генерации сигналов
- Адаптивные задержки при ошибках
- Мониторинг здоровья системы
- Управление жизненным циклом задачи

Production Ready:
-----------------
- Полная обработка ошибок
- Таймауты для операций
- Метрики и мониторинг
- Корректное завершение
"""

import asyncio
import logging
from typing import Any, Optional, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# Глобальное состояние задачи trading системы
_trading_task: Optional[asyncio.Task] = None


@dataclass
class TradingRunnerConfig:
    """
    Конфигурация trading runner
    
    Attributes:
        check_interval: Интервал между циклами (секунды)
        heartbeat_interval: Интервал heartbeat (секунды)
        max_consecutive_errors: Максимум последовательных ошибок
        base_delay: Базовая задержка при ошибке (секунды)
        max_delay: Максимальная задержка при ошибках (секунды)
        initial_delay: Начальная задержка при старте (секунды)
    """
    check_interval: int = 300
    heartbeat_interval: int = 60
    max_consecutive_errors: int = 5
    base_delay: int = 30
    max_delay: int = 300
    initial_delay: int = 30


class TradingHeartbeatManager:
    """
    Менеджер heartbeat для trading системы
    
    Responsibilities:
    -----------------
    - Отправка heartbeat в health monitor
    - Отслеживание последнего heartbeat
    - Валидация health monitor
    """
    
    def __init__(self, health_monitor: Any):
        """
        Инициализация менеджера heartbeat
        
        Args:
            health_monitor: Монитор здоровья системы
        """
        self.health_monitor = health_monitor
        logger.debug("[TRADING-HB] HeartbeatManager initialized")
    
    def send_heartbeat(self) -> None:
        """
        Отправка heartbeat в health monitor
        
        Использует метод update_trading_heartbeat()
        """
        try:
            if hasattr(self.health_monitor, 'update_trading_heartbeat'):
                self.health_monitor.update_trading_heartbeat()
                logger.debug("[TRADING-HB] Heartbeat sent")
            else:
                logger.warning("[TRADING-HB] Health monitor has no update_trading_heartbeat method")
        
        except Exception as e:
            logger.error(f"[TRADING-HB] Error sending heartbeat: {e}")
    
    def is_health_monitor_valid(self) -> bool:
        """
        Проверка валидности health monitor
        
        Returns:
            bool: True если health monitor имеет необходимые методы
        """
        return hasattr(self.health_monitor, 'update_trading_heartbeat')


class TradingErrorHandler:
    """
    Обработчик ошибок с адаптивными задержками
    
    Responsibilities:
    -----------------
    - Подсчет последовательных ошибок
    - Расчет адаптивных задержек
    - Регистрация ошибок в системах мониторинга
    """
    
    def __init__(
        self,
        config: TradingRunnerConfig,
        health_monitor: Any,
        statistics: Any
    ):
        """
        Инициализация обработчика ошибок
        
        Args:
            config: Конфигурация runner
            health_monitor: Монитор здоровья
            statistics: Сборщик статистики
        """
        self.config = config
        self.health_monitor = health_monitor
        self.statistics = statistics
        self.consecutive_errors = 0
        
        logger.debug("[TRADING-ERR] ErrorHandler initialized")
    
    def record_error(self, error: Exception) -> None:
        """
        Регистрация ошибки
        
        Args:
            error: Произошедшая ошибка
        """
        self.consecutive_errors += 1
        
        # Регистрация в health monitor
        if hasattr(self.health_monitor, 'record_error'):
            self.health_monitor.record_error('trading')
        
        # Регистрация в статистике
        if hasattr(self.statistics, 'increment_errors'):
            self.statistics.increment_errors()
        
        logger.error(
            f"❌ [TRADING-ERR] Error ({self.consecutive_errors}/{self.config.max_consecutive_errors}): {error}",
            exc_info=True
        )
    
    def reset_error_counter(self) -> None:
        """Сброс счетчика ошибок после успешного выполнения"""
        if self.consecutive_errors > 0:
            logger.debug(f"[TRADING-ERR] Resetting error counter (was {self.consecutive_errors})")
            self.consecutive_errors = 0
    
    def get_delay(self) -> float:
        """
        Расчет задержки на основе количества ошибок
        
        Использует экспоненциальную задержку с ограничением.
        
        Returns:
            float: Задержка в секундах
        """
        delay = min(
            self.config.base_delay * (2 ** (self.consecutive_errors - 1)),
            self.config.max_delay
        )
        return delay
    
    async def handle_error(self) -> None:
        """
        Обработка ошибки с задержкой
        
        Выполняет адаптивную задержку перед повтором.
        """
        delay = self.get_delay()
        logger.info(f"⏳ [TRADING-ERR] Retry in {delay}s...")
        await asyncio.sleep(delay)
    
    def is_critical_error_count(self) -> bool:
        """
        Проверка достижения критического количества ошибок
        
        Returns:
            bool: True если достигнут предел ошибок
        """
        return self.consecutive_errors >= self.config.max_consecutive_errors
    
    async def handle_critical_errors(self) -> None:
        """Обработка критического количества ошибок"""
        logger.error("❌ [TRADING-ERR] Too many consecutive errors, long pause...")
        await asyncio.sleep(self.config.check_interval)
        self.consecutive_errors = 0
        
        if hasattr(self.statistics, 'increment_restarts'):
            self.statistics.increment_restarts()


class TradingCycleExecutor:
    """
    Исполнитель циклов trading анализа
    
    Responsibilities:
    -----------------
    - Выполнение анализа активов
    - Генерация торговых сигналов
    - Получение статистики производительности
    """
    
    def __init__(self, trading_system: Any):
        """
        Инициализация исполнителя
        
        Args:
            trading_system: Trading system instance
        """
        self.trading_system = trading_system
        logger.debug("[TRADING-EXEC] CycleExecutor initialized")
    
    def is_system_enabled(self) -> bool:
        """
        Проверка включена ли trading система
        
        Returns:
            bool: True если система включена
        """
        if not self.trading_system:
            return False
        
        # Проверка метода is_enabled
        if hasattr(self.trading_system, 'is_enabled'):
            return self.trading_system.is_enabled()
        
        # Проверка атрибута enabled
        if hasattr(self.trading_system, 'enabled'):
            return self.trading_system.enabled
        
        # По умолчанию считаем включенной
        return True
    
    async def execute_cycle(self) -> None:
        """
        Выполнение цикла trading анализа
        
        Проводит анализ активов и генерирует торговые сигналы.
        
        Raises:
            Exception: При ошибках анализа
        """
        logger.debug("[TRADING-EXEC] Running analysis cycle...")
        
        # Получение статистики
        stats = await self._get_performance_stats()
        
        if stats:
            logger.debug(
                f"[TRADING-EXEC] Stats: "
                f"signals={stats.get('total_signals', 0)}, "
                f"trades={stats.get('total_trades', 0)}"
            )
        
        # Выполнение анализа
        await self._run_analysis()
        
        # Генерация сигналов
        await self._generate_signals()
        
        logger.debug("[TRADING-EXEC] Cycle completed")
    
    async def _run_analysis(self) -> None:
        """Выполнение анализа если метод доступен"""
        if hasattr(self.trading_system, 'run_analysis'):
            await self.trading_system.run_analysis()
    
    async def _generate_signals(self) -> None:
        """Генерация сигналов если метод доступен"""
        if hasattr(self.trading_system, 'generate_signals'):
            await self.trading_system.generate_signals()
    
    async def _get_performance_stats(self) -> Dict[str, Any]:
        """
        Получение статистики производительности
        
        Returns:
            Dict[str, Any]: Статистика или пустой dict
        """
        try:
            if hasattr(self.trading_system, 'get_performance_stats'):
                stats = await self.trading_system.get_performance_stats()
                return stats if stats else {}
            return {}
        
        except Exception as e:
            logger.debug(f"[TRADING-EXEC] Could not get stats: {e}")
            return {}


class TradingSystemRunner:
    """
    Раннер для Trading System
    
    Основной класс для управления циклами анализа и генерации торговых сигналов.
    Обеспечивает адаптивную обработку ошибок и мониторинг.
    
    Responsibilities:
    -----------------
    - Координация компонентов trading системы
    - Управление жизненным циклом
    - Мониторинг ресурсов
    - Сбор статистики
    
    Attributes:
        config: Конфигурация runner
        heartbeat_manager: Менеджер heartbeat
        error_handler: Обработчик ошибок
        cycle_executor: Исполнитель циклов
        resource_monitor: Монитор ресурсов
        statistics: Сборщик статистики
        shutdown_event: Event для остановки
    """
    
    def __init__(
        self,
        trading_system: Any,
        health_monitor: Any,
        resource_monitor: Any,
        statistics: Any,
        shutdown_event: asyncio.Event,
        config: Optional[TradingRunnerConfig] = None
    ):
        """
        Инициализация раннера
        
        Args:
            trading_system: Trading system instance
            health_monitor: Монитор здоровья
            resource_monitor: Монитор ресурсов
            statistics: Сборщик статистики
            shutdown_event: Event для остановки
            config: Конфигурация (опционально)
        """
        self.config = config or TradingRunnerConfig()
        self.resource_monitor = resource_monitor
        self.statistics = statistics
        self.shutdown_event = shutdown_event
        
        # Инициализация компонентов
        self.heartbeat_manager = TradingHeartbeatManager(health_monitor)
        self.error_handler = TradingErrorHandler(
            self.config,
            health_monitor,
            statistics
        )
        self.cycle_executor = TradingCycleExecutor(trading_system)
        
        logger.debug("[TRADING] TradingSystemRunner initialized")
    
    async def run(self) -> None:
        """
        Основной цикл trading системы
        
        Выполняет циклы анализа и генерации сигналов с:
        - Обработкой ошибок
        - Адаптивными задержками
        - Мониторингом здоровья
        - Проверкой ресурсов
        
        Обрабатывает:
        - asyncio.CancelledError: Отмена задачи
        - Exception: Все остальные ошибки
        """
        logger.info("📈 [TRADING] Starting Trading System...")
        
        # Начальная задержка для стабилизации
        await asyncio.sleep(self.config.initial_delay)
        
        while not self.shutdown_event.is_set():
            try:
                # Обновление heartbeat
                self.heartbeat_manager.send_heartbeat()
                
                # Проверка включена ли система
                if not self.cycle_executor.is_system_enabled():
                    logger.debug("[TRADING] System disabled, waiting...")
                    await asyncio.sleep(self.config.check_interval)
                    continue
                
                # Выполнение цикла анализа
                await self.cycle_executor.execute_cycle()
                
                # Сброс счетчика ошибок при успехе
                self.error_handler.reset_error_counter()
                
                # Обновление статистики
                if hasattr(self.statistics, 'increment_trading'):
                    self.statistics.increment_trading()
                
                # Проверка памяти
                await self._check_resources()
                
                # Задержка до следующего цикла
                await asyncio.sleep(self.config.check_interval)
            
            except asyncio.CancelledError:
                logger.info("📈 [TRADING] Received shutdown signal")
                break
            
            except Exception as e:
                # Регистрация ошибки
                self.error_handler.record_error(e)
                
                # Обработка ошибки с задержкой
                await self.error_handler.handle_error()
                
                # Проверка критического количества ошибок
                if self.error_handler.is_critical_error_count():
                    await self.error_handler.handle_critical_errors()
        
        logger.info("📈 [TRADING] Trading System stopped")
    
    async def _check_resources(self) -> None:
        """
        Проверка ресурсов системы
        
        Проверяет память и при необходимости делает паузу.
        """
        if not self.resource_monitor:
            return
        
        if hasattr(self.resource_monitor, 'check_memory'):
            if not self.resource_monitor.check_memory():
                logger.warning("⚠️  [TRADING] Memory pressure detected")
                await asyncio.sleep(self.config.base_delay)


# ==================== Task Management Functions ====================


async def start_trading_task(
    trading_system: Any,
    health_monitor: Any,
    resource_monitor: Any,
    statistics: Any,
    shutdown_event: asyncio.Event,
    config: Optional[TradingRunnerConfig] = None
) -> asyncio.Task:
    """
    Запуск фоновой задачи trading системы
    
    Создает и запускает асинхронную задачу с TradingSystemRunner.
    Задача работает в фоновом режиме до вызова stop_trading_task.
    
    Args:
        trading_system: Trading system instance
        health_monitor: Монитор здоровья системы
        resource_monitor: Монитор ресурсов системы
        statistics: Система сбора статистики
        shutdown_event: Event для graceful shutdown
        config: Конфигурация runner (опционально)
        
    Returns:
        asyncio.Task: Запущенная задача trading системы
        
    Raises:
        RuntimeError: Если задача уже запущена
        
    Example:
        >>> task = await start_trading_task(
        ...     trading_sys, health_mon, res_mon, stats, shutdown_evt
        ... )
        >>> # Задача работает в фоне
    """
    global _trading_task
    
    if _trading_task and not _trading_task.done():
        raise RuntimeError("Trading task is already running")
    
    logger.info("🚀 [TRADING] Запуск фоновой задачи trading системы...")
    
    # Создание runner
    runner = TradingSystemRunner(
        trading_system,
        health_monitor,
        resource_monitor,
        statistics,
        shutdown_event,
        config
    )
    
    # Запуск задачи
    _trading_task = asyncio.create_task(
        runner.run(),
        name='trading_system_task'
    )
    
    logger.info("✅ [TRADING] Фоновая задача trading системы запущена")
    
    return _trading_task


async def stop_trading_task(timeout: float = 30.0) -> None:
    """
    Остановка фоновой задачи trading системы
    
    Отменяет задачу и ожидает её завершения.
    Гарантирует graceful shutdown через TradingSystemRunner.
    
    Args:
        timeout: Таймаут ожидания завершения задачи (секунды)
        
    Raises:
        asyncio.TimeoutError: Если задача не завершилась за timeout
        
    Example:
        >>> await stop_trading_task(timeout=30.0)
    """
    global _trading_task
    
    if not _trading_task or _trading_task.done():
        logger.debug("Trading task не запущена или уже завершена")
        return
    
    logger.info("🛑 [TRADING] Остановка фоновой задачи trading системы...")
    
    try:
        # Отмена задачи
        _trading_task.cancel()
        
        # Ожидание завершения
        await asyncio.wait_for(_trading_task, timeout=timeout)
        
        logger.info("✅ [TRADING] Фоновая задача trading системы остановлена")
    
    except asyncio.TimeoutError:
        logger.warning(f"⚠️  [TRADING] Timeout при остановке задачи ({timeout}s)")
        raise
    
    except asyncio.CancelledError:
        logger.info("✅ [TRADING] Задача отменена успешно")
    
    except Exception as e:
        logger.error(f"❌ [TRADING] Ошибка при остановке задачи: {e}")
        logger.exception(e)
    
    finally:
        _trading_task = None


def get_trading_task() -> Optional[asyncio.Task]:
    """
    Получение ссылки на задачу trading системы
    
    Используется для проверки статуса или ожидания завершения.
    
    Returns:
        Optional[asyncio.Task]: Задача trading системы или None
        
    Example:
        >>> task = get_trading_task()
        >>> if task and not task.done():
        ...     print("Trading system is running")
        >>> else:
        ...     print("Trading system is not running")
    """
    global _trading_task
    return _trading_task


def get_trading_task_status() -> Dict[str, Any]:
    """
    Получение детального статуса задачи trading системы
    
    Возвращает информацию о состоянии задачи для мониторинга.
    
    Returns:
        Dict[str, Any]: Статус задачи с полями:
            - running: bool - запущена ли задача
            - status: str - статус (not_started/active/cancelled/completed)
            - task_name: str - имя задачи (если запущена)
            - exception: str - информация об ошибке (если есть)
            
    Example:
        >>> status = get_trading_task_status()
        >>> print(f"Running: {status['running']}")
        >>> print(f"Status: {status['status']}")
    """
    global _trading_task
    
    if not _trading_task:
        return {
            'running': False,
            'status': 'not_started'
        }
    
    if _trading_task.done():
        exception = None
        if not _trading_task.cancelled():
            try:
                exception = _trading_task.exception()
            except Exception:
                pass
        
        return {
            'running': False,
            'status': 'cancelled' if _trading_task.cancelled() else 'completed',
            'exception': str(exception) if exception else None
        }
    
    return {
        'running': True,
        'status': 'active',
        'task_name': _trading_task.get_name()
    }


__all__ = [
    'TradingSystemRunner',
    'TradingRunnerConfig',
    'TradingHeartbeatManager',
    'TradingErrorHandler',
    'TradingCycleExecutor',
    'start_trading_task',
    'stop_trading_task',
    'get_trading_task',
    'get_trading_task_status'
]