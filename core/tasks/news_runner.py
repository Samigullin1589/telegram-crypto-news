# core/tasks/news_runner.py
"""
News System Runner v2.0
Улучшенный раннер новостной системы
"""

import asyncio
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class NewsSystemRunner:
    """
    Запуск и управление новостной системой
    
    Улучшения:
    - Лучшая обработка ошибок
    - Адаптивные задержки
    - Мониторинг здоровья системы
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
        
        # Параметры
        self.max_consecutive_errors = 5
        self.base_delay = 30
        self.max_delay = 300
        self.cycle_timeout = 180.0
        self.normal_interval = 300  # 5 минут
    
    async def run(self):
        """Основной цикл новостной системы"""
        logger.info("📰 [NEWS] Запуск News Bot...")
        
        consecutive_errors = 0
        
        # Начальная задержка для стабилизации
        await asyncio.sleep(5)
        
        while not self.shutdown_event.is_set():
            try:
                # Обновление heartbeat
                self.health_monitor.update_news_heartbeat()
                
                # Выполнение цикла обработки
                await self._execute_news_cycle()
                
                # Сброс счетчика ошибок
                consecutive_errors = 0
                
                # Обновление статистики
                self.statistics.increment_news()
                
                # Проверка памяти
                if not self.resource_monitor.check_memory():
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
        
        Raises:
            asyncio.TimeoutError: Если цикл превысил таймаут
            Exception: При других ошибках
        """
        # Проверка инициализации
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
        
        Returns:
            Callable метод или None
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


__all__ = ['NewsSystemRunner']