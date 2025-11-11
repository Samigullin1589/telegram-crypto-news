# core/tasks/bot_runner.py
"""
Bot Webhook Runner Module
==========================

Модуль управления Telegram ботом в режиме webhook.

Components:
-----------
- BotWebhookRunner: Основной класс для запуска бота
- Task Management Functions: Функции управления фоновой задачей

Architecture:
-------------
Обеспечивает:
- Инициализацию bot application
- Регистрацию command handlers
- Установку webhook
- Мониторинг здоровья
- Graceful shutdown
- Управление жизненным циклом задачи

Production Ready:
-----------------
- Полная обработка ошибок
- Таймауты для операций
- Метрики и мониторинг
- Корректное завершение
"""

import asyncio
import logging
import traceback
import os
from typing import Optional, Any
from dataclasses import dataclass


logger = logging.getLogger(__name__)


# Глобальное состояние задачи бота
_bot_task: Optional[asyncio.Task] = None


@dataclass
class BotConfig:
    """
    Конфигурация бота
    
    Хранит параметры необходимые для запуска бота в webhook режиме.
    
    Attributes:
        bot_application: Telegram bot application instance
        health_monitor: Монитор здоровья системы
        statistics: Система сбора статистики
        shutdown_event: Event для graceful shutdown
        webhook_url: URL для webhook (опционально)
    """
    bot_application: Any
    health_monitor: Any
    statistics: Any
    shutdown_event: asyncio.Event
    webhook_url: str = ''


