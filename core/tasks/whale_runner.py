# core/tasks/whale_runner.py
"""
Whale System Runner Module
===========================

Модуль управления системой мониторинга крупных транзакций (whale monitoring).

Components:
-----------
- WhaleSystemRunner: Основной класс для запуска whale системы
- Task Management Functions: Функции управления фоновой задачей

Architecture:
-------------
Обеспечивает:
- Выполнение циклов мониторинга whale транзакций
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
import traceback
from typing import Any, Optional

logger = logging.getLogger(__name__)


# Глобальное состояние задачи whale системы
_whale_task: Optional[asyncio.Task] = None


class WhaleSystemRunner:
    """
    Запуск и управление whale monitoring системой
    
    Основной класс для выполнения циклов мониторинга крупных транзакций.
    Обеспечивает адаптивную обработку ошибок и мониторинг.
    
    Responsibilities:
    -----------------
    - Выполнение циклов мониторинга whale транзакций
    - Адаптивные задержки при ошибках
    - Обновление heartbeat
    - Мониторинг ресурсов
    - Сбор статистики
    
    Attributes:
        whale_scheduler: Планировщик whale мониторинга
        health_monitor: Монитор здоровья
        resource_monitor: Монитор ресурсов
        statistics: Сборщик статистики
        shutdown_event: Event для остановки
    """
    
    def __init__(
        self,
        whale_scheduler: Any,
        health_monitor: Any,
        resource_monitor: Any,
        statistics: Any,
        shutdown_event: asyncio.Event
    ):
        """
        Инициализация раннера
        
        Args:
            whale_scheduler: Планировщик whale мониторинга
            health_monitor: Монитор здоровья
            resource_monitor: Монитор ресурсов
            statistics: Сборщик статистики
            shutdown_event: Event для остановки
        """
        self.whale_scheduler = whale_scheduler
        self.health_monitor = health_monitor
        self.resource_monitor = resource_monitor
        self.statistics = statistics
        self.shutdown_event = shutdown_event
        
        # Параметры обработки ошибок
        self.max_consecutive_errors = 5
        self.base_delay = 30
        self.max_delay = 300
        
        # Параметры выполнения
        self.cycle_timeout = 120.0
        self.normal_interval = 1  # Минимальная задержка между циклами
        
        logger.debug("WhaleSystemRunner initialized")
    
    async def run(self):
        """
        Основной цикл whale системы
        
        Выполняет циклы мониторинга whale транзакций с:
        - Обработкой ошибок
        - Адаптивными задержками
        - Мониторингом здоровья
        - Проверкой ресурсов
        
        Обрабатывает:
        - asyncio.TimeoutError: Превышение таймаута цикла
        - asyncio.CancelledError: Отмена задачи
        - Exception: Все остальные ошибки
        """
        logger.info("🐋 [WHALE] Запуск Whale Monitor...")
        
        consecutive_errors = 0
        
        # Начальная задержка для стабилизации
        await asyncio.sleep(10)
        
        while not self.shutdown_event.is_set():
            try:
                # Обновление heartbeat
                self.health_monitor.update_whale_heartbeat()
                
                # Выполнение цикла мониторинга
                await asyncio.wait_for(
                    self.whale_scheduler.run_cycle(),
                    timeout=self.cycle_timeout
                )
                
                # Сброс счетчика ошибок при успехе
                consecutive_errors = 0
                
                # Обновление статистики
                self.statistics.increment_whale()
                
                # Проверка памяти
                if not self.resource_monitor.check_memory():
                    logger.warning("⚠️  [WHALE] Memory pressure detected, slowing down...")
                    await asyncio.sleep(self.base_delay)
                
                # Минимальная задержка между циклами
                await asyncio.sleep(self.normal_interval)
            
            except asyncio.TimeoutError:
                consecutive_errors += 1
                logger.warning(
                    f"⚠️  [WHALE] Cycle timeout ({self.cycle_timeout}s) "
                    f"- error {consecutive_errors}/{self.max_consecutive_errors}"
                )
                await self._handle_error(consecutive_errors)
            
            except asyncio.CancelledError:
                logger.info("🐋 [WHALE] Received shutdown signal")
                break
            
            except Exception as e:
                consecutive_errors += 1
                self.health_monitor.record_error('whale')
                self.statistics.increment_errors()
                
                logger.error(
                    f"❌ [WHALE] Error ({consecutive_errors}/{self.max_consecutive_errors}): {e}",
                    exc_info=True
                )
                
                await self._handle_error(consecutive_errors)
                
                # Проверка критического количества ошибок
                if consecutive_errors >= self.max_consecutive_errors:
                    logger.error("❌ [WHALE] Too many errors, long pause...")
                    await asyncio.sleep(300)  # 5 минут
                    consecutive_errors = 0
                    self.statistics.increment_restarts()
        
        logger.info("🐋 [WHALE] Whale system stopped")
    
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
        
        logger.info(f"⏳ [WHALE] Retry in {delay}s...")
        await asyncio.sleep(delay)


# ==================== Task Management Functions ====================


async def start_whale_task(
    whale_scheduler: Any,
    health_monitor: Any,
    resource_monitor: Any,
    statistics: Any,
    shutdown_event: asyncio.Event
) -> asyncio.Task:
    """
    Запуск фоновой задачи whale системы
    
    Создает и запускает асинхронную задачу с WhaleSystemRunner.
    Задача работает в фоновом режиме до вызова stop_whale_task.
    
    Args:
        whale_scheduler: Планировщик whale мониторинга
        health_monitor: Монитор здоровья системы
        resource_monitor: Монитор ресурсов системы
        statistics: Система сбора статистики
        shutdown_event: Event для graceful shutdown
        
    Returns:
        asyncio.Task: Запущенная задача whale системы
        
    Raises:
        RuntimeError: Если задача уже запущена
        
    Example:
        >>> task = await start_whale_task(
        ...     whale_sched, health_mon, res_mon, stats, shutdown_evt
        ... )
        >>> # Задача работает в фоне
    """
    global _whale_task
    
    if _whale_task and not _whale_task.done():
        raise RuntimeError("Whale task is already running")
    
    logger.info("🚀 [WHALE] Запуск фоновой задачи whale системы...")
    
    # Создание runner
    runner = WhaleSystemRunner(
        whale_scheduler,
        health_monitor,
        resource_monitor,
        statistics,
        shutdown_event
    )
    
    # Запуск задачи
    _whale_task = asyncio.create_task(
        runner.run(),
        name='whale_system_task'
    )
    
    logger.info("✅ [WHALE] Фоновая задача whale системы запущена")
    
    return _whale_task


async def stop_whale_task(timeout: float = 30.0) -> None:
    """
    Остановка фоновой задачи whale системы
    
    Отменяет задачу и ожидает её завершения.
    Гарантирует graceful shutdown через WhaleSystemRunner.
    
    Args:
        timeout: Таймаут ожидания завершения задачи (секунды)
        
    Raises:
        asyncio.TimeoutError: Если задача не завершилась за timeout
        
    Example:
        >>> await stop_whale_task(timeout=30.0)
    """
    global _whale_task
    
    if not _whale_task or _whale_task.done():
        logger.debug("Whale task не запущена или уже завершена")
        return
    
    logger.info("🛑 [WHALE] Остановка фоновой задачи whale системы...")
    
    try:
        # Отмена задачи
        _whale_task.cancel()
        
        # Ожидание завершения
        await asyncio.wait_for(_whale_task, timeout=timeout)
        
        logger.info("✅ [WHALE] Фоновая задача whale системы остановлена")
    
    except asyncio.TimeoutError:
        logger.warning(f"⚠️  [WHALE] Timeout при остановке задачи ({timeout}s)")
        raise
    
    except asyncio.CancelledError:
        logger.info("✅ [WHALE] Задача отменена успешно")
    
    except Exception as e:
        logger.error(f"❌ [WHALE] Ошибка при остановке задачи: {e}")
        traceback.print_exc()
    
    finally:
        _whale_task = None


def get_whale_task() -> Optional[asyncio.Task]:
    """
    Получение ссылки на задачу whale системы
    
    Используется для проверки статуса или ожидания завершения.
    
    Returns:
        Optional[asyncio.Task]: Задача whale системы или None
        
    Example:
        >>> task = get_whale_task()
        >>> if task and not task.done():
        ...     print("Whale system is running")
        >>> else:
        ...     print("Whale system is not running")
    """
    global _whale_task
    return _whale_task


def get_whale_task_status() -> dict:
    """
    Получение детального статуса задачи whale системы
    
    Возвращает информацию о состоянии задачи для мониторинга.
    
    Returns:
        dict: Статус задачи с полями:
            - running: bool - запущена ли задача
            - status: str - статус (not_started/active/cancelled/completed)
            - task_name: str - имя задачи (если запущена)
            - exception: str - информация об ошибке (если есть)
            
    Example:
        >>> status = get_whale_task_status()
        >>> print(f"Running: {status['running']}")
        >>> print(f"Status: {status['status']}")
    """
    global _whale_task
    
    if not _whale_task:
        return {
            'running': False,
            'status': 'not_started'
        }
    
    if _whale_task.done():
        exception = None
        if not _whale_task.cancelled():
            try:
                exception = _whale_task.exception()
            except Exception:
                pass
        
        return {
            'running': False,
            'status': 'cancelled' if _whale_task.cancelled() else 'completed',
            'exception': str(exception) if exception else None
        }
    
    return {
        'running': True,
        'status': 'active',
        'task_name': _whale_task.get_name()
    }


__all__ = [
    'WhaleSystemRunner',
    'start_whale_task',
    'stop_whale_task',
    'get_whale_task',
    'get_whale_task_status'
]