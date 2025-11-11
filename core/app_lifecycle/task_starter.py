"""
Task starter module
Запуск фоновых задач приложения
"""

import logging
import asyncio
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class TaskStarter:
    """
    Менеджер запуска фоновых задач
    
    Отвечает за запуск и управление всеми фоновыми задачами
    приложения на основе включенных модулей
    """
    
    def __init__(self, config: Any, monitor: Any, task_manager: Any):
        """
        Инициализация запускателя задач
        
        Args:
            config: Конфигурация приложения
            monitor: Монитор системы
            task_manager: Менеджер задач
        """
        self.config = config
        self.monitor = monitor
        self.task_manager = task_manager
        self.started_tasks: List[str] = []
    
    async def start_all_tasks(self) -> Dict[str, Any]:
        """
        Запуск всех фоновых задач
        
        Returns:
            Dict: Результаты запуска задач
        """
        logger.info("="*80)
        logger.info("🎯 STARTING BACKGROUND TASKS")
        logger.info("="*80)
        
        results = {
            'news': False,
            'whale': False,
            'trading': False,
            'bot': False,
            'database_optimizer': False,
            'errors': []
        }
        
        try:
            # Определение каких задач нужно запускать
            tasks_to_start = self._determine_tasks_to_start()
            
            logger.info(f"📋 Tasks to start: {', '.join(tasks_to_start)}")
            
            # ИСПРАВЛЕНИЕ: Используем правильную сигнатуру start_all()
            # Убираем параметр enable_database_optimization
            task_results = await self.task_manager.start_all()
            
            # Обработка результатов
            results = self._process_task_results(task_results, tasks_to_start)
            
            # Логирование успешных запусков
            self._log_task_results(results)
            
        except Exception as e:
            error_msg = f"Error starting background tasks: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            results['errors'].append(error_msg)
        
        logger.info("="*80)
        
        return results
    
    def _determine_tasks_to_start(self) -> List[str]:
        """
        Определение какие задачи нужно запускать
        
        Returns:
            List[str]: Список задач для запуска
        """
        tasks = []
        
        # Проверка включенных модулей
        if self.config.features.is_enabled('news'):
            tasks.append('news')
        
        if self.config.features.is_enabled('whale'):
            tasks.append('whale')
        
        if self.config.features.is_enabled('trading'):
            tasks.append('trading')
        
        # Бот запускается всегда если загружен
        if self.monitor.component_manager.bot_app is not None:
            tasks.append('bot')
        
        # Database optimizer запускается всегда
        tasks.append('database_optimizer')
        
        return tasks
    
    def _process_task_results(self, task_results: Any, 
                              expected_tasks: List[str]) -> Dict[str, Any]:
        """
        Обработка результатов запуска задач
        
        Args:
            task_results: Результаты от task_manager
            expected_tasks: Ожидаемые задачи
            
        Returns:
            Dict: Обработанные результаты
        """
        results = {
            'news': False,
            'whale': False,
            'trading': False,
            'bot': False,
            'database_optimizer': False,
            'errors': []
        }
        
        # Если task_results это словарь с результатами
        if isinstance(task_results, dict):
            for task_name in expected_tasks:
                if task_name in task_results:
                    results[task_name] = task_results[task_name]
                    if task_results[task_name]:
                        self.started_tasks.append(task_name)
        
        # Если task_results это булево значение (все успешно/неуспешно)
        elif isinstance(task_results, bool):
            for task_name in expected_tasks:
                results[task_name] = task_results
                if task_results:
                    self.started_tasks.append(task_name)
        
        return results
    
    def _log_task_results(self, results: Dict[str, Any]):
        """
        Логирование результатов запуска задач
        
        Args:
            results: Результаты запуска
        """
        successful = [name for name, status in results.items() 
                     if name != 'errors' and status]
        failed = [name for name, status in results.items() 
                 if name != 'errors' and not status]
        
        if successful:
            logger.info(f"✅ Successfully started tasks: {', '.join(successful)}")
        
        if failed:
            logger.warning(f"⚠️  Failed to start tasks: {', '.join(failed)}")
        
        if results.get('errors'):
            logger.error(f"❌ Errors during task startup:")
            for error in results['errors']:
                logger.error(f"   - {error}")
    
    async def stop_all_tasks(self):
        """Остановка всех запущенных задач"""
        if not self.started_tasks:
            logger.info("No tasks to stop")
            return
        
        logger.info(f"Stopping {len(self.started_tasks)} tasks...")
        
        try:
            await self.task_manager.stop_all()
            logger.info("✅ All tasks stopped successfully")
        except Exception as e:
            logger.error(f"❌ Error stopping tasks: {e}", exc_info=True)
        
        self.started_tasks.clear()
    
    def get_running_tasks(self) -> List[str]:
        """
        Получение списка запущенных задач
        
        Returns:
            List[str]: Список имен запущенных задач
        """
        return self.started_tasks.copy()


__all__ = ['TaskStarter']