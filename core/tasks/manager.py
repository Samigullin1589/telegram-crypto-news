"""
Обновление task manager для включения оптимизации БД
"""

# Добавить в существующий файл core/tasks/manager.py

import logging
from typing import Dict, Any, Optional

from .database_optimizer_runner import (
    DatabaseOptimizationTask,
    start_database_optimization,
    stop_database_optimization,
    get_optimization_task
)

logger = logging.getLogger(__name__)


class TaskManager:
    """
    Главный менеджер задач (существующий класс)
    
    Добавляем интеграцию с оптимизацией БД
    """
    
    def __init__(self):
        # ... существующий код ...
        
        # Добавляем задачу оптимизации БД
        self.database_optimization_task: Optional[DatabaseOptimizationTask] = None
    
    async def start_all(self) -> Dict[str, Any]:
        """Запуск всех задач (обновленный метод)"""
        results = {}
        
        # ... существующий код запуска других задач ...
        
        # Запуск оптимизации БД
        try:
            logger.info("Starting database optimization task")
            self.database_optimization_task = await start_database_optimization()
            results['database_optimization'] = {
                'status': 'started',
                'task_status': self.database_optimization_task.get_status()
            }
        except Exception as e:
            logger.error(f"Failed to start database optimization: {e}", exc_info=True)
            results['database_optimization'] = {
                'status': 'failed',
                'error': str(e)
            }
        
        return results
    
    async def stop_all(self) -> Dict[str, Any]:
        """Остановка всех задач (обновленный метод)"""
        results = {}
        
        # ... существующий код остановки других задач ...
        
        # Остановка оптимизации БД
        try:
            logger.info("Stopping database optimization task")
            await stop_database_optimization()
            results['database_optimization'] = {'status': 'stopped'}
        except Exception as e:
            logger.error(f"Failed to stop database optimization: {e}", exc_info=True)
            results['database_optimization'] = {
                'status': 'error',
                'error': str(e)
            }
        
        return results
    
    def get_task_status(self, task_name: str) -> Optional[Dict[str, Any]]:
        """Получение статуса конкретной задачи"""
        # ... существующий код ...
        
        if task_name == 'database_optimization':
            task = get_optimization_task()
            if task:
                return task.get_status()
        
        return None
    
    def get_all_tasks_status(self) -> Dict[str, Any]:
        """Получение статуса всех задач"""
        status = {}
        
        # ... существующий код для других задач ...
        
        # Статус оптимизации БД
        task = get_optimization_task()
        if task:
            status['database_optimization'] = task.get_status()
        
        return status