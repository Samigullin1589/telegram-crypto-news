# file: core/tasks/manager.py
"""
Task Manager Module v3.0
Управление всеми фоновыми задачами приложения

Отвечает за:
- Запуск и остановку фоновых задач
- Мониторинг состояния задач
- Координацию между задачами
- Обработку ошибок задач
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List

from .bot_runner import start_bot_task, stop_bot_task, get_bot_task
from .news_runner import start_news_task, stop_news_task, get_news_task
from .whale_runner import start_whale_task, stop_whale_task, get_whale_task
from .trading_runner import start_trading_task, stop_trading_task, get_trading_task
from .database_optimizer_runner import (
    start_database_optimization,
    stop_database_optimization,
    get_optimization_task
)

logger = logging.getLogger(__name__)


class TaskManager:
    """
    Центральный менеджер всех фоновых задач системы
    
    Управляет задачами:
    - Bot task: обработка Telegram команд
    - News task: агрегация и публикация новостей
    - Whale task: мониторинг крупных транзакций
    - Trading task: генерация торговых сигналов
    - Database optimizer: оптимизация БД
    
    Версия 3.0:
    - Автоматическое определение задач из конфигурации
    - Независимый запуск задач
    - Детальное логирование
    - Graceful shutdown всех задач
    """
    
    def __init__(self, config: Any, monitor: Any):
        """
        Инициализация менеджера задач
        
        Args:
            config: Конфигурация приложения
            monitor: Монитор системы с загруженными компонентами
        """
        self.config = config
        self.monitor = monitor
        
        # Хранилище ссылок на задачи
        self.bot_task: Optional[Any] = None
        self.news_task: Optional[Any] = None
        self.whale_task: Optional[Any] = None
        self.trading_task: Optional[Any] = None
        self.database_optimization_task: Optional[Any] = None
        
        # Статистика
        self.started_tasks: List[str] = []
        self.failed_tasks: List[str] = []
        
        logger.info("TaskManager initialized")
    
    async def start_all(self) -> Dict[str, Any]:
        """
        Запуск всех фоновых задач
        
        ИСПРАВЛЕНО: Метод НЕ принимает параметры!
        Все решения о запуске принимаются на основе:
        - config.features.is_enabled()
        - Наличия загруженных компонентов в monitor
        
        Returns:
            Dict[str, Any]: Результаты запуска каждой задачи
            
        Example:
            >>> results = await task_manager.start_all()
            >>> print(results['news']['status'])
            'started'
        """
        logger.info("="*80)
        logger.info("🎯 STARTING ALL BACKGROUND TASKS")
        logger.info("="*80)
        
        results = {
            'news': {'status': 'skipped', 'reason': 'not_enabled'},
            'whale': {'status': 'skipped', 'reason': 'not_enabled'},
            'trading': {'status': 'skipped', 'reason': 'not_enabled'},
            'bot': {'status': 'skipped', 'reason': 'not_loaded'},
            'database_optimization': {'status': 'skipped', 'reason': 'error'}
        }
        
        # Запуск задач параллельно (независимо друг от друга)
        tasks_to_start = []
        
        # 1. News Task
        if self._should_start_news():
            tasks_to_start.append(self._start_news_task(results))
        
        # 2. Whale Task
        if self._should_start_whale():
            tasks_to_start.append(self._start_whale_task(results))
        
        # 3. Trading Task
        if self._should_start_trading():
            tasks_to_start.append(self._start_trading_task(results))
        
        # 4. Bot Task
        if self._should_start_bot():
            tasks_to_start.append(self._start_bot_task(results))
        
        # 5. Database Optimization (всегда)
        tasks_to_start.append(self._start_database_optimization(results))
        
        # Запуск всех задач параллельно
        if tasks_to_start:
            await asyncio.gather(*tasks_to_start, return_exceptions=True)
        
        # Подсчет результатов
        self._log_startup_results(results)
        
        logger.info("="*80)
        
        return results
    
    def _should_start_news(self) -> bool:
        """Проверка нужно ли запускать news task"""
        if not self.config.features.is_enabled('news'):
            logger.debug("News task disabled in config")
            return False
        
        if not hasattr(self.monitor, 'component_manager'):
            logger.warning("Component manager not available")
            return False
        
        if self.monitor.component_manager.news_processor is None:
            logger.warning("News processor not loaded")
            return False
        
        return True
    
    def _should_start_whale(self) -> bool:
        """Проверка нужно ли запускать whale task"""
        if not self.config.features.is_enabled('whale'):
            logger.debug("Whale task disabled in config")
            return False
        
        if not hasattr(self.monitor, 'component_manager'):
            logger.warning("Component manager not available")
            return False
        
        if self.monitor.component_manager.whale_scheduler is None:
            logger.warning("Whale scheduler not loaded")
            return False
        
        return True
    
    def _should_start_trading(self) -> bool:
        """Проверка нужно ли запускать trading task"""
        if not self.config.features.is_enabled('trading'):
            logger.debug("Trading task disabled in config")
            return False
        
        if not hasattr(self.monitor, 'component_manager'):
            logger.warning("Component manager not available")
            return False
        
        if self.monitor.component_manager.trading_system is None:
            logger.warning("Trading system not loaded")
            return False
        
        return True
    
    def _should_start_bot(self) -> bool:
        """Проверка нужно ли запускать bot task"""
        if not hasattr(self.monitor, 'component_manager'):
            logger.warning("Component manager not available")
            return False
        
        if self.monitor.component_manager.bot_app is None:
            logger.warning("Bot application not loaded")
            return False
        
        return True
    
    async def _start_news_task(self, results: Dict[str, Any]):
        """
        Запуск news task

        ИСПРАВЛЕНО: Передаём правильные параметры в start_news_task()
        """
        try:
            logger.info("📰 Starting news task...")

            # ИСПРАВЛЕНИЕ: Передаём все необходимые параметры
            news_processor = self.monitor.component_manager.news_processor
            health_monitor = self.monitor.health_monitor
            resource_monitor = self.monitor.resource_monitor
            statistics = self.monitor.statistics
            shutdown_event = self.monitor.shutdown_event

            self.news_task = await start_news_task(
                news_processor=news_processor,
                health_monitor=health_monitor,
                resource_monitor=resource_monitor,
                statistics=statistics,
                shutdown_event=shutdown_event
            )

            if self.news_task:
                results['news'] = {'status': 'started', 'task_id': id(self.news_task)}
                self.started_tasks.append('news')
                logger.info("✅ News task started successfully")
            else:
                results['news'] = {'status': 'failed', 'reason': 'task_not_created'}
                self.failed_tasks.append('news')
                logger.error("❌ News task failed to start")

        except Exception as e:
            results['news'] = {'status': 'error', 'error': str(e)}
            self.failed_tasks.append('news')
            logger.error(f"❌ Error starting news task: {e}", exc_info=True)
    
    async def _start_whale_task(self, results: Dict[str, Any]):
        """
        Запуск whale task

        ИСПРАВЛЕНО: Передаём правильные параметры в start_whale_task()
        """
        try:
            logger.info("🐋 Starting whale task...")

            # ИСПРАВЛЕНИЕ: Передаём все необходимые параметры
            whale_scheduler = self.monitor.component_manager.whale_scheduler
            health_monitor = self.monitor.health_monitor
            resource_monitor = self.monitor.resource_monitor
            statistics = self.monitor.statistics
            shutdown_event = self.monitor.shutdown_event

            self.whale_task = await start_whale_task(
                whale_scheduler=whale_scheduler,
                health_monitor=health_monitor,
                resource_monitor=resource_monitor,
                statistics=statistics,
                shutdown_event=shutdown_event
            )

            if self.whale_task:
                results['whale'] = {'status': 'started', 'task_id': id(self.whale_task)}
                self.started_tasks.append('whale')
                logger.info("✅ Whale task started successfully")
            else:
                results['whale'] = {'status': 'failed', 'reason': 'task_not_created'}
                self.failed_tasks.append('whale')
                logger.error("❌ Whale task failed to start")

        except Exception as e:
            results['whale'] = {'status': 'error', 'error': str(e)}
            self.failed_tasks.append('whale')
            logger.error(f"❌ Error starting whale task: {e}", exc_info=True)
    
    async def _start_trading_task(self, results: Dict[str, Any]):
        """
        Запуск trading task
        
        ИСПРАВЛЕНО: Передаём правильные параметры в start_trading_task()
        """
        try:
            logger.info("📈 Starting trading task...")
            
            # ИСПРАВЛЕНИЕ: Передаём все необходимые параметры
            trading_system = self.monitor.component_manager.trading_system
            health_monitor = self.monitor.health_monitor
            resource_monitor = self.monitor.resource_monitor
            statistics = self.monitor.statistics
            shutdown_event = self.monitor.shutdown_event
            
            self.trading_task = await start_trading_task(
                trading_system=trading_system,
                health_monitor=health_monitor,
                resource_monitor=resource_monitor,
                statistics=statistics,
                shutdown_event=shutdown_event
            )
            
            if self.trading_task:
                results['trading'] = {'status': 'started', 'task_id': id(self.trading_task)}
                self.started_tasks.append('trading')
                logger.info("✅ Trading task started successfully")
            else:
                results['trading'] = {'status': 'failed', 'reason': 'task_not_created'}
                self.failed_tasks.append('trading')
                logger.error("❌ Trading task failed to start")
                
        except Exception as e:
            results['trading'] = {'status': 'error', 'error': str(e)}
            self.failed_tasks.append('trading')
            logger.error(f"❌ Error starting trading task: {e}", exc_info=True)
    
    async def _start_bot_task(self, results: Dict[str, Any]):
        """
        Запуск bot task
        
        ИСПРАВЛЕНО: Передаём правильные параметры в start_bot_task()
        """
        try:
            logger.info("🤖 Starting bot task...")
            
            # ИСПРАВЛЕНИЕ: Передаём все необходимые параметры
            bot_app = self.monitor.component_manager.bot_app
            health_monitor = self.monitor.health_monitor
            statistics = self.monitor.statistics
            shutdown_event = self.monitor.shutdown_event
            
            self.bot_task = await start_bot_task(
                bot_application=bot_app,
                health_monitor=health_monitor,
                statistics=statistics,
                shutdown_event=shutdown_event
            )
            
            if self.bot_task:
                results['bot'] = {'status': 'started', 'task_id': id(self.bot_task)}
                self.started_tasks.append('bot')
                logger.info("✅ Bot task started successfully")
            else:
                results['bot'] = {'status': 'failed', 'reason': 'task_not_created'}
                self.failed_tasks.append('bot')
                logger.error("❌ Bot task failed to start")
                
        except Exception as e:
            results['bot'] = {'status': 'error', 'error': str(e)}
            self.failed_tasks.append('bot')
            logger.error(f"❌ Error starting bot task: {e}", exc_info=True)
    
    async def _start_database_optimization(self, results: Dict[str, Any]):
        """Запуск database optimization task"""
        try:
            logger.info("💾 Starting database optimization task...")
            
            self.database_optimization_task = await start_database_optimization()
            
            if self.database_optimization_task:
                task_status = self.database_optimization_task.get_status()
                results['database_optimization'] = {
                    'status': 'started',
                    'task_status': task_status
                }
                self.started_tasks.append('database_optimization')
                logger.info("✅ Database optimization task started successfully")
            else:
                results['database_optimization'] = {
                    'status': 'failed',
                    'reason': 'task_not_created'
                }
                self.failed_tasks.append('database_optimization')
                logger.error("❌ Database optimization task failed to start")
                
        except Exception as e:
            results['database_optimization'] = {'status': 'error', 'error': str(e)}
            self.failed_tasks.append('database_optimization')
            logger.error(f"❌ Error starting database optimization: {e}", exc_info=True)
    
    def _log_startup_results(self, results: Dict[str, Any]):
        """Логирование результатов запуска"""
        started = [name for name, data in results.items() if data.get('status') == 'started']
        failed = [name for name, data in results.items() if data.get('status') in ['failed', 'error']]
        skipped = [name for name, data in results.items() if data.get('status') == 'skipped']
        
        logger.info("")
        logger.info("📊 TASK STARTUP SUMMARY")
        logger.info("-" * 80)
        
        if started:
            logger.info(f"✅ Started ({len(started)}): {', '.join(started)}")
        
        if failed:
            logger.warning(f"❌ Failed ({len(failed)}): {', '.join(failed)}")
        
        if skipped:
            logger.info(f"⏭️  Skipped ({len(skipped)}): {', '.join(skipped)}")
        
        logger.info("-" * 80)
    
    async def stop_all(self) -> Dict[str, Any]:
        """
        Остановка всех запущенных задач
        
        Returns:
            Dict[str, Any]: Результаты остановки каждой задачи
        """
        logger.info("Stopping all background tasks...")
        
        results = {}
        
        # Остановка задач параллельно
        stop_tasks = []
        
        if 'news' in self.started_tasks:
            stop_tasks.append(self._stop_news_task(results))
        
        if 'whale' in self.started_tasks:
            stop_tasks.append(self._stop_whale_task(results))
        
        if 'trading' in self.started_tasks:
            stop_tasks.append(self._stop_trading_task(results))
        
        if 'bot' in self.started_tasks:
            stop_tasks.append(self._stop_bot_task(results))
        
        if 'database_optimization' in self.started_tasks:
            stop_tasks.append(self._stop_database_optimization(results))
        
        # Остановка всех задач
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        logger.info(f"✅ Stopped {len(self.started_tasks)} tasks")
        
        self.started_tasks.clear()
        self.failed_tasks.clear()
        
        return results
    
    async def _stop_news_task(self, results: Dict[str, Any]):
        """Остановка news task"""
        try:
            await stop_news_task()
            results['news'] = {'status': 'stopped'}
            logger.info("✅ News task stopped")
        except Exception as e:
            results['news'] = {'status': 'error', 'error': str(e)}
            logger.error(f"❌ Error stopping news task: {e}")
    
    async def _stop_whale_task(self, results: Dict[str, Any]):
        """Остановка whale task"""
        try:
            await stop_whale_task()
            results['whale'] = {'status': 'stopped'}
            logger.info("✅ Whale task stopped")
        except Exception as e:
            results['whale'] = {'status': 'error', 'error': str(e)}
            logger.error(f"❌ Error stopping whale task: {e}")
    
    async def _stop_trading_task(self, results: Dict[str, Any]):
        """Остановка trading task"""
        try:
            await stop_trading_task()
            results['trading'] = {'status': 'stopped'}
            logger.info("✅ Trading task stopped")
        except Exception as e:
            results['trading'] = {'status': 'error', 'error': str(e)}
            logger.error(f"❌ Error stopping trading task: {e}")
    
    async def _stop_bot_task(self, results: Dict[str, Any]):
        """Остановка bot task"""
        try:
            await stop_bot_task()
            results['bot'] = {'status': 'stopped'}
            logger.info("✅ Bot task stopped")
        except Exception as e:
            results['bot'] = {'status': 'error', 'error': str(e)}
            logger.error(f"❌ Error stopping bot task: {e}")
    
    async def _stop_database_optimization(self, results: Dict[str, Any]):
        """Остановка database optimization task"""
        try:
            await stop_database_optimization()
            results['database_optimization'] = {'status': 'stopped'}
            logger.info("✅ Database optimization stopped")
        except Exception as e:
            results['database_optimization'] = {'status': 'error', 'error': str(e)}
            logger.error(f"❌ Error stopping database optimization: {e}")
    
    def get_task_status(self, task_name: str) -> Optional[Dict[str, Any]]:
        """
        Получение статуса конкретной задачи
        
        Args:
            task_name: Имя задачи (news, whale, trading, bot, database_optimization)
            
        Returns:
            Optional[Dict]: Статус задачи или None
        """
        status_getters = {
            'news': get_news_task,
            'whale': get_whale_task,
            'trading': get_trading_task,
            'bot': get_bot_task,
            'database_optimization': get_optimization_task
        }
        
        getter = status_getters.get(task_name)
        if not getter:
            return None
        
        try:
            task = getter()
            if task and hasattr(task, 'get_status'):
                return task.get_status()
        except Exception as e:
            logger.error(f"Error getting status for {task_name}: {e}")
        
        return None
    
    def get_all_tasks_status(self) -> Dict[str, Any]:
        """
        Получение статуса всех задач
        
        Returns:
            Dict: Статусы всех задач
        """
        return {
            'started_tasks': self.started_tasks.copy(),
            'failed_tasks': self.failed_tasks.copy(),
            'news': self.get_task_status('news'),
            'whale': self.get_task_status('whale'),
            'trading': self.get_task_status('trading'),
            'bot': self.get_task_status('bot'),
            'database_optimization': self.get_task_status('database_optimization')
        }


__all__ = ['TaskManager']