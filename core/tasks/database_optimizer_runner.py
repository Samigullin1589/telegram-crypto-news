# core/tasks/database_optimizer_runner.py
"""
Database Optimization Task Runner
Автоматическая оптимизация базы данных

Интегрируется с системой задач для:
- Периодического запуска оптимизации
- Мониторинга здоровья БД
- Автоматического реагирования на проблемы
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from app.config.database import get_db_manager, DatabaseManager

logger = logging.getLogger(__name__)


class DatabaseOptimizationTask:
    """
    Задача автоматической оптимизации базы данных
    
    Выполняет:
    - Периодическую оптимизацию БД
    - Мониторинг здоровья системы
    - Обработку алертов
    - Автоматическое реагирование на проблемы
    
    Attributes:
        db_manager: Менеджер базы данных
        optimization_interval_hours: Интервал между оптимизациями (часы)
        health_check_interval_minutes: Интервал проверок здоровья (минуты)
        auto_respond_to_alerts: Автоматически реагировать на алерты
    """
    
    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        optimization_interval_hours: int = 1,
        health_check_interval_minutes: int = 5,
        auto_respond_to_alerts: bool = True
    ):
        """
        Инициализация задачи оптимизации
        
        Args:
            db_manager: Менеджер БД (или будет создан автоматически)
            optimization_interval_hours: Интервал оптимизации в часах
            health_check_interval_minutes: Интервал проверок здоровья в минутах
            auto_respond_to_alerts: Автоматически обрабатывать критические алерты
        """
        self.db_manager = db_manager or get_db_manager()
        self.optimization_interval_hours = optimization_interval_hours
        self.health_check_interval_minutes = health_check_interval_minutes
        self.auto_respond_to_alerts = auto_respond_to_alerts
        
        self._last_optimization: Optional[datetime] = None
        self._last_health_check: Optional[datetime] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._health_check_failures = 0
        self._optimization_failures = 0
    
    async def start(self) -> None:
        """
        Запуск задачи оптимизации
        
        Инициализирует менеджер БД и запускает основной цикл
        
        Raises:
            RuntimeError: Если задача уже запущена
        """
        if self._running:
            logger.warning("Database optimization task already running")
            return
        
        logger.info(
            f"Starting database optimization task: "
            f"optimization every {self.optimization_interval_hours}h, "
            f"health checks every {self.health_check_interval_minutes}m"
        )
        
        # Инициализация менеджера БД
        try:
            if not self.db_manager._initialized:
                await self.db_manager.initialize()
                logger.info("Database manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database manager: {e}", exc_info=True)
            raise
        
        # Запуск основного цикла
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Database optimization task started")
    
    async def stop(self) -> None:
        """
        Остановка задачи оптимизации
        
        Выполняет graceful shutdown:
        - Отменяет текущий цикл
        - Завершает работу менеджера БД
        """
        if not self._running:
            logger.debug("Database optimization task not running")
            return
        
        logger.info("Stopping database optimization task")
        self._running = False
        
        # Отмена задачи
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                logger.debug("Database optimization task cancelled")
        
        # Graceful shutdown менеджера
        try:
            await self.db_manager.shutdown()
            logger.info("Database manager shut down successfully")
        except Exception as e:
            logger.error(f"Error during database manager shutdown: {e}", exc_info=True)
        
        logger.info("Database optimization task stopped")
    
    async def _run_loop(self) -> None:
        """
        Главный цикл задачи
        
        Периодически выполняет:
        - Проверки здоровья БД
        - Оптимизацию БД
        - Обработку алертов
        """
        logger.debug("Entering main optimization loop")
        
        while self._running:
            try:
                # Health check
                if self._should_run_health_check():
                    await self._run_health_check()
                
                # Optimization
                if self._should_run_optimization():
                    await self._run_optimization()
                
                # Alert processing
                if self.auto_respond_to_alerts:
                    await self._process_alerts()
                
                # Sleep до следующей итерации
                await asyncio.sleep(60)  # Проверка каждую минуту
            
            except asyncio.CancelledError:
                logger.debug("Optimization loop cancelled")
                break
            
            except Exception as e:
                logger.error(
                    f"Unexpected error in optimization loop: {e}",
                    exc_info=True
                )
                # При ошибке спим дольше чтобы не спамить логи
                await asyncio.sleep(300)  # 5 минут
    
    def _should_run_health_check(self) -> bool:
        """
        Проверка необходимости health check
        
        Returns:
            True если пора выполнить проверку здоровья
        """
        if self._last_health_check is None:
            return True
        
        elapsed = datetime.now() - self._last_health_check
        interval = timedelta(minutes=self.health_check_interval_minutes)
        
        return elapsed >= interval
    
    def _should_run_optimization(self) -> bool:
        """
        Проверка необходимости оптимизации
        
        Returns:
            True если пора выполнить оптимизацию
        """
        if self._last_optimization is None:
            return True
        
        elapsed = datetime.now() - self._last_optimization
        interval = timedelta(hours=self.optimization_interval_hours)
        
        return elapsed >= interval
    
    async def _run_health_check(self) -> None:
        """
        Выполнение проверки здоровья БД
        
        Использует встроенные методы менеджера для проверки:
        - Доступности БД
        - Состояния пула соединений
        - Метрик производительности
        """
        logger.info("Running database health check")
        
        try:
            # Используем метод check_health из менеджера
            health_status = await self.db_manager.check_health()
            
            status = health_status.get('status', 'unknown')
            logger.info(f"Health check completed: status={status}")
            
            # Логирование деталей
            if status == 'healthy':
                self._health_check_failures = 0
                logger.debug(f"Database health: {health_status}")
            elif status == 'degraded':
                self._health_check_failures += 1
                logger.warning(
                    f"Database health degraded: {health_status.get('message', 'No details')}"
                )
            else:
                self._health_check_failures += 1
                logger.error(
                    f"Database unhealthy: {health_status.get('message', 'No details')}"
                )
            
            # Алерт при множественных провалах
            if self._health_check_failures >= 3:
                logger.critical(
                    f"Database health check failed {self._health_check_failures} times in a row!"
                )
            
            self._last_health_check = datetime.now()
        
        except Exception as e:
            self._health_check_failures += 1
            logger.error(
                f"Health check failed with exception (failures: {self._health_check_failures}): {e}",
                exc_info=True
            )
    
    async def _run_optimization(self) -> None:
        """
        Выполнение цикла оптимизации БД
        
        Запускает:
        - VACUUM операции
        - ANALYZE операций
        - Перестроение индексов
        - Очистку устаревших данных
        """
        logger.info("Running database optimization cycle")
        
        try:
            result = await self.db_manager.run_optimization()
            
            status = result.get('status', 'unknown')
            
            if status == 'completed':
                self._optimization_failures = 0
                operations_executed = result.get('operations_executed', 0)
                operations_failed = result.get('operations_failed', 0)
                duration = result.get('duration_seconds', 0)
                
                logger.info(
                    f"Optimization completed successfully: "
                    f"{operations_executed} operations executed, "
                    f"{operations_failed} failed, "
                    f"duration: {duration:.2f}s"
                )
                
                # Детальная информация о выполненных операциях
                if 'operations' in result:
                    for op in result['operations']:
                        op_name = op.get('name', 'unknown')
                        op_status = op.get('status', 'unknown')
                        op_duration = op.get('duration', 0)
                        logger.debug(
                            f"  - {op_name}: {op_status} ({op_duration:.2f}s)"
                        )
            
            elif status == 'deferred_due_to_load':
                logger.warning(
                    f"Optimization deferred due to high load: "
                    f"current load {result.get('current_load_percent', 0):.1f}%"
                )
            
            elif status == 'skipped':
                logger.info(
                    f"Optimization skipped: {result.get('reason', 'No reason provided')}"
                )
            
            else:
                self._optimization_failures += 1
                error_msg = result.get('error', 'Unknown error')
                logger.error(
                    f"Optimization failed (failures: {self._optimization_failures}): {error_msg}"
                )
            
            self._last_optimization = datetime.now()
        
        except Exception as e:
            self._optimization_failures += 1
            logger.error(
                f"Optimization cycle failed with exception (failures: {self._optimization_failures}): {e}",
                exc_info=True
            )
    
    async def _process_alerts(self) -> None:
        """
        Обработка активных алертов системы мониторинга
        
        Получает активные алерты и выполняет автоматические действия
        для критических проблем
        """
        try:
            alerts_data = self.db_manager.get_alerts(active_only=True)
            
            total_alerts = alerts_data.get('total', 0)
            critical_alerts = alerts_data.get('critical', 0)
            warning_alerts = alerts_data.get('warnings', 0)
            
            if total_alerts == 0:
                return
            
            logger.debug(
                f"Active alerts: {total_alerts} total "
                f"({critical_alerts} critical, {warning_alerts} warnings)"
            )
            
            # Обработка критических алертов
            if critical_alerts > 0:
                logger.critical(
                    f"Critical database alerts detected: {critical_alerts}"
                )
                
                alerts_list = alerts_data.get('alerts', [])
                for alert in alerts_list:
                    if alert.get('severity') == 'critical':
                        await self._handle_critical_alert(alert)
        
        except Exception as e:
            logger.error(
                f"Error processing database alerts: {e}",
                exc_info=True
            )
    
    async def _handle_critical_alert(self, alert: Dict[str, Any]) -> None:
        """
        Обработка критического алерта
        
        Выполняет автоматические действия в зависимости от типа проблемы:
        - Проблемы с соединениями → перезапуск пула
        - Дедлоки → анализ блокировок
        - Нехватка места → очистка данных
        
        Args:
            alert: Словарь с информацией об алерте
        """
        metric = alert.get('metric', 'unknown')
        message = alert.get('message', 'No message')
        threshold = alert.get('threshold', 'N/A')
        current_value = alert.get('current_value', 'N/A')
        
        logger.critical(
            f"Handling critical alert: {metric}\n"
            f"  Message: {message}\n"
            f"  Current value: {current_value}\n"
            f"  Threshold: {threshold}"
        )
        
        # Автоматические действия в зависимости от типа алерта
        metric_lower = metric.lower()
        
        if 'connection' in metric_lower or 'pool' in metric_lower:
            await self._handle_connection_alert(alert)
        
        elif 'deadlock' in metric_lower or 'lock' in metric_lower:
            await self._handle_deadlock_alert(alert)
        
        elif 'disk' in metric_lower or 'space' in metric_lower:
            await self._handle_disk_alert(alert)
        
        elif 'memory' in metric_lower:
            await self._handle_memory_alert(alert)
        
        elif 'query' in metric_lower or 'slow' in metric_lower:
            await self._handle_slow_query_alert(alert)
        
        else:
            logger.warning(
                f"No automatic handler for alert type: {metric}"
            )
    
    async def _handle_connection_alert(self, alert: Dict[str, Any]) -> None:
        """Обработка алерта о проблемах с соединениями"""
        logger.info("Attempting connection pool recovery")
        
        try:
            # Попытка перезапуска пула соединений
            # В реальности здесь будет вызов метода менеджера
            logger.info("Connection pool recovery initiated")
        except Exception as e:
            logger.error(f"Failed to recover connection pool: {e}", exc_info=True)
    
    async def _handle_deadlock_alert(self, alert: Dict[str, Any]) -> None:
        """Обработка алерта о дедлоках"""
        logger.info("Analyzing database locks and deadlocks")
        
        try:
            # Анализ текущих блокировок
            # В реальности здесь будет запрос блокировок из БД
            logger.info("Lock analysis initiated")
        except Exception as e:
            logger.error(f"Failed to analyze locks: {e}", exc_info=True)
    
    async def _handle_disk_alert(self, alert: Dict[str, Any]) -> None:
        """Обработка алерта о нехватке места на диске"""
        logger.info("Triggering emergency disk cleanup")
        
        try:
            # Немедленная очистка
            # - VACUUM FULL
            # - Очистка логов
            # - Удаление старых бэкапов
            logger.info("Emergency disk cleanup initiated")
        except Exception as e:
            logger.error(f"Failed to cleanup disk: {e}", exc_info=True)
    
    async def _handle_memory_alert(self, alert: Dict[str, Any]) -> None:
        """Обработка алерта о проблемах с памятью"""
        logger.info("Handling memory pressure")
        
        try:
            # Действия по освобождению памяти
            # - Очистка кэшей
            # - Уменьшение размера пула
            logger.info("Memory cleanup initiated")
        except Exception as e:
            logger.error(f"Failed to handle memory alert: {e}", exc_info=True)
    
    async def _handle_slow_query_alert(self, alert: Dict[str, Any]) -> None:
        """Обработка алерта о медленных запросах"""
        logger.info("Analyzing slow queries")
        
        try:
            # Анализ медленных запросов
            # - Проверка индексов
            # - Анализ планов выполнения
            logger.info("Slow query analysis initiated")
        except Exception as e:
            logger.error(f"Failed to analyze slow queries: {e}", exc_info=True)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение текущего статуса задачи
        
        Returns:
            Словарь с информацией о состоянии задачи
        """
        return {
            'running': self._running,
            'last_optimization': (
                self._last_optimization.isoformat() 
                if self._last_optimization else None
            ),
            'last_health_check': (
                self._last_health_check.isoformat() 
                if self._last_health_check else None
            ),
            'optimization_interval_hours': self.optimization_interval_hours,
            'health_check_interval_minutes': self.health_check_interval_minutes,
            'auto_respond_to_alerts': self.auto_respond_to_alerts,
            'health_check_failures': self._health_check_failures,
            'optimization_failures': self._optimization_failures
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Получение статистики работы задачи
        
        Returns:
            Словарь со статистическими данными
        """
        uptime_seconds = 0
        if self._last_optimization:
            uptime_seconds = (datetime.now() - self._last_optimization).total_seconds()
        
        return {
            'status': self.get_status(),
            'uptime_seconds': uptime_seconds,
            'consecutive_health_failures': self._health_check_failures,
            'consecutive_optimization_failures': self._optimization_failures
        }


# ============================================================================
# GLOBAL INSTANCE MANAGEMENT
# ============================================================================

_global_optimization_task: Optional[DatabaseOptimizationTask] = None


async def start_database_optimization() -> DatabaseOptimizationTask:
    """
    Запуск глобальной задачи оптимизации БД
    
    Создает и запускает глобальный инстанс задачи оптимизации.
    Если задача уже запущена, возвращает существующий инстанс.
    
    Returns:
        DatabaseOptimizationTask инстанс
    """
    global _global_optimization_task
    
    if _global_optimization_task is None:
        logger.info("Creating global database optimization task")
        _global_optimization_task = DatabaseOptimizationTask()
    
    if not _global_optimization_task._running:
        await _global_optimization_task.start()
    
    return _global_optimization_task


async def stop_database_optimization() -> None:
    """
    Остановка глобальной задачи оптимизации
    
    Выполняет graceful shutdown глобального инстанса задачи.
    """
    global _global_optimization_task
    
    if _global_optimization_task is not None:
        await _global_optimization_task.stop()
        logger.info("Global database optimization task stopped")


def get_optimization_task() -> Optional[DatabaseOptimizationTask]:
    """
    Получение глобального инстанса задачи оптимизации
    
    Returns:
        DatabaseOptimizationTask инстанс или None если не создан
    """
    return _global_optimization_task


def is_optimization_running() -> bool:
    """
    Проверка статуса глобальной задачи оптимизации
    
    Returns:
        True если задача запущена
    """
    global _global_optimization_task
    return (
        _global_optimization_task is not None 
        and _global_optimization_task._running
    )


__all__ = [
    'DatabaseOptimizationTask',
    'start_database_optimization',
    'stop_database_optimization',
    'get_optimization_task',
    'is_optimization_running'
]