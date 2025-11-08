# core/tasks/task_registry.py
"""
Task Registry
Реестр всех задач системы
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class TaskRegistry:
    """
    Реестр задач системы
    
    Управляет регистрацией и приоритетами задач
    """
    
    def __init__(self):
        """Инициализация реестра"""
        self.tasks: List[Dict[str, Any]] = []
    
    def register_task(
        self,
        name: str,
        component: Any,
        runner_class: str,
        runner_module: str,
        priority: int = 1
    ):
        """
        Регистрация задачи
        
        Args:
            name: Название задачи
            component: Компонент для задачи
            runner_class: Класс раннера
            runner_module: Модуль раннера
            priority: Приоритет (1=высший, 3=низший)
        """
        task_info = {
            'name': name,
            'component': component,
            'runner_class': runner_class,
            'runner_module': runner_module,
            'priority': priority
        }
        
        self.tasks.append(task_info)
        logger.debug(f"📋 [REGISTRY] Registered: {name} (priority={priority})")
    
    def get_tasks_by_priority(self) -> List[Dict[str, Any]]:
        """
        Получение задач отсортированных по приоритету
        
        Returns:
            Список задач
        """
        return sorted(self.tasks, key=lambda t: t['priority'])
    
    def get_task(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Получение задачи по имени
        
        Args:
            name: Название задачи
            
        Returns:
            Информация о задаче или None
        """
        for task in self.tasks:
            if task['name'] == name:
                return task
        return None
    
    def get_task_count(self) -> int:
        """Количество зарегистрированных задач"""
        return len(self.tasks)


__all__ = ['TaskRegistry']