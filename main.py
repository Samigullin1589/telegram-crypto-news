# main.py
import asyncio
import signal
from bot.processor import NewsProcessor
from app.scheduler import WhaleScheduler

class IntegratedBot:
    """
    Интегрированная система:
    - Кит-монитор (whale events + discovery)
    - Новостной бот (с умным гейтом)
    
    Один канал (CHAT_ID) для обеих систем
    """
    
    def __init__(self):
        self.news_processor = NewsProcessor()
        self.whale_scheduler = WhaleScheduler()
        self.shutdown_event = asyncio.Event()
    
    async def run(self):
        """Запускает обе системы параллельно"""
        
        print("=" * 80)
        print("🚀 INTEGRATED CRYPTO MONITOR v2.0")
        print("=" * 80)
        print("📰 Новостной бот: активен (с умным гейтом)")
        print("🐋 Кит-монитор: активен (Discovery + умные фильтры)")
        print("=" * 80)
        
        # Регистрируем обработчик сигналов
        loop = asyncio.get_event_loop()
        
        try:
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))
        except NotImplementedError:
            # Windows не поддерживает add_signal_handler
            print("⚠️  Signal handlers не поддерживаются на этой платформе")
        
        try:
            # Запускаем обе системы параллельно
            await asyncio.gather(
                self.news_processor.run(),
                self.whale_scheduler.run(),
                self._wait_for_shutdown()
            )
        except asyncio.CancelledError:
            print("\n[INFO] Задачи отменены")
        finally:
            await self.cleanup()
    
    async def _wait_for_shutdown(self):
        """Ждёт сигнала остановки"""
        await self.shutdown_event.wait()
    
    async def shutdown(self):
        """Корректное завершение"""
        print("\n⏹️  [SHUTDOWN] Получен сигнал остановки...")
        await self.whale_scheduler.shutdown()
        self.shutdown_event.set()
    
    async def cleanup(self):
        """Финальная очистка"""
        print("🧹 [CLEANUP] Завершение работы...")
        print("✅ [DONE] Все системы остановлены")

if __name__ == '__main__':
    print("✅ [INIT] Запуск интегрированного бота v2.0...")
    
    bot = IntegratedBot()
    
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\n[STOP] Бот остановлен вручную (Ctrl+C)")
    except Exception as e:
        print(f"❌ [CRITICAL] Непредвиденная ошибка: {e}")
        import traceback
        traceback.print_exc()