"""
INTEGRATED CRYPTO MONITOR v4.5 - Complete Database Integration
Entry point for unified monitoring system with database optimization

Новое в v4.5:
- Полная интеграция database архитектуры
- Автоматическая оптимизация БД
- Улучшенный мониторинг здоровья
- Централизованное управление задачами
"""

import sys
import asyncio
import logging
import signal
from typing import Optional

if sys.version_info < (3, 8):
    print("❌ Требуется Python 3.8 или выше")
    sys.exit(1)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('crypto_monitor.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

# Импорты
from core.startup import StartupValidator
from core.monitor import IntegratedCryptoMonitor
from core.tasks.manager import get_task_manager
from app import (
    config,
    get_database_manager,
    DatabaseManager,
    __version__
)


class Application:
    """
    Главный класс приложения
    
    Управляет жизненным циклом:
    - Инициализация конфигурации
    - Валидация окружения
    - Запуск мониторинга
    - Graceful shutdown
    """
    
    def __init__(self):
        """Инициализация приложения"""
        self.monitor: Optional[IntegratedCryptoMonitor] = None
        self.task_manager = get_task_manager()
        self.shutdown_requested = False
        
        logger.info("=" * 80)
        logger.info(f"🚀 CRYPTO MONITOR v{__version__} - Starting")
        logger.info("=" * 80)
    
    async def initialize(self) -> bool:
        """
        Инициализация приложения
        
        Returns:
            bool: True если успешно
        """
        try:
            logger.info("📋 Шаг 1/3: Валидация окружения")
            if not self._validate_environment():
                return False
            
            logger.info("📋 Шаг 2/3: Инициализация database")
            if not await self._initialize_database():
                return False
            
            logger.info("📋 Шаг 3/3: Инициализация мониторинга")
            if not self._initialize_monitor():
                return False
            
            logger.info("✅ Инициализация завершена успешно")
            return True
        
        except Exception as e:
            logger.error(f"❌ Критическая ошибка инициализации: {e}", exc_info=True)
            return False
    
    def _validate_environment(self) -> bool:
        """
        Валидация окружения
        
        Returns:
            bool: True если валидация успешна
        """
        try:
            startup_validator = StartupValidator()
            
            if not startup_validator.validate_all():
                logger.error("❌ Валидация окружения не пройдена")
                return False
            
            logger.info("✅ Окружение валидно")
            return True
        
        except Exception as e:
            logger.error(f"❌ Ошибка валидации окружения: {e}", exc_info=True)
            return False
    
    async def _initialize_database(self) -> bool:
        """
        Инициализация database
        
        Returns:
            bool: True если успешно
        """
        try:
            # Получаем database manager из config
            db_manager = get_database_manager()
            
            if not db_manager.is_initialized:
                logger.warning("DatabaseManager не инициализирован, инициализируем...")
                db_manager.initialize()
            
            logger.info(f"✅ Database инициализирована: {db_manager.config.db_path}")
            
            # Проверяем соединение
            cursor = db_manager.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            
            if result and result[0] == 1:
                logger.info("✅ Database connection OK")
                return True
            else:
                logger.error("❌ Database connection failed")
                return False
        
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации database: {e}", exc_info=True)
            return False
    
    def _initialize_monitor(self) -> bool:
        """
        Инициализация мониторинга
        
        Returns:
            bool: True если успешно
        """
        try:
            self.monitor = IntegratedCryptoMonitor()
            logger.info("✅ Мониторинг инициализирован")
            return True
        
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации мониторинга: {e}", exc_info=True)
            return False
    
    async def run(self) -> None:
        """Запуск приложения"""
        try:
            # Инициализация
            if not await self.initialize():
                logger.error("❌ Инициализация не удалась")
                sys.exit(1)
            
            logger.info("=" * 80)
            logger.info("🎯 Запуск задач")
            logger.info("=" * 80)
            
            # Запускаем все задачи
            task_results = await self.task_manager.start_all(
                enable_database_optimization=True,
                enable_news_monitoring=config.is_feature_enabled('news'),
                enable_whale_tracking=config.is_feature_enabled('whale'),
                enable_trading_signals=config.is_feature_enabled('trading')
            )
            
            logger.info("=" * 80)
            logger.info("✅ Все задачи запущены")
            logger.info("=" * 80)
            
            # Выводим статус
            for task_name, result in task_results.items():
                status = result.get('status', 'unknown')
                logger.info(f"  📌 {task_name}: {status}")
            
            logger.info("=" * 80)
            logger.info("🚀 Приложение работает. Нажмите Ctrl+C для остановки")
            logger.info("=" * 80)
            
            # Запуск главного мониторинга
            if self.monitor:
                await self.monitor.run()
        
        except asyncio.CancelledError:
            logger.info("Приложение прервано")
        
        except Exception as e:
            logger.error(f"❌ Критическая ошибка в run: {e}", exc_info=True)
            raise
    
    async def shutdown(self) -> None:
        """Graceful shutdown приложения"""
        if self.shutdown_requested:
            return
        
        self.shutdown_requested = True
        
        logger.info("=" * 80)
        logger.info("⏹️ Начало graceful shutdown")
        logger.info("=" * 80)
        
        try:
            # Останавливаем все задачи
            logger.info("Остановка задач...")
            await self.task_manager.stop_all()
            
            # Останавливаем мониторинг
            if self.monitor:
                logger.info("Остановка мониторинга...")
                # Добавь логику остановки если есть
            
            # Закрываем database
            try:
                db_manager = get_database_manager()
                if db_manager and db_manager.is_initialized:
                    logger.info("Закрытие database...")
                    db_manager.close()
            except Exception as e:
                logger.warning(f"Ошибка закрытия database: {e}")
            
            logger.info("=" * 80)
            logger.info("✅ Graceful shutdown завершен")
            logger.info("=" * 80)
        
        except Exception as e:
            logger.error(f"Ошибка во время shutdown: {e}", exc_info=True)


# ============================================================================
# MAIN FUNCTION
# ============================================================================


def handle_signal(signum, frame):
    """Обработчик сигналов"""
    logger.info(f"\n⏹️ Получен сигнал {signum}, начинается остановка...")
    # Просто выходим, cleanup произойдет в finally
    sys.exit(0)


async def async_main():
    """Асинхронная главная функция"""
    app = Application()
    
    try:
        await app.run()
    
    except KeyboardInterrupt:
        logger.info("\n⏹️ Остановка по Ctrl+C")
    
    except Exception as e:
        logger.error(f"\n❌ Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)
    
    finally:
        # Graceful shutdown
        try:
            await app.shutdown()
        except Exception as e:
            logger.error(f"Ошибка graceful shutdown: {e}", exc_info=True)


def main():
    """Главная точка входа"""
    # Настройка обработчиков сигналов
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    try:
        # Запуск приложения
        asyncio.run(async_main())
    
    except KeyboardInterrupt:
        logger.info("\n⏹️ Прервано пользователем")
    
    except Exception as e:
        logger.error(f"\n❌ Критическая ошибка в main: {e}", exc_info=True)
        sys.exit(1)
    
    logger.info("\n👋 Goodbye!")


if __name__ == '__main__':
    main()