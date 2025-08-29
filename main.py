# main.py
import asyncio
from bot.processor import NewsProcessor

if __name__ == '__main__':
    print("✅ [INIT] Запуск бота v13.0 (Multi-File Architecture)...")
    processor = NewsProcessor()
    try:
        asyncio.run(processor.run())
    except (KeyboardInterrupt, SystemExit):
        print("\n[STOP] Бот остановлен вручную.")
    except Exception as e:
        print(f"❌ [CRITICAL] Произошла непредвиденная ошибка: {e}")