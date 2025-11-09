# main.py
"""
INTEGRATED CRYPTO MONITOR v4.5 - Production Entry Point
Минимальная точка входа с делегированием в core
"""

import sys

if sys.version_info < (3, 8):
    print("❌ Python 3.8+ required")
    sys.exit(1)

from core.application import Application
from core.logging_config import setup_logging


def main() -> None:
    """Production entry point"""
    # Настройка логирования (только stdout для Render)
    setup_logging()
    
    # Запуск приложения
    app = Application()
    app.run()


if __name__ == '__main__':
    main()