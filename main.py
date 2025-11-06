# main.py
"""
INTEGRATED CRYPTO MONITOR v4.5 - Production Ready Edition
Entry point for unified monitoring system

Minimal main file - все логика вынесена в модули
"""

import sys
import asyncio
import logging

if sys.version_info < (3, 8):
    print("❌ Требуется Python 3.8 или выше")
    sys.exit(1)

from core.startup import StartupValidator
from core.monitor import IntegratedCryptoMonitor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Главная точка входа"""
    startup_validator = StartupValidator()
    
    if not startup_validator.validate_all():
        logger.error("❌ Startup validation failed")
        sys.exit(1)
    
    logger.info("🚀 Запуск Integrated Crypto Monitor v4.5...\n")
    
    monitor = IntegratedCryptoMonitor()
    
    try:
        asyncio.run(monitor.run())
    
    except KeyboardInterrupt:
        logger.info("\n⏹️ Остановка по Ctrl+C")
    
    except Exception as e:
        logger.error(f"\n❌ Критическая ошибка в main:")
        logger.exception(e)
        sys.exit(1)
    
    logger.info("\n👋 Goodbye!")


if __name__ == '__main__':
    main()