"""
INTEGRATED CRYPTO MONITOR v2.0
Unified system: News Bot + Whale Monitor
"""

import asyncio
import signal
import sys
from pathlib import Path
from datetime import datetime, timezone
from bot.processor import NewsProcessor
from app.scheduler import WhaleScheduler


class SystemHealthMonitor:
    """Мониторинг здоровья обеих систем"""
    
    def __init__(self):
        self.news_alive = False
        self.whale_alive = False
        self.last_news_heartbeat = None
        self.last_whale_heartbeat = None
        self.check_interval = 300  # 5 минут
    
    def update_news_heartbeat(self):
        """Обновление heartbeat новостной системы"""
        self.news_alive = True
        self.last_news_heartbeat = datetime.now(timezone.utc)
    
    def update_whale_heartbeat(self):
        """Обновление heartbeat whale системы"""
        self.whale_alive = True
        self.last_whale_heartbeat = datetime.now(timezone.utc)
    
    def check_health(self) -> tuple[bool, list]:
        """
        Проверка здоровья систем
        Returns: (is_healthy, issues)
        """
        issues = []
        now = datetime.now(timezone.utc)
        
        # Проверка новостной системы
        if self.last_news_heartbeat:
            silence = (now - self.last_news_heartbeat).seconds
            if silence > 1800:  # 30 минут тишины
                issues.append(f"News system silent for {silence//60} minutes")
        
        # Проверка whale системы
        if self.last_whale_heartbeat:
            silence = (now - self.last_whale_heartbeat).seconds
            if silence > 600:  # 10 минут тишины
                issues.append(f"Whale system silent for {silence//60} minutes")
        
        return len(issues) == 0, issues


