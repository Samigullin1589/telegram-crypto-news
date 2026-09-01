# core/tasks/news_runner.py
"""
News System Runner Module
==========================

Модуль управления новостной системой.

Components:
-----------
- NewsSystemRunner: Основной класс для запуска новостной системы
- Task Management Functions: Функции управления фоновой задачей

Architecture:
-------------
Обеспечивает:
- Выполнение циклов обработки новостей
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


# Глобальное состояние задачи новостной системы
_news_task: Optional[asyncio.Task] = None


class NewsSystemRunner:
    """
    Запуск и управление новостной системой
    
    Основной класс для выполнения циклов обработки новостей.
    Обеспечивает адаптивную обработку ошибок и мониторинг.
    
    Responsibilities:
    -----------------
    - Выполнение циклов обработки новостей
    - Адаптивные задержки при ошибках
    - Обновление heartbeat
    - Мониторинг ресурсов
    - Сбор статистики
    
    Attributes:
        news_processor: Процессор новостей
        health_monitor: Монитор здоровья
        resource_monitor: Монитор ресурсов
        statistics: Сборщик статистики
        shutdown_event: Event для остановки
    """
    
    def __init__(
        self,
        news_processor: Any,
        health_monitor: Any,
        resource_monitor: Any,
        statistics: Any,
        shutdown_event: asyncio.Event
    ):
        """
        Инициализация раннера
        
        Args:
            news_processor: Процессор новостей
            health_monitor: Монитор здоровья
            resource_monitor: Монитор ресурсов
            statistics: Сборщик статистики
            shutdown_event: Event для остановки
        """
        self.news_processor = news_processor
        self.health_monitor = health_monitor
        self.resource_monitor = resource_monitor
        self.statistics = statistics
        self.shutdown_event = shutdown_event
        
        # Параметры обработки ошибок
        self.max_consecutive_errors = 5
        self.base_delay = 30
        self.max_delay = 300
        
        # Параметры выполнения
        self.cycle_timeout = 180.0
        try:
            from app.config import config
            self.normal_interval = int(
                getattr(config.features, 'news_check_interval', 900)
            )
        except Exception:
            self.normal_interval = 900  # 15 минут
        
        logger.debug("NewsSystemRunner initialized")
    
    async def run(self):
        """
        Основной цикл новостной системы
        
        Выполняет циклы обработки новостей с:
        - Обработкой ошибок
        - Адаптивными задержками
        - Мониторингом здоровья
        - Проверкой ресурсов
        
        Обрабатывает:
        - asyncio.TimeoutError: Превышение таймаута цикла
        - asyncio.CancelledError: Отмена задачи
        - Exception: Все остальные ошибки
        """
        logger.info("📰 [NEWS] Запуск News Bot...")
        
        consecutive_errors = 0
        
        # Начальная задержка для стабилизации
        await asyncio.sleep(5)
        
        while not self.shutdown_event.is_set():
            try:
                # Обновление heartbeat
                if hasattr(self.health_monitor, 'update_news_heartbeat'):
                    self.health_monitor.update_news_heartbeat()
                
                # Выполнение цикла обработки
                await self._execute_news_cycle()
                
                # Сброс счетчика ошибок при успехе
                consecutive_errors = 0
                
                # Обновление статистики
                if hasattr(self.statistics, 'increment_news'):
                    self.statistics.increment_news()
                
                # Проверка памяти
                if (
                    hasattr(self.resource_monitor, 'check_memory')
                    and not self.resource_monitor.check_memory()
                ):
                    logger.warning("⚠️  [NEWS] Memory pressure detected")
                    await asyncio.sleep(self.base_delay)
                
                # Нормальная задержка между циклами
                await asyncio.sleep(self.normal_interval)
            
            except asyncio.TimeoutError:
                consecutive_errors += 1
                logger.warning(
                    f"⚠️  [NEWS] Cycle timeout ({self.cycle_timeout}s) "
                    f"- error {consecutive_errors}/{self.max_consecutive_errors}"
                )
                await self._handle_error(consecutive_errors)
            
            except asyncio.CancelledError:
                logger.info("📰 [NEWS] Received shutdown signal")
                break
            
            except Exception as e:
                consecutive_errors += 1
                self.health_monitor.record_error('news')
                self.statistics.increment_errors()
                
                logger.error(
                    f"❌ [NEWS] Error ({consecutive_errors}/{self.max_consecutive_errors}): {e}",
                    exc_info=True
                )
                
                await self._handle_error(consecutive_errors)
                
                # Проверка критического количества ошибок
                if consecutive_errors >= self.max_consecutive_errors:
                    logger.error("❌ [NEWS] Too many errors, long pause...")
                    await asyncio.sleep(self.normal_interval)
                    consecutive_errors = 0
                    self.statistics.increment_restarts()
        
        logger.info("📰 [NEWS] News system stopped")
    
    async def _execute_news_cycle(self):
        """
        Выполнение одного цикла обработки новостей
        
        Проверяет готовность процессора и выполняет
        соответствующий метод обработки.
        
        Raises:
            asyncio.TimeoutError: Если цикл превысил таймаут
            Exception: При других ошибках
        """
        # Проверка готовности процессора
        if not self._is_processor_ready():
            logger.warning("⚠️  [NEWS] Processor not ready")
            await asyncio.sleep(self.base_delay)
            return
        
        # Определение метода для вызова
        cycle_method = self._get_cycle_method()
        
        if cycle_method is None:
            logger.error("❌ [NEWS] No valid cycle method found")
            await asyncio.sleep(self.normal_interval)
            return
        
        # Выполнение с таймаутом
        await asyncio.wait_for(
            cycle_method(),
            timeout=self.cycle_timeout
        )
    
    def _is_processor_ready(self) -> bool:
        """
        Проверка готовности процессора
        
        Проверяет различные атрибуты процессора чтобы
        определить готовность к работе.
        
        Returns:
            True если процессор готов к работе
        """
        if not self.news_processor:
            return False
        
        # Проверка is_initialized
        if hasattr(self.news_processor, 'is_initialized'):
            return self.news_processor.is_initialized
        
        # Проверка state
        if hasattr(self.news_processor, 'state'):
            if hasattr(self.news_processor.state, 'is_ready'):
                return self.news_processor.state.is_ready()
            if hasattr(self.news_processor.state, 'core_initialized'):
                return self.news_processor.state.core_initialized
        
        # По умолчанию считаем готовым
        return True
    
    def _get_cycle_method(self) -> Optional[callable]:
        """
        Определение метода для вызова цикла
        
        Проверяет наличие методов в порядке приоритета:
        1. run_cycle
        2. process_news
        3. run
        
        Returns:
            Callable метод или None если не найден
        """
        # Порядок приоритета методов
        method_names = ['run_cycle', 'process_news', 'run']
        
        for method_name in method_names:
            if hasattr(self.news_processor, method_name):
                method = getattr(self.news_processor, method_name)
                if callable(method):
                    return method
        
        return None
    
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
        
        logger.info(f"⏳ [NEWS] Retry in {delay}s...")
        await asyncio.sleep(delay)


# ==================== Task Management Functions ====================


async def start_news_task(
    news_processor: Any,
    health_monitor: Any,
    resource_monitor: Any,
    statistics: Any,
    shutdown_event: asyncio.Event
) -> asyncio.Task:
    """
    Запуск фоновой задачи новостной системы
    
    Создает и запускает асинхронную задачу с NewsSystemRunner.
    Задача работает в фоновом режиме до вызова stop_news_task.
    
    Args:
        news_processor: Процессор новостей
        health_monitor: Монитор здоровья системы
        resource_monitor: Монитор ресурсов системы
        statistics: Система сбора статистики
        shutdown_event: Event для graceful shutdown
        
    Returns:
        asyncio.Task: Запущенная задача новостной системы
        
    Raises:
        RuntimeError: Если задача уже запущена
        
    Example:
        >>> task = await start_news_task(
        ...     news_proc, health_mon, res_mon, stats, shutdown_evt
        ... )
        >>> # Задача работает в фоне
    """
    global _news_task
    
    if _news_task and not _news_task.done():
        raise RuntimeError("News task is already running")
    
    logger.info("🚀 [NEWS] Запуск фоновой задачи новостной системы...")
    
    # Создание runner
    runner = NewsSystemRunner(
        news_processor,
        health_monitor,
        resource_monitor,
        statistics,
        shutdown_event
    )
    
    # Запуск задачи
    _news_task = asyncio.create_task(
        runner.run(),
        name='news_system_task'
    )
    
    logger.info("✅ [NEWS] Фоновая задача новостной системы запущена")
    
    return _news_task


async def stop_news_task(timeout: float = 30.0) -> None:
    """
    Остановка фоновой задачи новостной системы
    
    Отменяет задачу и ожидает её завершения.
    Гарантирует graceful shutdown через NewsSystemRunner.
    
    Args:
        timeout: Таймаут ожидания завершения задачи (секунды)
        
    Raises:
        asyncio.TimeoutError: Если задача не завершилась за timeout
        
    Example:
        >>> await stop_news_task(timeout=30.0)
    """
    global _news_task
    
    if not _news_task or _news_task.done():
        logger.debug("News task не запущена или уже завершена")
        return
    
    logger.info("🛑 [NEWS] Остановка фоновой задачи новостной системы...")
    
    try:
        # Отмена задачи
        _news_task.cancel()
        
        # Ожидание завершения
        await asyncio.wait_for(_news_task, timeout=timeout)
        
        logger.info("✅ [NEWS] Фоновая задача новостной системы остановлена")
    
    except asyncio.TimeoutError:
        logger.warning(f"⚠️  [NEWS] Timeout при остановке задачи ({timeout}s)")
        raise
    
    except asyncio.CancelledError:
        logger.info("✅ [NEWS] Задача отменена успешно")
    
    except Exception as e:
        logger.error(f"❌ [NEWS] Ошибка при остановке задачи: {e}")
        logger.exception(e)
    
    finally:
        _news_task = None


def get_news_task() -> Optional[asyncio.Task]:
    """
    Получение ссылки на задачу новостной системы
    
    Используется для проверки статуса или ожидания завершения.
    
    Returns:
        Optional[asyncio.Task]: Задача новостной системы или None
        
    Example:
        >>> task = get_news_task()
        >>> if task and not task.done():
        ...     print("News system is running")
        >>> else:
        ...     print("News system is not running")
    """
    global _news_task
    return _news_task


def get_news_task_status() -> dict:
    """
    Получение детального статуса задачи новостной системы
    
    Возвращает информацию о состоянии задачи для мониторинга.
    
    Returns:
        dict: Статус задачи с полями:
            - running: bool - запущена ли задача
            - status: str - статус (not_started/active/cancelled/completed)
            - task_name: str - имя задачи (если запущена)
            - exception: str - информация об ошибке (если есть)
            
    Example:
        >>> status = get_news_task_status()
        >>> print(f"Running: {status['running']}")
        >>> print(f"Status: {status['status']}")
    """
    global _news_task
    
    if not _news_task:
        return {
            'running': False,
            'status': 'not_started'
        }
    
    if _news_task.done():
        exception = None
        if not _news_task.cancelled():
            try:
                exception = _news_task.exception()
            except Exception:
                pass
        
        return {
            'running': False,
            'status': 'cancelled' if _news_task.cancelled() else 'completed',
            'exception': str(exception) if exception else None
        }
    
    return {
        'running': True,
        'status': 'active',
        'task_name': _news_task.get_name()
    }


__all__ = [
    'NewsSystemRunner',
    'start_news_task',
    'stop_news_task',
    'get_news_task',
    'get_news_task_status'
]