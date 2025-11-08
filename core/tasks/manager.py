# core/tasks/manager.py
"""
Task Manager v2.0 - Complete System Orchestration
Управление всеми задачами системы с поддержкой всех компонентов
"""

import asyncio
import logging
from typing import Any, List, Set
from datetime import datetime, timezone

from .task_registry import TaskRegistry
from .task_lifecycle import TaskLifecycle
from .task_health import TaskHealthMonitor

logger = logging.getLogger(__name__)


class TaskManager:
    """
    Управление задачами системы
    
    Улучшения v2.0:
    - Поддержка всех компонентов (news, whale, trading, bot)
    - Модульная архитектура
    - Graceful degradation
    - Улучшенная обработка ошибок
    """
    
    def __init__(
        self,
        components: Any,
        health_monitor: Any,
        resource_monitor: Any,
        statistics: Any,
        shutdown_event: asyncio.Event
    ):
        """
        Инициализация Task Manager
        
        Args:
            components: Компоненты системы
            health_monitor: Монитор здоровья
            resource_monitor: Монитор ресурсов
            statistics: Статистика
            shutdown_event: Event для graceful shutdown
        """
        self.components = components
        self.health_monitor = health_monitor
        self.resource_monitor = resource_monitor
        self.statistics = statistics
        self.shutdown_event = shutdown_event
        
        # Реестр задач
        self.registry = TaskRegistry()
        
        # Lifecycle manager
        self.lifecycle = TaskLifecycle(shutdown_event)
        
        # Health monitor для задач
        self.task_health = TaskHealthMonitor(health_monitor, resource_monitor)
        
        # Активные задачи
        self.tasks: List[asyncio.Task] = []
    
    async def start_all_tasks(self):
        """Запуск всех задач системы"""
        self.tasks = []
        
        # Регистрация всех доступных задач
        await self._register_system_tasks()
        
        # Запуск зарегистрированных задач
        await self._start_registered_tasks()
        
        # Системные задачи (всегда запускаются)
        await self._start_system_tasks()
        
        # Логирование запущенных задач
        self._log_started_tasks()
    
    async def _register_system_tasks(self):
        """Регистрация системных задач"""
        # News System
        if self.components.news_processor:
            self.registry.register_task(
                name='news_system',
                component=self.components.news_processor,
                runner_class='NewsSystemRunner',
                runner_module='core.tasks.news_runner',
                priority=2
            )
        else:
            logger.warning("⚠️  [MANAGER] News processor not available")
        
        # Whale System
        if hasattr(self.components, 'whale_scheduler') and self.components.whale_scheduler:
            self.registry.register_task(
                name='whale_system',
                component=self.components.whale_scheduler,
                runner_class='WhaleSystemRunner',
                runner_module='core.tasks.whale_runner',
                priority=2
            )
        else:
            logger.warning("⚠️  [MANAGER] Whale scheduler not available")
        
        # Trading System
        if hasattr(self.components, 'trading_system') and self.components.trading_system:
            if hasattr(self.components.trading_system, 'is_enabled') and self.components.trading_system.is_enabled():
                self.registry.register_task(
                    name='trading_system',
                    component=self.components.trading_system,
                    runner_class='TradingSystemRunner',
                    runner_module='core.tasks.trading_runner',
                    priority=1
                )
            else:
                logger.info("ℹ️  [MANAGER] Trading system disabled")
        else:
            logger.warning("⚠️  [MANAGER] Trading system not available")
        
        # Bot Commands (всегда последний)
        if self.components.bot_application:
            self.registry.register_task(
                name='bot_commands',
                component=self.components.bot_application,
                runner_class='BotWebhookRunner',
                runner_module='core.tasks.bot_runner',
                priority=3
            )
        else:
            logger.error("❌ [MANAGER] Bot application not available")
    
    async def _start_registered_tasks(self):
        """Запуск зарегистрированных задач"""
        for task_info in self.registry.get_tasks_by_priority():
            try:
                task = await self._create_task(task_info)
                if task:
                    self.tasks.append(task)
            
            except Exception as e:
                logger.error(
                    f"❌ [MANAGER] Failed to start {task_info['name']}: {e}",
                    exc_info=True
                )
    
    async def _create_task(self, task_info: dict) -> asyncio.Task:
        """
        Создание задачи
        
        Args:
            task_info: Информация о задаче
            
        Returns:
            Созданная задача или None
        """
        try:
            # Динамический импорт раннера
            module = __import__(
                task_info['runner_module'],
                fromlist=[task_info['runner_class']]
            )
            runner_class = getattr(module, task_info['runner_class'])
            
            # Создание раннера
            runner = runner_class(
                task_info['component'],
                self.health_monitor,
                self.resource_monitor,
                self.statistics,
                self.shutdown_event
            )
            
            # Создание задачи
            task = asyncio.create_task(
                runner.run(),
                name=task_info['name']
            )
            
            logger.debug(f"✅ [MANAGER] Created task: {task_info['name']}")
            return task
        
        except ImportError as e:
            logger.warning(
                f"⚠️  [MANAGER] Runner not available for {task_info['name']}: {e}"
            )
            return None
        
        except Exception as e:
            logger.error(
                f"❌ [MANAGER] Error creating task {task_info['name']}: {e}"
            )
            return None
    
    async def _start_system_tasks(self):
        """Запуск системных задач (мониторинг, координация)"""
        # Health monitor
        self.tasks.append(
            asyncio.create_task(
                self.task_health.run_health_checks(),
                name='health_monitor'
            )
        )
        
        # Coordinator
        self.tasks.append(
            asyncio.create_task(
                self.lifecycle.run_coordination(),
                name='coordinator'
            )
        )
        
        # Shutdown waiter
        self.tasks.append(
            asyncio.create_task(
                self.lifecycle.wait_for_shutdown(),
                name='shutdown_waiter'
            )
        )
    
    def _log_started_tasks(self):
        """Логирование запущенных задач"""
        logger.info(f"\n🚀 Запущено {len(self.tasks)} задач:")
        
        # Группировка по типам
        system_tasks = []
        service_tasks = []
        
        for task in self.tasks:
            name = task.get_name()
            if name in ['health_monitor', 'coordinator', 'shutdown_waiter']:
                system_tasks.append(name)
            else:
                service_tasks.append(name)
        
        if service_tasks:
            logger.info("📦 Сервисы:")
            for name in service_tasks:
                logger.info(f"   • {name}")
        
        if system_tasks:
            logger.info("🔧 Системные:")
            for name in system_tasks:
                logger.info(f"   • {name}")
        
        logger.info("")
    
    async def wait_for_completion(self) -> Set[asyncio.Task]:
        """
        Ожидание завершения первой задачи
        
        Returns:
            Множество завершенных задач
        """
        if not self.tasks:
            logger.warning("⚠️  [MANAGER] No tasks to wait for")
            return set()
        
        done, pending = await asyncio.wait(
            self.tasks,
            return_when=asyncio.FIRST_COMPLETED
        )
        
        return done
    
    async def cancel_all_tasks(self):
        """Отмена всех задач"""
        if not self.tasks:
            logger.debug("[MANAGER] No tasks to cancel")
            return
        
        logger.info("🛑 [MANAGER] Отмена всех задач...")
        
        # Отмена всех задач кроме shutdown_waiter
        for task in self.tasks:
            if not task.done() and task.get_name() != 'shutdown_waiter':
                task.cancel()
                logger.debug(f"   ↳ Отмена: {task.get_name()}")
        
        # Ожидание завершения с таймаутом
        try:
            await asyncio.wait_for(
                asyncio.gather(*self.tasks, return_exceptions=True),
                timeout=30.0
            )
            logger.info("   ✓ Все задачи завершены")
        
        except asyncio.TimeoutError:
            logger.warning("   ⚠️  Timeout ожидания завершения задач")
            
            # Принудительная отмена оставшихся
            for task in self.tasks:
                if not task.done():
                    logger.warning(f"   ⚠️  Принудительная отмена: {task.get_name()}")
                    task.cancel()
    
    def handle_completed_tasks(self, done: Set[asyncio.Task]):
        """
        Обработка завершенных задач
        
        Args:
            done: Множество завершенных задач
        """
        for task in done:
            task_name = task.get_name()
            
            # Shutdown waiter - нормальное завершение
            if task_name == 'shutdown_waiter':
                logger.info("✅ Получен сигнал graceful shutdown")
                continue
            
            # Проверка исключений
            try:
                exc = task.exception()
                
                if exc:
                    self._handle_task_exception(task_name, exc)
                else:
                    self._handle_task_completion(task_name)
            
            except asyncio.CancelledError:
                logger.debug(f"✓ Task '{task_name}' cancelled")
            
            except Exception as e:
                logger.error(f"❌ Error handling task '{task_name}': {e}")
    
    def _handle_task_exception(self, task_name: str, exc: Exception):
        """Обработка исключения в задаче"""
        import traceback
        
        logger.error(f"\n❌ [CRITICAL] Task '{task_name}' crashed:")
        logger.error("=" * 80)
        traceback.print_exception(type(exc), exc, exc.__traceback__)
        logger.error("=" * 80)
        
        self.statistics.increment_errors()
    
    def _handle_task_completion(self, task_name: str):
        """Обработка завершения задачи без ошибок"""
        logger.warning(f"⚠️  Task '{task_name}' завершилась без ошибок")
    
    def get_status(self) -> dict:
        """
        Получение статуса Task Manager
        
        Returns:
            Dict со статусом
        """
        return {
            'total_tasks': len(self.tasks),
            'running_tasks': sum(1 for t in self.tasks if not t.done()),
            'completed_tasks': sum(1 for t in self.tasks if t.done()),
            'tasks': [
                {
                    'name': task.get_name(),
                    'done': task.done(),
                    'cancelled': task.cancelled()
                }
                for task in self.tasks
            ]
        }


__all__ = ['TaskManager']