class IntegratedBot:
    """
    Интегрированная криптовалютная система мониторинга
    
    Компоненты:
    - News Bot: Умная агрегация крипто-новостей с AI обработкой
    - Whale Monitor: Отслеживание крупных перемещений и smart money
    
    Обе системы публикуют в один канал с умной приоритизацией
    """
    
    def __init__(self):
        self.news_processor = NewsProcessor()
        self.whale_scheduler = WhaleScheduler()
        self.health_monitor = SystemHealthMonitor()
        self.shutdown_event = asyncio.Event()
        self._tasks = []
        self._shutdown_in_progress = False
        
        print("🤖 [INIT] Integrated Bot инициализирован")
    
    async def run(self):
        """Запускает обе системы параллельно с мониторингом здоровья"""
        
        self._print_banner()
        
        # Регистрируем обработчики сигналов (graceful shutdown)
        self._setup_signal_handlers()
        
        try:
            # Запускаем системы параллельно
            self._tasks = [
                asyncio.create_task(self._run_news_system(), name="news_system"),
                asyncio.create_task(self._run_whale_system(), name="whale_system"),
                asyncio.create_task(self._health_check_loop(), name="health_monitor"),
                asyncio.create_task(self._wait_for_shutdown(), name="shutdown_waiter")
            ]
            
            # Ждём завершения любой задачи или сигнала остановки
            done, pending = await asyncio.wait(
                self._tasks,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Если какая-то задача завершилась неожиданно
            for task in done:
                if task.get_name() != "shutdown_waiter":
                    exc = task.exception()
                    if exc:
                        print(f"❌ [CRITICAL] Task {task.get_name()} failed: {exc}")
                        import traceback
                        traceback.print_exception(type(exc), exc, exc.__traceback__)
            
            # Останавливаем остальные задачи
            if not self._shutdown_in_progress:
                await self.shutdown()
            
        except asyncio.CancelledError:
            print("\n⏹️  [INFO] Задачи отменены")
        except KeyboardInterrupt:
            print("\n⏹️  [STOP] Получен Ctrl+C")
            await self.shutdown()
        except Exception as e:
            print(f"\n❌ [FATAL] Критическая ошибка: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.cleanup()
    
    async def _run_news_system(self):
        """Обёртка для новостной системы с heartbeat"""
        try:
            while not self.shutdown_event.is_set():
                self.health_monitor.update_news_heartbeat()
                await self.news_processor.run()
        except Exception as e:
            print(f"❌ [NEWS] Критическая ошибка: {e}")
            raise
    
    async def _run_whale_system(self):
        """Обёртка для whale системы с heartbeat"""
        try:
            while not self.shutdown_event.is_set():
                self.health_monitor.update_whale_heartbeat()
                await self.whale_scheduler.run()
        except Exception as e:
            print(f"❌ [WHALE] Критическая ошибка: {e}")
            raise
    
    async def _health_check_loop(self):
        """Периодическая проверка здоровья систем"""
        await asyncio.sleep(300)  # Первая проверка через 5 минут
        
        while not self.shutdown_event.is_set():
            try:
                is_healthy, issues = self.health_monitor.check_health()
                
                if not is_healthy:
                    print("\n⚠️  [HEALTH] Обнаружены проблемы:")
                    for issue in issues:
                        print(f"   - {issue}")
                    print()
                
                await asyncio.sleep(self.health_monitor.check_interval)
                
            except Exception as e:
                print(f"⚠️  [HEALTH] Ошибка мониторинга: {e}")
                await asyncio.sleep(60)
    
    async def _wait_for_shutdown(self):
        """Ожидание сигнала остановки"""
        await self.shutdown_event.wait()
    
    def _setup_signal_handlers(self):
        """Настройка обработчиков сигналов для graceful shutdown"""
        if sys.platform == "win32":
            # Windows не поддерживает add_signal_handler
            print("⚠️  [WARN] Signal handlers не поддерживаются на Windows")
            return
        
        loop = asyncio.get_event_loop()
        
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: asyncio.create_task(self._handle_signal(s))
                )
            except NotImplementedError:
                print(f"⚠️  [WARN] Не удалось установить обработчик для {sig.name}")
    
    async def _handle_signal(self, sig):
        """Обработка системных сигналов"""
        print(f"\n⏹️  [SIGNAL] Получен {sig.name}")
        await self.shutdown()
    
    async def shutdown(self):
        """Корректное завершение работы"""
        if self._shutdown_in_progress:
            return
        
        self._shutdown_in_progress = True
        
        print("\n" + "="*80)
        print("⏹️  SHUTDOWN: Начинается остановка системы...")
        print("="*80)
        
        # Сигнализируем остановку
        self.shutdown_event.set()
        
        # Даём системам время на graceful shutdown
        print("⏳ Ожидание завершения задач (макс 30с)...")
        
        shutdown_tasks = []
        
        # Останавливаем whale систему
        if hasattr(self.whale_scheduler, 'shutdown'):
            shutdown_tasks.append(
                asyncio.create_task(self.whale_scheduler.shutdown())
            )
        
        # Останавливаем новостную систему
        if hasattr(self.news_processor, 'shutdown'):
            shutdown_tasks.append(
                asyncio.create_task(self.news_processor.shutdown())
            )
        
        if shutdown_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*shutdown_tasks, return_exceptions=True),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                print("⚠️  Таймаут graceful shutdown, принудительная остановка")
        
        # Отменяем оставшиеся задачи
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        print("✅ Все задачи остановлены")
    
    async def cleanup(self):
        """Финальная очистка ресурсов"""
        print("\n🧹 [CLEANUP] Очистка ресурсов...")
        
        # Выводим финальную статистику
        self._print_final_stats()
        
        print("\n" + "="*80)
        print("✅ СИСТЕМА ПОЛНОСТЬЮ ОСТАНОВЛЕНА")
        print("="*80)
    
    def _print_banner(self):
        """Вывод баннера при запуске"""
        print("\n" + "="*80)
        print("🚀 INTEGRATED CRYPTO MONITOR v2.0")
        print("="*80)
        print("📰 News Bot: Активен (с AI обработкой и умным гейтом)")
        print("🐋 Whale Monitor: Активен (Discovery + Smart Money + Самообучение)")
        print("🔄 Health Monitor: Активен (проверка каждые 5 мин)")
        print("="*80)
        print(f"⏰ Запуск: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("="*80 + "\n")
    
    def _print_final_stats(self):
        """Вывод финальной статистики"""
        print("\n📊 ФИНАЛЬНАЯ СТАТИСТИКА:")
        print("="*80)
        
        # Статистика новостной системы
        if hasattr(self.news_processor, 'metrics'):
            news_stats = self.news_processor.metrics
            print("📰 News System:")
            print(f"   Циклов: {news_stats.cycles_completed}")
            print(f"   Обработано: {news_stats.articles_processed}")
            print(f"   Опубликовано: {news_stats.articles_published}")
            if news_stats.articles_processed > 0:
                publish_rate = (news_stats.articles_published / news_stats.articles_processed) * 100
                print(f"   Success rate: {publish_rate:.1f}%")
        
        # Статистика whale системы
        if hasattr(self.whale_scheduler, 'stats'):
            whale_stats = self.whale_scheduler.stats
            print("\n🐋 Whale System:")
            print(f"   События собрано: {whale_stats.get('events_collected', 0)}")
            print(f"   Прошло фильтры: {whale_stats.get('events_qualified', 0)}")
            print(f"   Опубликовано: {whale_stats.get('events_published', 0)}")
            print(f"   Успешных: {whale_stats.get('events_successful', 0)}")
            print(f"   Провалов: {whale_stats.get('events_failed', 0)}")
            
            if whale_stats.get('start_time'):
                uptime = datetime.now(timezone.utc) - whale_stats['start_time']
                hours = uptime.total_seconds() / 3600
                print(f"\n   Uptime: {hours:.1f}h")
        
        print("="*80)


def main():
    """
    Точка входа в приложение
    """
    print("="*80)
    print("🤖 CRYPTO COMPASS - Integrated Monitoring System")
    print("="*80)
    print(f"📅 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"🐍 Python {sys.version.split()[0]}")
    print("="*80 + "\n")
    
    # Проверка зависимостей
    try:
        import telegram
        import aiohttp
        import feedparser
        print("✅ Все зависимости установлены")
    except ImportError as e:
        print(f"❌ Отсутствует зависимость: {e}")
        print("\nУстановите зависимости: pip install -r requirements.txt")
        sys.exit(1)
    
    # Создаём необходимые директории
    dirs_to_create = [
        Path("data"),
        Path("data/history"),
        Path("data/learning"),
        Path("/tmp") if not Path("/tmp").exists() else None
    ]
    
    for dir_path in dirs_to_create:
        if dir_path:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    # Запускаем бота
    bot = IntegratedBot()
    
    try:
        # Python 3.7+
        if sys.version_info >= (3, 7):
            asyncio.run(bot.run())
        else:
            # Fallback для старых версий
            loop = asyncio.get_event_loop()
            loop.run_until_complete(bot.run())
            loop.close()
    
    except KeyboardInterrupt:
        print("\n⏹️  Остановка по Ctrl+C")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()