class BotWebhookRunner:
    """
    Запуск Telegram бота в режиме WEBHOOK
    
    Основной класс для управления жизненным циклом бота.
    Обеспечивает полный цикл работы от инициализации до shutdown.
    
    Responsibilities:
    -----------------
    - Инициализация bot application
    - Регистрация command handlers
    - Установка и удаление webhook
    - Мониторинг работы бота
    - Graceful shutdown
    
    Attributes:
        bot_application: Telegram bot application
        health_monitor: Монитор здоровья
        statistics: Сборщик статистики
        shutdown_event: Event остановки
    """
    
    def __init__(self, bot_application, health_monitor, statistics, shutdown_event):
        """
        Инициализация runner
        
        Args:
            bot_application: Telegram bot application instance
            health_monitor: Монитор здоровья системы
            statistics: Система сбора статистики
            shutdown_event: Event для graceful shutdown
        """
        self.bot_application = bot_application
        self.health_monitor = health_monitor
        self.statistics = statistics
        self.shutdown_event = shutdown_event
        
        logger.debug("BotWebhookRunner initialized")
    
    async def run(self):
        """
        Основной цикл работы бота
        
        Выполняет полный цикл:
        1. Инициализация application
        2. Регистрация handlers
        3. Установка webhook
        4. Мониторинг работы
        5. Graceful shutdown
        
        Обрабатывает:
        - asyncio.TimeoutError: При превышении таймаутов
        - asyncio.CancelledError: При отмене задачи
        - Exception: Все остальные ошибки
        """
        try:
            logger.info("🤖 [BOT] Инициализация command handler (WEBHOOK MODE)...")
            
            # Шаг 1: Инициализация application
            await self._initialize_application()
            
            # Шаг 2: Регистрация handlers
            self._register_handlers()
            
            # Шаг 3: Установка webhook
            await self._setup_webhook()
            
            # Шаг 4: Мониторинг работы
            await self._monitoring_loop()
            
            logger.info("🤖 [BOT] Получен сигнал остановки")
        
        except asyncio.TimeoutError:
            logger.error("❌ [BOT] Timeout при инициализации")
            self._record_error()
        
        except asyncio.CancelledError:
            logger.info("🤖 [BOT] Получен сигнал отмены")
            raise
        
        except Exception as e:
            self._record_error()
            logger.error(f"❌ [BOT] Ошибка при работе бота: {e}")
            traceback.print_exc()
        
        finally:
            await self._cleanup()
    
    async def _initialize_application(self):
        """
        Инициализация bot application
        
        Выполняет initialize() и start() с таймаутами.
        
        Raises:
            asyncio.TimeoutError: При превышении таймаута
            Exception: При ошибках инициализации
        """
        logger.debug("Initializing bot application...")
        
        await asyncio.wait_for(
            self.bot_application.initialize(),
            timeout=30.0
        )
        logger.debug("   ✓ Application initialized")
        
        await asyncio.wait_for(
            self.bot_application.start(),
            timeout=30.0
        )
        logger.debug("   ✓ Application started")
    
    def _register_handlers(self):
        """
        Регистрация command handlers
        
        Критически важный метод!
        Импортирует и регистрирует все handlers из app.bot.
        
        Обрабатывает:
        - ImportError: Если модуль app.bot недоступен
        - Exception: Другие ошибки регистрации
        """
        try:
            from app.bot import register_all_handlers, handlers_registered
            
            # Проверка что handlers еще не зарегистрированы
            if handlers_registered():
                logger.info("✅ [BOT] Handlers уже зарегистрированы")
                return
            
            logger.info("🔧 [BOT] Регистрация command handlers...")
            
            # Регистрация handlers
            register_all_handlers()
            
            # Проверка успешности
            if handlers_registered():
                logger.info("✅ [BOT] Handlers успешно зарегистрированы")
            else:
                logger.warning("⚠️  [BOT] Статус регистрации handlers неизвестен")
        
        except ImportError as e:
            logger.error(f"❌ [BOT] Не удалось импортировать register_all_handlers: {e}")
            traceback.print_exc()
            raise
        
        except Exception as e:
            logger.error(f"❌ [BOT] Ошибка регистрации handlers: {e}")
            traceback.print_exc()
            raise
    
    async def _setup_webhook(self):
        """
        Установка webhook
        
        Выполняет:
        1. Определение URL webhook
        2. Удаление старого webhook
        3. Установка нового webhook
        4. Обновление heartbeat
        5. Вывод статуса
        
        Raises:
            asyncio.TimeoutError: При превышении таймаута
            Exception: При ошибках установки
        """
        # Определение URL
        webhook_url = self._determine_webhook_url()
        
        logger.info(f"🤖 [BOT] Устанавливаем webhook: {webhook_url}")
        
        # Удаление старого webhook
        await asyncio.wait_for(
            self.bot_application.bot.delete_webhook(drop_pending_updates=True),
            timeout=10.0
        )
        
        # Установка нового webhook
        webhook_info = await asyncio.wait_for(
            self.bot_application.bot.set_webhook(
                url=webhook_url,
                allowed_updates=None,
                drop_pending_updates=True
            ),
            timeout=10.0
        )
        
        if webhook_info:
            logger.info("✅ [BOT] Webhook установлен успешно")
        else:
            logger.warning("⚠️  [BOT] Webhook set вернул False, но продолжаем")
        
        # Обновление heartbeat
        self.health_monitor.update_bot_heartbeat()
        
        # Вывод статуса
        self._log_status(webhook_url)
    
    async def _monitoring_loop(self):
        """
        Цикл мониторинга работы бота
        
        Работает до получения сигнала остановки.
        Каждые 60 секунд обновляет heartbeat.
        
        Raises:
            asyncio.CancelledError: При отмене задачи
        """
        while not self.shutdown_event.is_set():
            self.health_monitor.update_bot_heartbeat()
            await asyncio.sleep(60)
    
    def _log_status(self, webhook_url: str):
        """
        Вывод статуса бота
        
        Args:
            webhook_url: URL установленного webhook
        """
        handlers_count = self._count_handlers()
        
        logger.info("✅ [BOT] Command handler активен в WEBHOOK режиме")
        logger.info(f"   Webhook URL: {webhook_url}")
        logger.info(f"   Зарегистрировано handlers: {handlers_count}")
        logger.info("   Доступные команды: /start, /help, /status, /positions, /performance")
    
    def _count_handlers(self) -> int:
        """
        Подсчет зарегистрированных handlers
        
        Returns:
            int: Количество handlers
        """
        try:
            total = 0
            for group in self.bot_application.handlers.values():
                total += len(group)
            return total
        except Exception:
            return 0
    
    def _determine_webhook_url(self) -> str:
        """
        Определение URL для webhook
        
        Приоритет источников:
        1. WEBHOOK_URL environment variable
        2. RENDER_EXTERNAL_URL + /webhook/telegram
        3. RENDER_SERVICE_NAME + .onrender.com/webhook/telegram
        
        Returns:
            str: URL для webhook
        """
        webhook_url = os.environ.get('WEBHOOK_URL', '')
        
        if not webhook_url:
            render_url = os.environ.get('RENDER_EXTERNAL_URL', '')
            if render_url:
                webhook_url = f"{render_url}/webhook/telegram"
            else:
                service_name = os.environ.get('RENDER_SERVICE_NAME', 'crypto-compass')
                webhook_url = f"https://{service_name}.onrender.com/webhook/telegram"
        
        return webhook_url
    
    def _record_error(self):
        """Запись ошибки в мониторинг и статистику"""
        self.health_monitor.record_error('bot')
        self.statistics.increment_errors()
    
    async def _cleanup(self):
        """
        Очистка ресурсов
        
        Выполняет graceful shutdown:
        1. Удаление webhook
        2. Остановка application
        3. Shutdown application
        
        Обрабатывает все ошибки чтобы гарантировать выполнение всех шагов.
        """
        logger.info("🤖 [BOT] Останавливаем command handler...")
        
        # Удаление webhook
        await self._delete_webhook()
        
        # Остановка application
        await self._stop_application()
        
        # Shutdown application
        await self._shutdown_application()
        
        logger.info("✅ [BOT] Command handler полностью остановлен")
    
    async def _delete_webhook(self):
        """Удаление webhook с обработкой ошибок"""
        try:
            await asyncio.wait_for(
                self.bot_application.bot.delete_webhook(),
                timeout=10.0
            )
            logger.info("   ✓ Webhook удалён")
        except asyncio.TimeoutError:
            logger.warning("   ⚠️  Timeout при удалении webhook")
        except Exception as e:
            logger.warning(f"   ⚠️  Ошибка при удалении webhook: {e}")
    
    async def _stop_application(self):
        """Остановка application с обработкой ошибок"""
        try:
            if self.bot_application.running:
                await asyncio.wait_for(
                    self.bot_application.stop(),
                    timeout=10.0
                )
                logger.info("   ✓ Application остановлен")
        except asyncio.TimeoutError:
            logger.warning("   ⚠️  Timeout при остановке application")
        except Exception as e:
            logger.warning(f"   ⚠️  Ошибка при остановке application: {e}")
    
    async def _shutdown_application(self):
        """Shutdown application с обработкой ошибок"""
        try:
            await asyncio.wait_for(
                self.bot_application.shutdown(),
                timeout=10.0
            )
            logger.info("   ✓ Shutdown завершён")
        except asyncio.TimeoutError:
            logger.warning("   ⚠️  Timeout при shutdown")
        except Exception as e:
            logger.warning(f"   ⚠️  Ошибка при shutdown: {e}")


