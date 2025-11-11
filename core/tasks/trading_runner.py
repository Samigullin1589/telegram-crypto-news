# core/tasks/trading_runner.py
"""
Trading System Runner Module
=============================

Модуль управления trading системой.

Components:
-----------
- TradingSystemRunner: Основной класс для запуска trading системы
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
from typing import Any, Optional

logger = logging.getLogger(__name__)


# Глобальное состояние задачи trading системы
_trading_task: Optional[asyncio.Task] = None


class TradingSystemRunner:
    """
    Раннер для Trading System
    
    Основной класс для управления циклами анализа и генерации торговых сигналов.
    Обеспечивает адаптивную обработку ошибок и мониторинг.
    
    Responsibilities:
    -----------------
    - Выполнение циклов анализа активов
    - Генерация торговых сигналов
    - Обновление heartbeat
    - Мониторинг ресурсов
    - Сбор статистики
    
    Attributes:
        trading_system: Trading system instance
        health_monitor: Монитор здоровья
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
        shutdown_event: asyncio.Event
    ):
        """
        Инициализация раннера
        
        Args:
            trading_system: Trading system instance
            health_monitor: Монитор здоровья
            resource_monitor: Монитор ресурсов
            statistics: Сборщик статистики
            shutdown_event: Event для остановки
        """
        self.trading_system = trading_system
        self.health_monitor = health_monitor
        self.resource_monitor = resource_monitor
        self.statistics = statistics
        self.shutdown_event = shutdown_event
        
        # Параметры обработки ошибок
        self.max_consecutive_errors = 5
        self.base_delay = 30
        self.max_delay = 300
        
        # Параметры выполнения
        self.check_interval = 300  # 5 минут между циклами
        self.heartbeat_interval = 60  # Heartbeat каждую минуту
        
        logger.debug("TradingSystemRunner initialized")
    
    async def run(self):
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
        
        consecutive_errors = 0
        
        # Начальная задержка для стабилизации
        await asyncio.sleep(30)
        
        while not self.shutdown_event.is_set():
            try:
                # Обновление heartbeat
                self.health_monitor.update_trading_heartbeat()
                
                # Проверка включена ли система
                if not self._is_system_enabled():
                    logger.debug("[TRADING] System disabled, waiting...")
                    await asyncio.sleep(self.check_interval)
                    continue
                
                # Выполнение цикла анализа
                await self._run_trading_cycle()
                
                # Сброс счетчика ошибок при успехе
                consecutive_errors = 0
                
                # Обновление статистики
                self.statistics.increment_trading()
                
                # Проверка памяти
                if not self.resource_monitor.check_memory():
                    logger.warning("⚠️  [TRADING] Memory pressure detected")
                    await asyncio.sleep(self.base_delay)
                
                # Задержка до следующего цикла
                await asyncio.sleep(self.check_interval)
            
            except asyncio.CancelledError:
                logger.info("📈 [TRADING] Received shutdown signal")
                break
            
            except Exception as e:
                consecutive_errors += 1
                self.health_monitor.record_error('trading')
                self.statistics.increment_errors()
                
                logger.error(
                    f"❌ [TRADING] Error ({consecutive_errors}/{self.max_consecutive_errors}): {e}",
                    exc_info=True
                )
                
                await self._handle_error(consecutive_errors)
                
                # Проверка критического количества ошибок
                if consecutive_errors >= self.max_consecutive_errors:
                    logger.error("❌ [TRADING] Too many errors, long pause...")
                    await asyncio.sleep(self.check_interval)
                    consecutive_errors = 0
                    self.statistics.increment_restarts()
        
        logger.info("📈 [TRADING] Trading System stopped")
    
    def _is_system_enabled(self) -> bool:
        """
        Проверка включена ли trading система
        
        Returns:
            True если система включена
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
    
    async def _run_trading_cycle(self):
        """
        Выполнение цикла trading анализа
        
        Проводит анализ активов и генерирует торговые сигналы.
        
        Raises:
            Exception: При ошибках анализа
        """
        logger.debug("[TRADING] Running analysis cycle...")
        
        try:
            # Получение статистики
            stats = await self._get_performance_stats()
            
            if stats:
                logger.debug(
                    f"[TRADING] Stats: "
                    f"signals={stats.get('total_signals', 0)}, "
                    f"trades={stats.get('total_trades', 0)}"
                )
            
            # Выполнение анализа если есть метод
            if hasattr(self.trading_system, 'run_analysis'):
                await self.trading_system.run_analysis()
            
            # Генерация сигналов если есть метод
            if hasattr(self.trading_system, 'generate_signals'):
                await self.trading_system.generate_signals()
        
        except Exception as e:
            logger.error(f"❌ [TRADING] Analysis error: {e}")
            raise
    
    async def _get_performance_stats(self) -> dict:
        """
        Получение статистики производительности
        
        Returns:
            dict: Статистика или пустой dict
        """
        try:
            if hasattr(self.trading_system, 'get_performance_stats'):
                stats = await self.trading_system.get_performance_stats()
                return stats if stats else {}
            return {}
        
        except Exception as e:
            logger.debug(f"[TRADING] Could not get stats: {e}")
            return {}
    
    async def _handle_error(self, consecutive_errors: int):
        """
        Обработка ошибки с адаптивной задержкой
        
        Использует экспоненциальную задержку с ограничением
        максимальной длительности.
        
        Args:
            consecutive_errors: Количество последовательных ошибок
        """
        # Экспоненциальная задержка с ограничением
        delay = min(
            self.base_delay * (2 ** (consecutive_errors - 1)),
            self.max_delay
        )
        
        logger.info(f"⏳ [TRADING] Retry in {delay}s...")
        await asyncio.sleep(delay)


# ==================== Task Management Functions ====================


async def start_trading_task(
    trading_system: Any,
    health_monitor: Any,
    resource_monitor: Any,
    statistics: Any,
    shutdown_event: asyncio.Event
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
        shutdown_event
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


def get_trading_task_status() -> dict:
    """
    Получение детального статуса задачи trading системы
    
    Возвращает информацию о состоянии задачи для мониторинга.
    
    Returns:
        dict: Статус задачи с полями:
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
    'start_trading_task',
    'stop_trading_task',
    'get_trading_task',
    'get_trading_task_status'
]