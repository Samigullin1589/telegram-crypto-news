# core/shutdown.py
"""
Shutdown Manager v5.3
Graceful остановка приложения

ИСПРАВЛЕНО v5.3:
- Совместимость с IntegratedCryptoMonitor v5.3
- Работа с DatabaseManager напрямую (не через DatabaseInitializer)
- Убрана зависимость от устаревшего TaskManager
- Monitor сам управляет своими задачами через infrastructure

Выполняет:
- Координацию остановки всех компонентов
- Правильную последовательность shutdown
- Обработку таймаутов
- Логирование процесса остановки
"""

import asyncio
from typing import Optional, Any, TYPE_CHECKING
from core.logging_config import get_logger

# ИСПРАВЛЕНО: TYPE_CHECKING для избежания циклического импорта
if TYPE_CHECKING:
    from core.monitor import IntegratedCryptoMonitor

logger = get_logger(__name__)


class ShutdownManager:
    """
    Менеджер graceful shutdown приложения v5.3

    ИСПРАВЛЕНО v5.3:
    - Совместимость с IntegratedCryptoMonitor v5.3
    - Monitor управляет своими задачами через infrastructure
    - Работа с DatabaseManager напрямую

    Координирует остановку всех компонентов системы в правильном порядке,
    обеспечивая корректное освобождение ресурсов и сохранение данных.

    Порядок остановки:
    1. Остановка мониторинга (IntegratedCryptoMonitor)
       - Monitor.stop() сам останавливает business tasks и HTTP server
    2. Закрытие соединений с БД (DatabaseManager)

    Attributes:
        monitor: Система мониторинга (опционально)
        db_manager: Менеджер БД (опционально)
        shutdown_timeout: Максимальное время на shutdown каждого компонента
        shutdown_in_progress: Флаг выполнения shutdown
    """

    # Таймауты для каждого этапа (в секундах)
    DEFAULT_MONITOR_SHUTDOWN_TIMEOUT = 15
    DEFAULT_DATABASE_SHUTDOWN_TIMEOUT = 10

    def __init__(
        self,
        monitor: Optional['IntegratedCryptoMonitor'] = None,
        db_manager: Optional[Any] = None,
        monitor_shutdown_timeout: int = DEFAULT_MONITOR_SHUTDOWN_TIMEOUT,
        database_shutdown_timeout: int = DEFAULT_DATABASE_SHUTDOWN_TIMEOUT
    ):
        """
        Инициализация shutdown manager v5.3

        ИСПРАВЛЕНО v5.3:
        - Убраны устаревшие task_manager и db_initializer
        - Прямая работа с monitor и db_manager

        Args:
            monitor: Монитор для остановки (опционально)
            db_manager: Database manager для закрытия соединений (опционально)
            monitor_shutdown_timeout: Таймаут остановки монитора (секунды)
            database_shutdown_timeout: Таймаут закрытия БД (секунды)
        """
        self.monitor = monitor
        self.db_manager = db_manager

        # Таймауты
        self.monitor_shutdown_timeout = monitor_shutdown_timeout
        self.database_shutdown_timeout = database_shutdown_timeout

        # Состояние
        self.shutdown_in_progress = False
        self.shutdown_completed = False

        logger.debug(
            f"ShutdownManager v5.3 initialized with timeouts: "
            f"monitor={monitor_shutdown_timeout}s, "
            f"database={database_shutdown_timeout}s"
        )
    
    async def shutdown(self) -> bool:
        """
        Выполнение полного graceful shutdown v5.3

        ИСПРАВЛЕНО v5.3:
        - Monitor.stop() сам останавливает business tasks и HTTP server
        - Убран _stop_tasks() (задачи управляются Monitor.infrastructure)
        - Упрощенная последовательность: monitor → database

        Останавливает все компоненты системы в правильном порядке
        с соблюдением таймаутов и обработкой ошибок.

        Returns:
            True если все компоненты остановлены успешно
        """
        if self.shutdown_in_progress:
            logger.warning("⚠️ Shutdown already in progress, skipping duplicate call")
            return False

        if self.shutdown_completed:
            logger.warning("⚠️ Shutdown already completed")
            return True

        self.shutdown_in_progress = True

        logger.info("="*80)
        logger.info("🛑 Starting graceful shutdown sequence v5.3...")
        logger.info("="*80)

        shutdown_success = True

        try:
            # Шаг 1: Останавливаем мониторинг
            # Monitor.stop() сам останавливает business tasks и HTTP server
            if not await self._stop_monitor():
                shutdown_success = False

            # Шаг 2: Закрываем базу данных
            if not await self._close_database():
                shutdown_success = False

            if shutdown_success:
                logger.info("="*80)
                logger.info("✅ Graceful shutdown completed successfully")
                logger.info("="*80)
            else:
                logger.warning("="*80)
                logger.warning("⚠️ Shutdown completed with some errors")
                logger.warning("="*80)

            self.shutdown_completed = True
            return shutdown_success

        except Exception as e:
            logger.error(
                f"❌ Critical error during shutdown sequence: {e}",
                exc_info=True
            )
            return False

        finally:
            self.shutdown_in_progress = False
    
    async def _stop_monitor(self) -> bool:
        """
        Остановка системы мониторинга v5.3

        ИСПРАВЛЕНО v5.3:
        - Monitor.stop() теперь останавливает business tasks и HTTP server
        - Упрощенная логика вызова

        Останавливает IntegratedCryptoMonitor с соблюдением таймаута.

        Returns:
            True если монитор остановлен успешно
        """
        try:
            logger.info("📊 Step 1/2: Stopping monitor...")

            if not self.monitor:
                logger.info("ℹ️ Monitor is not set, skipping")
                return True

            # Проверяем наличие метода stop
            if not hasattr(self.monitor, 'stop'):
                logger.warning("⚠️ Monitor has no stop method, skipping")
                return True

            # Останавливаем монитор с таймаутом
            try:
                stop_coro = self.monitor.stop()

                if asyncio.iscoroutine(stop_coro):
                    await asyncio.wait_for(
                        stop_coro,
                        timeout=self.monitor_shutdown_timeout
                    )
                else:
                    # Если stop не async, вызываем напрямую
                    self.monitor.stop()

                logger.info("✅ Monitor stopped successfully")
                return True

            except asyncio.TimeoutError:
                logger.error(
                    f"❌ Monitor shutdown timeout ({self.monitor_shutdown_timeout}s) exceeded"
                )
                return False

        except Exception as e:
            logger.error(
                f"❌ Error stopping monitor: {e}",
                exc_info=True
            )
            return False

    async def _close_database(self) -> bool:
        """
        Закрытие соединений с базой данных v5.3

        ИСПРАВЛЕНО v5.3:
        - Работа с DatabaseManager напрямую (не через DatabaseInitializer)
        - Поддержка sync/async методов close/shutdown

        Закрывает DatabaseManager с соблюдением таймаута.

        Returns:
            True если БД закрыта успешно
        """
        try:
            logger.info("💾 Step 2/2: Closing database connections...")

            if not self.db_manager:
                logger.info("ℹ️ Database manager is not set, skipping")
                return True

            # Проверяем инициализацию БД (опционально)
            db_manager = self.db_manager
            if hasattr(db_manager, 'is_initialized'):
                if not db_manager.is_initialized:
                    logger.info("ℹ️ Database is not initialized, skipping")
                    return True
            elif hasattr(db_manager, '_initialized'):
                if not db_manager._initialized:
                    logger.info("ℹ️ Database is not initialized, skipping")
                    return True

            # Закрываем БД с таймаутом
            try:
                async def close_db():
                    """Обертка для синхронного/асинхронного close"""
                    if hasattr(db_manager, 'close'):
                        if asyncio.iscoroutinefunction(db_manager.close):
                            await db_manager.close()
                        else:
                            db_manager.close()
                    elif hasattr(db_manager, 'shutdown'):
                        if asyncio.iscoroutinefunction(db_manager.shutdown):
                            await db_manager.shutdown()
                        else:
                            db_manager.shutdown()
                    else:
                        logger.warning("⚠️ DatabaseManager has no close/shutdown method")

                await asyncio.wait_for(
                    close_db(),
                    timeout=self.database_shutdown_timeout
                )

                logger.info("✅ Database connections closed successfully")
                return True

            except asyncio.TimeoutError:
                logger.error(
                    f"❌ Database shutdown timeout ({self.database_shutdown_timeout}s) exceeded"
                )
                return False

        except Exception as e:
            logger.error(
                f"❌ Error closing database: {e}",
                exc_info=True
            )
            return False

    def set_monitor(self, monitor: 'IntegratedCryptoMonitor') -> None:
        """
        Установка монитора для shutdown

        Args:
            monitor: Экземпляр IntegratedCryptoMonitor
        """
        self.monitor = monitor
        logger.debug("Monitor set for shutdown management")

    def get_status(self) -> dict:
        """
        Получение статуса shutdown manager v5.3

        ИСПРАВЛЕНО v5.3:
        - Обновлены проверки has_* для новой архитектуры
        - Убраны устаревшие task_manager и db_initializer

        Returns:
            Словарь с информацией о состоянии
        """
        return {
            'shutdown_in_progress': self.shutdown_in_progress,
            'shutdown_completed': self.shutdown_completed,
            'has_db_manager': self.db_manager is not None,
            'has_monitor': self.monitor is not None,
            'timeouts': {
                'monitor': self.monitor_shutdown_timeout,
                'database': self.database_shutdown_timeout
            }
        }
    
    def __repr__(self) -> str:
        """Строковое представление v5.3"""
        # ИСПРАВЛЕНО v5.3: обновлено для новой архитектуры
        components_count = sum([
            self.db_manager is not None,
            self.monitor is not None
        ])

        return (
            f"ShutdownManager("
            f"in_progress={self.shutdown_in_progress}, "
            f"completed={self.shutdown_completed}, "
            f"components={components_count}"
            f")"
        )