# ==================== Task Management Functions ====================


async def start_bot_task(
    bot_application: Any,
    health_monitor: Any,
    statistics: Any,
    shutdown_event: asyncio.Event,
    webhook_url: str = ''
) -> asyncio.Task:
    """
    Запуск фоновой задачи бота
    
    Создает и запускает асинхронную задачу с BotWebhookRunner.
    Задача работает в фоновом режиме до вызова stop_bot_task.
    
    Args:
        bot_application: Telegram bot application instance
        health_monitor: Монитор здоровья системы
        statistics: Система сбора статистики
        shutdown_event: Event для graceful shutdown
        webhook_url: URL для webhook (опционально)
        
    Returns:
        asyncio.Task: Запущенная задача бота
        
    Raises:
        RuntimeError: Если задача уже запущена
        
    Example:
        >>> task = await start_bot_task(
        ...     bot_app, health_mon, stats, shutdown_evt
        ... )
        >>> # Задача работает в фоне
    """
    global _bot_task
    
    if _bot_task and not _bot_task.done():
        raise RuntimeError("Bot task is already running")
    
    logger.info("🚀 [BOT] Запуск фоновой задачи бота...")
    
    # Создание runner
    runner = BotWebhookRunner(
        bot_application,
        health_monitor,
        statistics,
        shutdown_event
    )
    
    # Запуск задачи
    _bot_task = asyncio.create_task(
        runner.run(),
        name='bot_webhook_task'
    )
    
    logger.info("✅ [BOT] Фоновая задача бота запущена")
    
    return _bot_task


