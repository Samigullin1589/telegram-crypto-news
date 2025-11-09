# core/signal_handlers.py
"""
Signal Handlers - Обработка системных сигналов
Обеспечивает graceful shutdown при SIGINT/SIGTERM
"""

import signal
import sys
from typing import Callable, Optional
from core.logging_config import get_logger

logger = get_logger(__name__)


class SignalHandler:
    """
    Обработчик системных сигналов
    
    Перехватывает SIGINT (Ctrl+C) и SIGTERM (kill)
    для graceful shutdown
    """
    
    def __init__(self, shutdown_callback: Callable[[], None]):
        """
        Args:
            shutdown_callback: Функция для вызова при получении сигнала
        """
        self.shutdown_callback = shutdown_callback
        self.original_handlers: dict = {}
        self.signal_received: Optional[int] = None
    
    def setup(self) -> None:
        """Установка обработчиков сигналов"""
        # SIGINT (Ctrl+C)
        self.original_handlers[signal.SIGINT] = signal.signal(
            signal.SIGINT,
            self._handle_signal
        )
        
        # SIGTERM (kill)
        if hasattr(signal, 'SIGTERM'):
            self.original_handlers[signal.SIGTERM] = signal.signal(
                signal.SIGTERM,
                self._handle_signal
            )
        
        logger.debug("Signal handlers configured")
    
    def _handle_signal(self, signum: int, frame) -> None:
        """
        Обработчик сигнала
        
        Args:
            signum: Номер сигнала
            frame: Stack frame
        """
        if self.signal_received is not None:
            # Повторный сигнал - форсированная остановка
            logger.warning(f"⚠️ Second signal {signum} received, forcing exit")
            sys.exit(1)
        
        self.signal_received = signum
        signal_name = signal.Signals(signum).name
        logger.info(f"⏹️ Signal {signal_name} ({signum}) received")
        
        # Вызываем callback для graceful shutdown
        self.shutdown_callback()
    
    def restore(self) -> None:
        """Восстановление оригинальных обработчиков"""
        for sig, handler in self.original_handlers.items():
            signal.signal(sig, handler)
        
        self.original_handlers.clear()
        logger.debug("Signal handlers restored")