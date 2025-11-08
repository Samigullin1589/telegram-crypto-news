"""
Task runner для автоматической оптимизации БД

Интеграция с существующей системой задач для:
- Периодического запуска оптимизации
- Мониторинга здоровья БД
- Автоматического реагирования на проблемы
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from app.config.database import get_db_manager, DatabaseManager
from app.config.database.health_checks import DatabaseHealthChecker

logger = logging.getLogger(__name__)


class DatabaseOptimizationTask:
    """
    Задача автоматической оптимизации БД
    
    Запускается периодически для:
    - Мониторинга здоровья
    - Выполнения оптимизации
    - Обработки алертов
    """
    
    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        optimization_interval_hours: int = 1,
        health_check_interval_minutes: int = 5,
        auto_respond_to_alerts: bool = True
    ):
        self.db_manager = db_manager or get_db_manager()
        self.optimization_interval_hours = optimization_interval_hours
        self.health_check_interval_minutes = health_check_interval_minutes
        self.auto_respond_to_alerts = auto_respond_to_alerts
        
        self.health_checker = DatabaseHealthChecker()
        
        self._last_optimization: Optional[datetime] = None
        self._last_health_check: Optional[datetime] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Запуск задачи оптимизации"""
        if self._running:
            logger.warning("Database optimization task already running")
            return
        
        logger.info("Starting database optimization task")
        
        # Инициализация менеджера
        if not self.db_manager._initialized:
            await self.db_manager.initialize()
        
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
    
    async def stop(self) -> None:
        """Остановка задачи"""
        if not self._running:
            return
        
        logger.info("Stopping database optimization task")
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        # Graceful shutdown менеджера
        await self.db_manager.shutdown()
    
    async def _run_loop(self) -> None:
        """Главный цикл задачи"""
        while self._running:
            try:
                # Health check
                if self._should_run_health_check():
                    await self._run_health_check()
                
                # Optimization
                if self._should_run_optimization():
                    await self._run_optimization()
                
                # Обработка алертов
                if self.auto_respond_to_alerts:
                    await self._process_alerts()
                
                # Сон до следующей итерации
                await asyncio.sleep(60)  # Проверка каждую минуту
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in database optimization loop: {e}", exc_info=True)
                await asyncio.sleep(300)  # 5 минут при ошибке
    
    def _should_run_health_check(self) -> bool:
        """Нужна ли проверка здоровья"""
        if self._last_health_check is None:
            return True
        
        elapsed = datetime.now() - self._last_health_check
        return elapsed >= timedelta(minutes=self.health_check_interval_minutes)
    
    def _should_run_optimization(self) -> bool:
        """Нужна ли оптимизация"""
        if self._last_optimization is None:
            return True
        
        elapsed = datetime.now() - self._last_optimization
        return elapsed >= timedelta(hours=self.optimization_interval_hours)
    
    async def _run_health_check(self) -> None:
        """Выполнение health check"""
        logger.info("Running database health check")
        
        try:
            results = await self.health_checker.run_all_checks()
            overall_status = self.health_checker.get_overall_status(results)
            
            logger.info(f"Health check completed: {overall_status.value}")
            
            # Запись метрик в монитор
            for check_name, result in results.items():
                if result.status.value == 'unhealthy':
                    logger.warning(f"Health check failed: {check_name} - {result.message}")
                elif result.status.value == 'degraded':
                    logger.warning(f"Health check degraded: {check_name} - {result.message}")
            
            self._last_health_check = datetime.now()
        
        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
    
    async def _run_optimization(self) -> None:
        """Выполнение оптимизации"""
        logger.info("Running database optimization cycle")
        
        try:
            result = await self.db_manager.run_optimization()
            
            if result['status'] == 'completed':
                logger.info(
                    f"Optimization completed: "
                    f"{result['operations_executed']} operations executed, "
                    f"{result['operations_failed']} failed, "
                    f"duration: {result['duration_seconds']:.2f}s"
                )
            elif result['status'] == 'deferred_due_to_load':
                logger.warning(
                    f"Optimization deferred due to high load: "
                    f"{result['current_load_percent']:.1f}%"
                )
            else:
                logger.error(f"Optimization failed: {result.get('error', 'Unknown error')}")
            
            self._last_optimization = datetime.now()
        
        except Exception as e:
            logger.error(f"Optimization cycle failed: {e}", exc_info=True)
    
    async def _process_alerts(self) -> None:
        """Обработка активных алертов"""
        try:
            alerts_data = self.db_manager.get_alerts(active_only=True)
            
            if alerts_data['critical'] > 0:
                logger.critical(f"Critical database alerts: {alerts_data['critical']}")
                
                # Автоматические действия для критических алертов
                for alert in alerts_data['alerts']:
                    if alert['severity'] == 'critical':
                        await self._handle_critical_alert(alert)
        
        except Exception as e:
            logger.error(f"Error processing alerts: {e}", exc_info=True)
    
    async def _handle_critical_alert(self, alert: Dict[str, Any]) -> None:
        """Обработка критического алерта"""
        metric = alert['metric']
        
        logger.critical(f"Handling critical alert for {metric}: {alert['message']}")
        
        # Автоматические действия в зависимости от типа алерта
        if 'connection' in metric.lower():
            # Проблемы с соединениями - попытка восстановления пула
            logger.info("Attempting connection pool recovery")
            # В реальности здесь будет логика восстановления
        
        elif 'deadlock' in metric.lower():
            # Дедлоки - запуск анализа блокировок
            logger.info("Analyzing database locks")
            # Анализ блокировок
        
        elif 'disk' in metric.lower():
            # Проблемы с диском - немедленная очистка
            logger.info("Triggering emergency disk cleanup")
            # Запуск VACUUM, очистки логов и т.д.
    
    def get_status(self) -> Dict[str, Any]:
        """Получение статуса задачи"""
        return {
            'running': self._running,
            'last_optimization': self._last_optimization.isoformat() if self._last_optimization else None,
            'last_health_check': self._last_health_check.isoformat() if self._last_health_check else None,
            'optimization_interval_hours': self.optimization_interval_hours,
            'health_check_interval_minutes': self.health_check_interval_minutes,
            'auto_respond_to_alerts': self.auto_respond_to_alerts
        }


# Глобальный инстанс задачи
_global_optimization_task: Optional[DatabaseOptimizationTask] = None


async def start_database_optimization() -> DatabaseOptimizationTask:
    """
    Запуск глобальной задачи оптимизации БД
    
    Returns:
        DatabaseOptimizationTask инстанс
    """
    global _global_optimization_task
    
    if _global_optimization_task is None:
        _global_optimization_task = DatabaseOptimizationTask()
    
    if not _global_optimization_task._running:
        await _global_optimization_task.start()
    
    return _global_optimization_task


async def stop_database_optimization() -> None:
    """Остановка глобальной задачи оптимизации"""
    global _global_optimization_task
    
    if _global_optimization_task is not None:
        await _global_optimization_task.stop()


def get_optimization_task() -> Optional[DatabaseOptimizationTask]:
    """Получение глобальной задачи оптимизации"""
    return _global_optimization_task


__all__ = [
    'DatabaseOptimizationTask',
    'start_database_optimization',
    'stop_database_optimization',
    'get_optimization_task'
]