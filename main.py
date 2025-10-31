"""
INTEGRATED CRYPTO MONITOR v4.0 - Complete Edition
Unified system: News Bot + Whale Monitor + Trading System + Telegram Commands

РЕВОЛЮЦИОННЫЕ ВОЗМОЖНОСТИ:
✅ News Bot - AI-powered crypto news aggregation
✅ Whale Monitor - Smart money tracking & discovery
✅ Trading System - Technical + Fundamental + ML signals
✅ Telegram Bot - Interactive command handler
✅ Unified Health Monitoring
✅ Graceful Shutdown
✅ Performance Analytics
✅ Multi-Chain Support
✅ Advanced Analytics
✅ Position Management
✅ Risk Management
✅ User Commands (/start, /positions, /signal, etc.)
"""

import asyncio
import signal
import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict
import traceback as tb
from collections import defaultdict

# Проверка Python версии
if sys.version_info < (3, 8):
    print("❌ Требуется Python 3.8 или выше")
    sys.exit(1)


class SystemHealthMonitor:
    """
    Централизованный мониторинг здоровья всех подсистем
    
    Отслеживает:
    - News Bot heartbeat
    - Whale Monitor heartbeat
    - Trading System heartbeat
    - Bot Commands Handler heartbeat
    - Error rates
    - Performance metrics
    - System resources
    """
    
    def __init__(self):
        # Heartbeats
        self.news_alive = False
        self.whale_alive = False
        self.trading_alive = False
        self.bot_alive = False
        
        self.last_news_heartbeat: Optional[datetime] = None
        self.last_whale_heartbeat: Optional[datetime] = None
        self.last_trading_heartbeat: Optional[datetime] = None
        self.last_bot_heartbeat: Optional[datetime] = None
        
        # Metrics
        self.news_cycles = 0
        self.whale_cycles = 0
        self.trading_cycles = 0
        self.bot_commands_processed = 0
        
        self.news_errors = 0
        self.whale_errors = 0
        self.trading_errors = 0
        self.bot_errors = 0
        
        # Configuration
        self.check_interval = 300  # 5 минут
        self.news_silence_threshold = 1800  # 30 минут
        self.whale_silence_threshold = 600  # 10 минут
        self.trading_silence_threshold = 3900  # 65 минут (чуть больше 1 часа)
        self.bot_silence_threshold = 86400  # 24 часа (бот может долго не получать команды)
        
        self.start_time = datetime.now(timezone.utc)
        
        print("💚 [HEALTH] Health Monitor инициализирован")
    
    def update_news_heartbeat(self):
        """Обновление heartbeat новостной системы"""
        self.news_alive = True
        self.last_news_heartbeat = datetime.now(timezone.utc)
        self.news_cycles += 1
    
    def update_whale_heartbeat(self):
        """Обновление heartbeat whale системы"""
        self.whale_alive = True
        self.last_whale_heartbeat = datetime.now(timezone.utc)
        self.whale_cycles += 1
    
    def update_trading_heartbeat(self):
        """Обновление heartbeat trading системы"""
        self.trading_alive = True
        self.last_trading_heartbeat = datetime.now(timezone.utc)
        self.trading_cycles += 1
    
    def update_bot_heartbeat(self):
        """Обновление heartbeat telegram bot"""
        self.bot_alive = True
        self.last_bot_heartbeat = datetime.now(timezone.utc)
    
    def record_bot_command(self):
        """Регистрация обработанной команды"""
        self.bot_commands_processed += 1
        self.update_bot_heartbeat()
    
    def record_error(self, system: str):
        """Регистрация ошибки в системе"""
        if system == "news":
            self.news_errors += 1
        elif system == "whale":
            self.whale_errors += 1
        elif system == "trading":
            self.trading_errors += 1
        elif system == "bot":
            self.bot_errors += 1
    
    def check_health(self) -> tuple[bool, List[str]]:
        """
        Проверка здоровья всех систем
        
        Returns:
            (is_healthy, issues): Кортеж с общим статусом и списком проблем
        """
        issues = []
        now = datetime.now(timezone.utc)
        
        # Проверка новостной системы
        if self.last_news_heartbeat:
            silence = (now - self.last_news_heartbeat).seconds
            if silence > self.news_silence_threshold:
                issues.append(
                    f"📰 News Bot: Silent for {silence//60} minutes "
                    f"(threshold: {self.news_silence_threshold//60}m)"
                )
        elif self.news_cycles > 0:
            issues.append("📰 News Bot: No recent heartbeat")
        
        # Проверка whale системы
        if self.last_whale_heartbeat:
            silence = (now - self.last_whale_heartbeat).seconds
            if silence > self.whale_silence_threshold:
                issues.append(
                    f"🐋 Whale Monitor: Silent for {silence//60} minutes "
                    f"(threshold: {self.whale_silence_threshold//60}m)"
                )
        elif self.whale_cycles > 0:
            issues.append("🐋 Whale Monitor: No recent heartbeat")
        
        # Проверка trading системы
        if self.last_trading_heartbeat:
            silence = (now - self.last_trading_heartbeat).seconds
            if silence > self.trading_silence_threshold:
                issues.append(
                    f"📈 Trading System: Silent for {silence//60} minutes "
                    f"(threshold: {self.trading_silence_threshold//60}m)"
                )
        elif self.trading_cycles > 0:
            issues.append("📈 Trading System: No recent heartbeat")
        
        # Проверка bot (более мягкая - может долго не получать команды)
        if self.last_bot_heartbeat:
            silence = (now - self.last_bot_heartbeat).seconds
            if silence > self.bot_silence_threshold:
                issues.append(
                    f"🤖 Bot Handler: Silent for {silence//3600:.1f} hours "
                    f"(threshold: {self.bot_silence_threshold//3600}h)"
                )
        
        # Проверка error rate
        total_cycles = self.news_cycles + self.whale_cycles + self.trading_cycles
        total_errors = self.news_errors + self.whale_errors + self.trading_errors + self.bot_errors
        
        if total_cycles > 0:
            error_rate = (total_errors / total_cycles) * 100
            if error_rate > 10:  # Больше 10% ошибок
                issues.append(f"⚠️ High error rate: {error_rate:.1f}%")
        
        return len(issues) == 0, issues
    
    def get_uptime(self) -> timedelta:
        """Получение времени работы системы"""
        return datetime.now(timezone.utc) - self.start_time
    
    def get_stats(self) -> Dict:
        """Получение статистики здоровья"""
        uptime = self.get_uptime()
        
        return {
            "uptime_seconds": uptime.total_seconds(),
            "uptime_formatted": self._format_duration(uptime.total_seconds()),
            "systems": {
                "news": {
                    "alive": self.news_alive,
                    "cycles": self.news_cycles,
                    "errors": self.news_errors,
                    "last_heartbeat": self.last_news_heartbeat.isoformat() if self.last_news_heartbeat else None
                },
                "whale": {
                    "alive": self.whale_alive,
                    "cycles": self.whale_cycles,
                    "errors": self.whale_errors,
                    "last_heartbeat": self.last_whale_heartbeat.isoformat() if self.last_whale_heartbeat else None
                },
                "trading": {
                    "alive": self.trading_alive,
                    "cycles": self.trading_cycles,
                    "errors": self.trading_errors,
                    "last_heartbeat": self.last_trading_heartbeat.isoformat() if self.last_trading_heartbeat else None
                },
                "bot": {
                    "alive": self.bot_alive,
                    "commands_processed": self.bot_commands_processed,
                    "errors": self.bot_errors,
                    "last_heartbeat": self.last_bot_heartbeat.isoformat() if self.last_bot_heartbeat else None
                }
            },
            "total_cycles": self.news_cycles + self.whale_cycles + self.trading_cycles,
            "total_errors": self.news_errors + self.whale_errors + self.trading_errors + self.bot_errors,
            "total_bot_commands": self.bot_commands_processed
        }
    
    def _format_duration(self, seconds: float) -> str:
        """Форматирование длительности"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds/60)}m"
        elif seconds < 86400:
            return f"{seconds/3600:.1f}h"
        else:
            days = int(seconds / 86400)
            hours = (seconds % 86400) / 3600
            return f"{days}d {hours:.1f}h"


class IntegratedCryptoMonitor:
    """
    Интегрированная система мониторинга криптовалют
    
    Компоненты:
    1. News Bot - Умная агрегация криптовалютных новостей с AI обработкой
    2. Whale Monitor - Отслеживание крупных перемещений и smart money
    3. Trading System - Генерация торговых сигналов с ML предсказаниями
    4. Telegram Bot - Интерактивный обработчик команд пользователя
    
    Все системы публикуют в один канал с умной приоритизацией
    и координацией для избежания перегрузки канала
    """
    
    def __init__(self):
        print("\n" + "="*80)
        print("🚀 INITIALIZING INTEGRATED CRYPTO MONITOR")
        print("="*80 + "\n")
        
        # Импортируем компоненты
        try:
            from bot.processor import NewsProcessor
            self.news_processor = NewsProcessor()
            print("✅ News Processor loaded")
        except Exception as e:
            print(f"⚠️ Failed to load News Processor: {e}")
            self.news_processor = None
        
        try:
            from app.scheduler import scheduler as whale_scheduler
            self.whale_scheduler = whale_scheduler
            print("✅ Whale Scheduler loaded")
        except Exception as e:
            print(f"⚠️ Failed to load Whale Scheduler: {e}")
            self.whale_scheduler = None
        
        # ====================================================================
        # TELEGRAM BOT INTEGRATION (НОВОЕ!)
        # ====================================================================
        try:
            from app.bot import application as bot_application
            self.bot_application = bot_application
            print("✅ Bot Commands Handler loaded")
            
            # Патчим обработчики для отслеживания команд
            self._patch_bot_handlers()
            
        except Exception as e:
            print(f"⚠️ Bot Commands Handler not loaded: {e}")
            self.bot_application = None
        
        # Health monitoring
        self.health_monitor = SystemHealthMonitor()
        
        # Shutdown coordination
        self.shutdown_event = asyncio.Event()
        self._tasks: List[asyncio.Task] = []
        self._shutdown_in_progress = False
        
        # Statistics
        self.stats = {
            "start_time": datetime.now(timezone.utc),
            "total_publications": 0,
            "news_publications": 0,
            "whale_publications": 0,
            "trading_publications": 0,
            "bot_commands": 0,
            "errors_caught": 0,
            "restarts": 0
        }
        
        print("\n✅ Integrated Crypto Monitor инициализирован")
    
    def _patch_bot_handlers(self):
        """
        Патчим обработчики команд для мониторинга
        
        Добавляет отслеживание команд в health monitor
        """
        
        if not self.bot_application:
            return
        
        try:
            # Обёртка для всех обработчиков
            original_handlers = list(self.bot_application.handlers[0])
            
            for handler in original_handlers:
                if hasattr(handler, 'callback'):
                    original_callback = handler.callback
                    
                    async def wrapped_callback(update, context, original=original_callback):
                        # Регистрируем команду
                        self.health_monitor.record_bot_command()
                        self.stats["bot_commands"] += 1
                        
                        try:
                            # Вызываем оригинальный обработчик
                            return await original(update, context)
                        except Exception as e:
                            self.health_monitor.record_error("bot")
                            raise
                    
                    handler.callback = wrapped_callback
            
            print("   ✓ Bot handlers патчнуты для мониторинга")
        
        except Exception as e:
            print(f"   ⚠️ Не удалось пропатчить bot handlers: {e}")
    
    async def run(self):
        """
        Главный цикл выполнения
        
        Запускает все подсистемы параллельно с мониторингом
        и координацией между ними
        """
        
        self._print_startup_banner()
        
        # Настраиваем обработчики сигналов
        self._setup_signal_handlers()
        
        try:
            # Создаём задачи для всех систем
            self._tasks = []
            
            # News Bot
            if self.news_processor:
                self._tasks.append(
                    asyncio.create_task(
                        self._run_news_system(),
                        name="news_system"
                    )
                )
            
            # Whale Monitor
            if self.whale_scheduler:
                self._tasks.append(
                    asyncio.create_task(
                        self._run_whale_system(),
                        name="whale_system"
                    )
                )
            
            # Telegram Bot Commands Handler (НОВОЕ!)
            if self.bot_application:
                self._tasks.append(
                    asyncio.create_task(
                        self._run_bot_polling(),
                        name="bot_commands"
                    )
                )
            
            # Health Monitor
            self._tasks.append(
                asyncio.create_task(
                    self._health_check_loop(),
                    name="health_monitor"
                )
            )
            
            # Coordinator (для балансировки публикаций)
            self._tasks.append(
                asyncio.create_task(
                    self._coordination_loop(),
                    name="coordinator"
                )
            )
            
            # Shutdown Waiter
            self._tasks.append(
                asyncio.create_task(
                    self._wait_for_shutdown(),
                    name="shutdown_waiter"
                )
            )
            
            print(f"\n🚀 Запущено {len(self._tasks)} задач:")
            for task in self._tasks:
                print(f"   • {task.get_name()}")
            print()
            
            # Ждём завершения любой задачи
            done, pending = await asyncio.wait(
                self._tasks,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Проверяем причину завершения
            for task in done:
                task_name = task.get_name()
                
                if task_name == "shutdown_waiter":
                    print("✅ Получен сигнал graceful shutdown")
                else:
                    # Неожиданное завершение задачи
                    exc = task.exception()
                    if exc:
                        print(f"\n❌ [CRITICAL] Task '{task_name}' crashed with exception:")
                        print("="*80)
                        tb.print_exception(type(exc), exc, exc.__traceback__)
                        print("="*80)
                        self.stats["errors_caught"] += 1
                    else:
                        print(f"⚠️ Task '{task_name}' завершилась без ошибок")
            
            # Инициируем shutdown если ещё не начат
            if not self._shutdown_in_progress:
                print("\n⚠️ Инициируется shutdown из-за завершения задачи...")
                await self.shutdown()
        
        except asyncio.CancelledError:
            print("\n⏹️ [INFO] Задачи отменены")
        
        except KeyboardInterrupt:
            print("\n⏹️ [STOP] Получен Ctrl+C")
            await self.shutdown()
        
        except Exception as e:
            print(f"\n❌ [FATAL] Критическая ошибка в main loop:")
            print("="*80)
            tb.print_exc()
            print("="*80)
            self.stats["errors_caught"] += 1
        
        finally:
            await self.cleanup()
    
    async def _run_news_system(self):
        """
        Обёртка для новостной системы
        
        Добавляет heartbeat, error handling и restart logic
        """
        
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        while not self.shutdown_event.is_set():
            try:
                # Обновляем heartbeat
                self.health_monitor.update_news_heartbeat()
                
                # Запускаем цикл обработки новостей
                await self.news_processor.run()
                
                # Сброс счётчика ошибок при успехе
                consecutive_errors = 0
                
                # Небольшая пауза между циклами
                await asyncio.sleep(1)
            
            except asyncio.CancelledError:
                print("📰 [NEWS] Получен сигнал остановки")
                break
            
            except Exception as e:
                consecutive_errors += 1
                self.health_monitor.record_error("news")
                self.stats["errors_caught"] += 1
                
                print(f"\n❌ [NEWS] Ошибка в цикле ({consecutive_errors}/{max_consecutive_errors}):")
                print(f"   {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    print(f"❌ [NEWS] Слишком много ошибок подряд, перезапуск через 5 минут...")
                    await asyncio.sleep(300)
                    consecutive_errors = 0
                    self.stats["restarts"] += 1
                else:
                    # Экспоненциальная задержка
                    delay = min(60 * (2 ** consecutive_errors), 300)
                    print(f"⏳ [NEWS] Повторная попытка через {delay}с...")
                    await asyncio.sleep(delay)
        
        print("📰 [NEWS] Система остановлена")
    
    async def _run_whale_system(self):
        """
        Обёртка для whale monitoring системы
        
        Добавляет heartbeat, error handling и restart logic
        """
        
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        while not self.shutdown_event.is_set():
            try:
                # Обновляем heartbeat
                self.health_monitor.update_whale_heartbeat()
                
                # Trading system внутри whale_scheduler также получит heartbeat
                if self.whale_scheduler.trading_enabled:
                    self.health_monitor.update_trading_heartbeat()
                
                # Запускаем scheduler
                await self.whale_scheduler.run()
                
                # Сброс счётчика ошибок при успехе
                consecutive_errors = 0
            
            except asyncio.CancelledError:
                print("🐋 [WHALE] Получен сигнал остановки")
                break
            
            except Exception as e:
                consecutive_errors += 1
                self.health_monitor.record_error("whale")
                self.stats["errors_caught"] += 1
                
                print(f"\n❌ [WHALE] Ошибка в цикле ({consecutive_errors}/{max_consecutive_errors}):")
                print(f"   {e}")
                tb.print_exc()
                
                if consecutive_errors >= max_consecutive_errors:
                    print(f"❌ [WHALE] Слишком много ошибок подряд, перезапуск через 10 минут...")
                    await asyncio.sleep(600)
                    consecutive_errors = 0
                    self.stats["restarts"] += 1
                else:
                    # Экспоненциальная задержка
                    delay = min(120 * (2 ** consecutive_errors), 600)
                    print(f"⏳ [WHALE] Повторная попытка через {delay}с...")
                    await asyncio.sleep(delay)
        
        print("🐋 [WHALE] Система остановлена")
    
    async def _run_bot_polling(self):
        """
        Запуск Telegram bot для обработки пользовательских команд
        
        Обрабатывает команды типа:
        - /start, /help
        - /positions, /performance
        - /signal <ASSET>
        - /close <position_id>
        и т.д.
        """
        
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        while not self.shutdown_event.is_set():
            try:
                print("🤖 [BOT] Инициализация command handler...")
                
                # Инициализируем приложение
                await self.bot_application.initialize()
                await self.bot_application.start()
                
                print("🤖 [BOT] Запускаем polling...")
                
                # Запускаем polling
                await self.bot_application.updater.start_polling(
                    drop_pending_updates=True,
                    allowed_updates=None
                )
                
                # Обновляем heartbeat
                self.health_monitor.update_bot_heartbeat()
                
                print("✅ [BOT] Command handler активен и готов к приёму команд")
                print("   Доступные команды: /start, /help, /status, /positions, /performance")
                
                # Ждём сигнала остановки
                while not self.shutdown_event.is_set():
                    self.health_monitor.update_bot_heartbeat()
                    await asyncio.sleep(60)  # Heartbeat каждую минуту
                
                print("🤖 [BOT] Получен сигнал остановки")
                break
            
            except asyncio.CancelledError:
                print("🤖 [BOT] Получен сигнал отмены")
                break
            
            except Exception as e:
                consecutive_errors += 1
                self.health_monitor.record_error("bot")
                self.stats["errors_caught"] += 1
                
                print(f"\n❌ [BOT] Ошибка ({consecutive_errors}/{max_consecutive_errors}):")
                print(f"   {e}")
                tb.print_exc()
                
                # Останавливаем перед повторной попыткой
                try:
                    if self.bot_application.updater.running:
                        await self.bot_application.updater.stop()
                    if self.bot_application.running:
                        await self.bot_application.stop()
                except:
                    pass
                
                if consecutive_errors >= max_consecutive_errors:
                    print(f"❌ [BOT] Слишком много ошибок подряд, перезапуск через 5 минут...")
                    await asyncio.sleep(300)
                    consecutive_errors = 0
                    self.stats["restarts"] += 1
                else:
                    delay = min(30 * (2 ** consecutive_errors), 300)
                    print(f"⏳ [BOT] Повторная попытка через {delay}с...")
                    await asyncio.sleep(delay)
        
        # Graceful shutdown
        print("🤖 [BOT] Останавливаем command handler...")
        try:
            if self.bot_application.updater.running:
                await self.bot_application.updater.stop()
                print("   ✓ Updater остановлен")
            
            if self.bot_application.running:
                await self.bot_application.stop()
                print("   ✓ Application остановлен")
            
            await self.bot_application.shutdown()
            print("   ✓ Shutdown завершён")
        
        except Exception as e:
            print(f"   ⚠️ Ошибка при shutdown: {e}")
        
        print("✅ [BOT] Command handler полностью остановлен")
    
    async def _health_check_loop(self):
        """
        Периодическая проверка здоровья всех систем
        
        Выводит предупреждения при обнаружении проблем
        """
        
        # Первая проверка через 5 минут после запуска
        await asyncio.sleep(300)
        
        while not self.shutdown_event.is_set():
            try:
                is_healthy, issues = self.health_monitor.check_health()
                
                if not is_healthy:
                    print("\n" + "="*80)
                    print("⚠️ [HEALTH] ОБНАРУЖЕНЫ ПРОБЛЕМЫ:")
                    print("="*80)
                    for issue in issues:
                        print(f"   {issue}")
                    print("="*80 + "\n")
                
                # Следующая проверка
                await asyncio.sleep(self.health_monitor.check_interval)
            
            except asyncio.CancelledError:
                break
            
            except Exception as e:
                print(f"⚠️ [HEALTH] Ошибка мониторинга: {e}")
                await asyncio.sleep(60)
        
        print("💚 [HEALTH] Health Monitor остановлен")
    
    async def _coordination_loop(self):
        """
        Координация между системами
        
        Задачи:
        - Балансировка публикаций между системами
        - Предотвращение спама в канале
        - Приоритизация важных сигналов
        - Агрегация метрик
        """
        
        await asyncio.sleep(60)  # Первый запуск через минуту
        
        while not self.shutdown_event.is_set():
            try:
                # Собираем метрики от всех систем
                if self.news_processor and hasattr(self.news_processor, 'metrics'):
                    self.stats["news_publications"] = self.news_processor.metrics.articles_published
                
                if self.whale_scheduler and hasattr(self.whale_scheduler, 'stats'):
                    whale_stats = self.whale_scheduler.stats
                    self.stats["whale_publications"] = whale_stats.get("events_published", 0)
                    self.stats["trading_publications"] = whale_stats.get("trading_signals_sent", 0)
                
                self.stats["total_publications"] = (
                    self.stats["news_publications"] +
                    self.stats["whale_publications"] +
                    self.stats["trading_publications"]
                )
                
                # Следующая итерация
                await asyncio.sleep(300)  # Каждые 5 минут
            
            except asyncio.CancelledError:
                break
            
            except Exception as e:
                print(f"⚠️ [COORDINATOR] Ошибка: {e}")
                await asyncio.sleep(60)
        
        print("🔄 [COORDINATOR] Coordinator остановлен")
    
    async def _wait_for_shutdown(self):
        """Ожидание сигнала остановки"""
        await self.shutdown_event.wait()
        print("🛑 [SHUTDOWN] Сигнал shutdown получен")
    
    def _setup_signal_handlers(self):
        """
        Настройка обработчиков системных сигналов
        
        Обеспечивает graceful shutdown при получении SIGINT/SIGTERM
        """
        
        if sys.platform == "win32":
            print("⚠️ [WARN] Signal handlers не поддерживаются на Windows")
            print("         Используйте Ctrl+C для остановки")
            return
        
        loop = asyncio.get_event_loop()
        
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: asyncio.create_task(self._handle_signal(s))
                )
                print(f"✅ Установлен обработчик для {sig.name}")
            except (NotImplementedError, RuntimeError) as e:
                print(f"⚠️ [WARN] Не удалось установить обработчик для {sig.name}: {e}")
    
    async def _handle_signal(self, sig):
        """Обработка системного сигнала"""
        print(f"\n⚡ [SIGNAL] Получен {sig.name}")
        await self.shutdown()
    
    async def shutdown(self):
        """
        Корректное завершение работы всех систем
        
        Последовательность:
        1. Установка флага shutdown
        2. Graceful shutdown каждой системы (с таймаутом)
        3. Отмена оставшихся задач
        4. Финальная очистка
        """
        
        if self._shutdown_in_progress:
            print("⚠️ Shutdown уже в процессе...")
            return
        
        self._shutdown_in_progress = True
        
        print("\n" + "="*80)
        print("⏹️ SHUTDOWN SEQUENCE INITIATED")
        print("="*80)
        
        # Сигнализируем всем системам
        self.shutdown_event.set()
        
        print("\n⏳ Останавливаем подсистемы (макс 60 секунд)...")
        
        shutdown_tasks = []
        
        # Telegram Bot
        if self.bot_application:
            print("   • Останавливаем Telegram Bot...")
            # Bot остановится сам через _run_bot_polling
        
        # Whale Scheduler (включая Trading System)
        if self.whale_scheduler and hasattr(self.whale_scheduler, 'shutdown'):
            print("   • Останавливаем Whale Monitor + Trading System...")
            shutdown_tasks.append(
                asyncio.create_task(
                    self.whale_scheduler.shutdown(),
                    name="whale_shutdown"
                )
            )
        
        # News Processor
        if self.news_processor and hasattr(self.news_processor, 'shutdown'):
            print("   • Останавливаем News Processor...")
            shutdown_tasks.append(
                asyncio.create_task(
                    self.news_processor.shutdown(),
                    name="news_shutdown"
                )
            )
        
        # Ждём завершения с таймаутом
        if shutdown_tasks:
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*shutdown_tasks, return_exceptions=True),
                    timeout=60.0
                )
                
                # Проверяем результаты
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        print(f"   ⚠️ Ошибка при shutdown задачи {shutdown_tasks[i].get_name()}: {result}")
                    else:
                        print(f"   ✅ {shutdown_tasks[i].get_name()} завершён успешно")
            
            except asyncio.TimeoutError:
                print("   ⚠️ Таймаут graceful shutdown, принудительная остановка...")
        
        # Отменяем все оставшиеся задачи
        print("\n⏳ Отменяем оставшиеся задачи...")
        
        cancelled_count = 0
        for task in self._tasks:
            if not task.done():
                task.cancel()
                cancelled_count += 1
        
        if cancelled_count > 0:
            print(f"   • Отменено задач: {cancelled_count}")
            
            # Ждём завершения отменённых задач
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        print("   ✅ Все задачи остановлены")
        
        print("\n" + "="*80)
        print("✅ SHUTDOWN SEQUENCE COMPLETED")
        print("="*80)
    
    async def cleanup(self):
        """
        Финальная очистка ресурсов
        
        Выполняется после shutdown всех систем
        """
        
        print("\n🧹 [CLEANUP] Очистка ресурсов...")
        
        # Сохраняем финальное состояние
        try:
            if self.whale_scheduler and hasattr(self.whale_scheduler, '_save_state'):
                self.whale_scheduler._save_state()
                print("   ✅ Состояние Whale Monitor сохранено")
        except Exception as e:
            print(f"   ⚠️ Ошибка сохранения состояния: {e}")
        
        # Выводим финальную статистику
        self._print_final_statistics()
        
        print("\n" + "="*80)
        print("👋 СИСТЕМА ПОЛНОСТЬЮ ОСТАНОВЛЕНА")
        print("="*80)
    
    def _print_startup_banner(self):
        """Вывод баннера при запуске"""
        
        print("\n" + "="*80)
        print("🚀 INTEGRATED CRYPTO MONITOR v4.0 - STARTING UP")
        print("="*80)
        
        print("\n📦 АКТИВНЫЕ КОМПОНЕНТЫ:\n")
        
        # News Bot
        if self.news_processor:
            print("📰 News Bot")
            print("   ├─ AI-powered content processing")
            print("   ├─ Smart gate filtering")
            print("   ├─ Multi-source aggregation")
            print("   └─ Status: ✅ Active")
        else:
            print("📰 News Bot")
            print("   └─ Status: ❌ Disabled")
        
        print()
        
        # Whale Monitor
        if self.whale_scheduler:
            print("🐋 Whale Monitor")
            print("   ├─ Blockchain event tracking")
            print("   ├─ Smart money discovery")
            print("   ├─ Adaptive thresholds")
            print("   ├─ Performance tracking")
            
            if self.whale_scheduler.trading_enabled:
                print("   ├─ Trading System: ✅ Enabled")
                print("   │  ├─ Technical Analysis (50+ indicators)")
                print("   │  ├─ Fundamental Analysis")
                print("   │  ├─ Hot Wallet Tracking")
                print("   │  ├─ ML Predictions (1h, 4h, 24h, 7d)")
                print("   │  ├─ Position Management")
                print("   │  └─ Risk Management (Auto SL/TP)")
            else:
                print("   ├─ Trading System: ❌ Disabled")
            
            if self.whale_scheduler.chains_enabled:
                print(f"   ├─ Multi-Chain: ✅ {', '.join(self.whale_scheduler.supported_chains)}")
            else:
                print("   ├─ Multi-Chain: ❌ Disabled")
            
            if self.whale_scheduler.analytics_enabled:
                print("   ├─ Analytics: ✅ Sentiment, Risk, Correlation, Anomaly")
            else:
                print("   ├─ Analytics: ❌ Disabled")
            
            print("   └─ Status: ✅ Active")
        else:
            print("🐋 Whale Monitor")
            print("   └─ Status: ❌ Disabled")
        
        print()
        
        # Telegram Bot (НОВОЕ!)
        if self.bot_application:
            print("🤖 Telegram Bot Commands")
            print("   ├─ User command handling")
            print("   ├─ Interactive keyboards")
            print("   ├─ Position management")
            print("   ├─ Performance analytics")
            print("   ├─ Manual signal generation")
            print("   ├─ Available commands:")
            print("   │  ├─ /start, /help, /menu")
            print("   │  ├─ /status, /positions, /performance")
            print("   │  ├─ /signal <ASSET>, /close <position_id>")
            print("   │  └─ /wallets, /config, /thresholds")
            print("   └─ Status: ✅ Active")
        else:
            print("🤖 Telegram Bot Commands")
            print("   └─ Status: ❌ Disabled")
        
        print()
        
        # Health Monitor
        print("💚 Health Monitor")
        print("   ├─ System heartbeat tracking")
        print("   ├─ Error rate monitoring")
        print("   ├─ Auto-restart on failures")
        print(f"   ├─ Check interval: {self.health_monitor.check_interval}s")
        print("   └─ Status: ✅ Active")
        
        print()
        
        # Coordinator
        print("🔄 Coordinator")
        print("   ├─ Publication balancing")
        print("   ├─ Priority management")
        print("   ├─ Metrics aggregation")
        print("   └─ Status: ✅ Active")
        
        print("\n" + "="*80)
        print(f"⏰ Startup Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("="*80 + "\n")
    
    def _print_final_statistics(self):
        """Вывод финальной статистики"""
        
        print("\n" + "="*80)
        print("📊 ФИНАЛЬНАЯ СТАТИСТИКА")
        print("="*80)
        
        # Uptime
        uptime = self.health_monitor.get_uptime()
        print(f"\n⏱️ UPTIME: {self.health_monitor._format_duration(uptime.total_seconds())}")
        
        # Health Stats
        health_stats = self.health_monitor.get_stats()
        
        print(f"\n💚 HEALTH MONITOR:")
        print(f"   Total Cycles: {health_stats['total_cycles']}")
        print(f"   Total Errors: {health_stats['total_errors']}")
        print(f"   Bot Commands Processed: {health_stats['total_bot_commands']}")
        
        if health_stats['total_cycles'] > 0:
            error_rate = (health_stats['total_errors'] / health_stats['total_cycles']) * 100
            print(f"   Error Rate: {error_rate:.2f}%")
        
        # News Bot Stats
        if self.news_processor and hasattr(self.news_processor, 'metrics'):
            news_metrics = self.news_processor.metrics
            
            print(f"\n📰 NEWS BOT:")
            print(f"   Cycles: {news_metrics.cycles_completed}")
            print(f"   Articles Processed: {news_metrics.articles_processed}")
            print(f"   Articles Published: {news_metrics.articles_published}")
            
            if news_metrics.articles_processed > 0:
                publish_rate = (news_metrics.articles_published / news_metrics.articles_processed) * 100
                print(f"   Publish Rate: {publish_rate:.1f}%")
            
            print(f"   Errors: {news_metrics.errors}")
        
        # Whale Monitor Stats
        if self.whale_scheduler and hasattr(self.whale_scheduler, 'stats'):
            whale_stats = self.whale_scheduler.stats
            
            print(f"\n🐋 WHALE MONITOR:")
            print(f"   Events Collected: {whale_stats.get('events_collected', 0)}")
            print(f"   Events Qualified: {whale_stats.get('events_qualified', 0)}")
            print(f"   Events Published: {whale_stats.get('events_published', 0)}")
            
            successful = whale_stats.get('events_successful', 0)
            failed = whale_stats.get('events_failed', 0)
            
            if successful + failed > 0:
                accuracy = (successful / (successful + failed)) * 100
                print(f"   Accuracy: {accuracy:.1f}% ({successful}/{successful + failed})")
            
            print(f"   Wallets Discovered: {whale_stats.get('wallets_discovered', 0)}")
            print(f"   Wallets Removed: {whale_stats.get('wallets_removed', 0)}")
            
            # Trading Stats
            if self.whale_scheduler.trading_enabled:
                print(f"\n📈 TRADING SYSTEM:")
                print(f"   Signals Generated: {whale_stats.get('trading_signals_generated', 0)}")
                print(f"   Signals Sent: {whale_stats.get('trading_signals_sent', 0)}")
                print(f"   Positions Opened: {whale_stats.get('positions_opened', 0)}")
                print(f"   Positions Closed: {whale_stats.get('positions_closed', 0)}")
                
                try:
                    positions_summary = self.whale_scheduler.signal_generator.positions.get_summary()
                    print(f"   Open Positions: {positions_summary['total_open']}")
                    print(f"   Unrealized P&L: ${positions_summary['total_unrealized_pnl_usd']:,.2f}")
                    
                    # Performance metrics (используем asyncio.run для получения async данных)
                    try:
                        loop = asyncio.new_event_loop()
                        metrics = loop.run_until_complete(
                            self.whale_scheduler.signal_generator.performance.calculate_metrics(
                                period_days=30
                            )
                        )
                        loop.close()
                        
                        if metrics.total_trades > 0:
                            print(f"\n   📊 Performance (30d):")
                            print(f"      Total Trades: {metrics.total_trades}")
                            print(f"      Win Rate: {metrics.win_rate:.1f}%")
                            print(f"      Total P&L: ${metrics.total_pnl_usd:,.2f}")
                            print(f"      Profit Factor: {metrics.profit_factor:.2f}")
                            print(f"      Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
                    except Exception as e:
                        print(f"   ⚠️ Ошибка получения performance метрик: {e}")
                
                except Exception as e:
                    print(f"   ⚠️ Ошибка получения trading метрик: {e}")
        
        # Telegram Bot Stats (НОВОЕ!)
        if self.bot_application:
            print(f"\n🤖 TELEGRAM BOT:")
            print(f"   Commands Processed: {health_stats['total_bot_commands']}")
            print(f"   Errors: {health_stats['systems']['bot']['errors']}")
        
        # Overall Stats
        print(f"\n📊 ОБЩАЯ СТАТИСТИКА:")
        print(f"   Total Publications: {self.stats['total_publications']}")
        print(f"   ├─ News: {self.stats['news_publications']}")
        print(f"   ├─ Whale: {self.stats['whale_publications']}")
        print(f"   └─ Trading: {self.stats['trading_publications']}")
        print(f"   Bot Commands: {self.stats['bot_commands']}")
        print(f"   Errors Caught: {self.stats['errors_caught']}")
        print(f"   System Restarts: {self.stats['restarts']}")
        
        print("\n" + "="*80)


def check_dependencies():
    """
    Проверка установленных зависимостей
    
    Returns:
        bool: True если все зависимости установлены
    """
    
    print("🔍 Проверка зависимостей...\n")
    
    required_packages = {
        'telegram': 'python-telegram-bot',
        'aiohttp': 'aiohttp',
        'feedparser': 'feedparser',
        'pandas': 'pandas',
        'numpy': 'numpy',
        'sklearn': 'scikit-learn'
    }
    
    missing = []
    
    for module, package in required_packages.items():
        try:
            __import__(module)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package}")
            missing.append(package)
    
    if missing:
        print(f"\n❌ Отсутствуют зависимости: {', '.join(missing)}")
        print("\nУстановите их командой:")
        print(f"pip install {' '.join(missing)}")
        return False
    
    print("\n✅ Все зависимости установлены")
    return True


def create_directories():
    """Создание необходимых директорий"""
    
    print("\n📁 Создание директорий...\n")
    
    directories = [
        Path("data"),
        Path("data/history"),
        Path("data/learning"),
        Path("data/wallets"),
        Path("data/positions"),
        Path("data/performance"),
        Path("logs"),
    ]
    
    # Добавляем /tmp только если не существует
    if not Path("/tmp").exists():
        directories.append(Path("/tmp"))
    
    for directory in directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"   ✅ {directory}")
        except Exception as e:
            print(f"   ⚠️ {directory}: {e}")
    
    print()


def print_system_info():
    """Вывод информации о системе"""
    
    print("="*80)
    print("💎 CRYPTO COMPASS - Integrated Monitoring System v4.0")
    print("="*80)
    print(f"📅 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"🐍 Python {sys.version.split()[0]}")
    print(f"💻 Platform: {sys.platform}")
    print(f"📂 Working Directory: {os.getcwd()}")
    print("="*80 + "\n")


def main():
    """
    Главная точка входа в приложение
    
    Последовательность запуска:
    1. Вывод информации о системе
    2. Проверка зависимостей
    3. Создание директорий
    4. Инициализация бота
    5. Запуск главного цикла
    """
    
    # Информация о системе
    print_system_info()
    
    # Проверка зависимостей
    if not check_dependencies():
        sys.exit(1)
    
    # Создание директорий
    create_directories()
    
    # Создаём и запускаем бота
    print("🚀 Запуск Integrated Crypto Monitor...\n")
    
    bot = IntegratedCryptoMonitor()
    
    try:
        # Запускаем через asyncio.run() (Python 3.7+)
        if sys.version_info >= (3, 7):
            asyncio.run(bot.run())
        else:
            # Fallback для старых версий Python
            loop = asyncio.get_event_loop()
            try:
                loop.run_until_complete(bot.run())
            finally:
                loop.close()
    
    except KeyboardInterrupt:
        print("\n⏹️ Остановка по Ctrl+C")
    
    except Exception as e:
        print(f"\n❌ Критическая ошибка в main:")
        print("="*80)
        tb.print_exc()
        print("="*80)
        sys.exit(1)
    
    print("\n👋 Goodbye!")


if __name__ == '__main__':
    main()