async def stop_bot_task(timeout: float = 30.0) -> None:
    """
    Остановка фоновой задачи бота
    
    Отменяет задачу и ожидает её завершения.
    Гарантирует graceful shutdown через BotWebhookRunner._cleanup.
    
    Args:
        timeout: Таймаут ожидания завершения задачи (секунды)
        
    Raises:
        asyncio.TimeoutError: Если задача не завершилась за timeout
        
    Example:
        >>> await stop_bot_task(timeout=30.0)
    """
    global _bot_task
    
    if not _bot_task or _bot_task.done():
        logger.debug("Bot task не запущена или уже завершена")
        return
    
    logger.info("🛑 [BOT] Остановка фоновой задачи бота...")
    
    try:
        # Отмена задачи
        _bot_task.cancel()
        
        # Ожидание завершения
        await asyncio.wait_for(_bot_task, timeout=timeout)
        
        logger.info("✅ [BOT] Фоновая задача бота остановлена")
    
    except asyncio.TimeoutError:
        logger.warning(f"⚠️  [BOT] Timeout при остановке задачи ({timeout}s)")
        raise
    
    except asyncio.CancelledError:
        logger.info("✅ [BOT] Задача отменена успешно")
    
    except Exception as e:
        logger.error(f"❌ [BOT] Ошибка при остановке задачи: {e}")
        traceback.print_exc()
    
    finally:
        _bot_task = None


def get_bot_task() -> Optional[asyncio.Task]:
    """
    Получение ссылки на задачу бота
    
    Используется для проверки статуса или ожидания завершения.
    
    Returns:
        Optional[asyncio.Task]: Задача бота или None если не запущена
        
    Example:
        >>> task = get_bot_task()
        >>> if task and not task.done():
        ...     print("Bot is running")
        >>> else:
        ...     print("Bot is not running")
    """
    global _bot_task
    return _bot_task


def get_bot_task_status() -> dict:
    """
    Получение детального статуса задачи бота
    
    Возвращает информацию о состоянии задачи для мониторинга.
    
    Returns:
        dict: Статус задачи с полями:
            - running: bool - запущена ли задача
            - status: str - статус (not_started/active/cancelled/completed)
            - task_name: str - имя задачи (если запущена)
            - exception: str - информация об ошибке (если есть)
            
    Example:
        >>> status = get_bot_task_status()
        >>> print(f"Running: {status['running']}")
        >>> print(f"Status: {status['status']}")
    """
    global _bot_task
    
    if not _bot_task:
        return {
            'running': False,
            'status': 'not_started'
        }
    
    if _bot_task.done():
        exception = None
        if not _bot_task.cancelled():
            try:
                exception = _bot_task.exception()
            except Exception:
                pass
        
        return {
            'running': False,
            'status': 'cancelled' if _bot_task.cancelled() else 'completed',
            'exception': str(exception) if exception else None
        }
    
    return {
        'running': True,
        'status': 'active',
        'task_name': _bot_task.get_name()
    }


__all__ = [
    'BotWebhookRunner',
    'start_bot_task',
    'stop_bot_task',
    'get_bot_task',
    'get_bot_task_status'
]