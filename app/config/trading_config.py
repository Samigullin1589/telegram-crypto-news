# app/config/trading_config.py
"""
Trading Configuration Module
Конфигурация торговой системы
"""

import os
import logging
from typing import List

logger = logging.getLogger(__name__)


class TradingConfig:
    """
    Конфигурация торговой системы

    Управляет настройками автоматической торговой системы,
    включая интервалы сигналов, отслеживаемые активы и режим работы.

    Attributes:
        enabled: Включена ли торговая система
        dry_run: Режим тестирования без реальных сделок
        signal_interval_hours: Интервал генерации торговых сигналов (часы)
        monitored_assets: Список отслеживаемых активов
        position_update_interval_seconds: Интервал обновления позиций (секунды)
    """

    def __init__(self):
        """Инициализация конфигурации торговой системы"""

        # Основные настройки
        self.enabled = self._load_enabled()
        self.dry_run = self._load_dry_run()

        # Интервалы
        self.signal_interval_hours = self._load_signal_interval_hours()
        self.position_update_interval_seconds = self._load_position_update_interval()

        # Активы для мониторинга
        self.monitored_assets = self._load_monitored_assets()

        # Логирование конфигурации
        self._log_configuration()

    def _load_enabled(self) -> bool:
        """
        Загрузка флага включения торговой системы

        Returns:
            True если система включена
        """
        value = os.getenv('TRADING_ENABLED', 'true').lower()
        return value in ('true', '1', 'yes', 'on')

    def _load_dry_run(self) -> bool:
        """
        Загрузка режима dry run

        Returns:
            True если включен режим тестирования
        """
        value = os.getenv('TRADING_DRY_RUN', 'true').lower()
        return value in ('true', '1', 'yes', 'on')

    def _load_signal_interval_hours(self) -> int:
        """
        Загрузка интервала генерации сигналов

        Returns:
            Интервал в часах (по умолчанию 1)
        """
        try:
            value = int(os.getenv('TRADING_SIGNAL_INTERVAL_HOURS', '1'))
            if value < 1:
                logger.warning(
                    f"TRADING_SIGNAL_INTERVAL_HOURS слишком мал ({value}), "
                    f"используется минимум 1 час"
                )
                return 1
            return value
        except ValueError:
            logger.warning(
                f"Некорректное значение TRADING_SIGNAL_INTERVAL_HOURS, "
                f"используется 1 час"
            )
            return 1

    def _load_position_update_interval(self) -> int:
        """
        Загрузка интервала обновления позиций

        Returns:
            Интервал в секундах (по умолчанию 300)
        """
        try:
            value = int(os.getenv('TRADING_POSITION_UPDATE_INTERVAL_SECONDS', '300'))
            if value < 60:
                logger.warning(
                    f"TRADING_POSITION_UPDATE_INTERVAL_SECONDS слишком мал ({value}), "
                    f"используется минимум 60 секунд"
                )
                return 60
            return value
        except ValueError:
            logger.warning(
                f"Некорректное значение TRADING_POSITION_UPDATE_INTERVAL_SECONDS, "
                f"используется 300 секунд"
            )
            return 300

    def _load_monitored_assets(self) -> List[str]:
        """
        Загрузка списка отслеживаемых активов

        Returns:
            Список тикеров активов
        """
        default_assets = "BTC,ETH,SOL,BNB,XRP,ADA,AVAX,DOT,MATIC,LINK"
        assets_str = os.getenv('TRADING_MONITORED_ASSETS', default_assets)

        # Парсинг через запятую
        assets = [asset.strip().upper() for asset in assets_str.split(',') if asset.strip()]

        if not assets:
            logger.warning("Не указаны активы для мониторинга, используются по умолчанию")
            assets = default_assets.split(',')

        return assets

    def _log_configuration(self):
        """Логирование конфигурации"""
        logger.debug("📈 [TRADING CONFIG] Инициализирована")
        logger.debug(f"   Enabled: {self.enabled}")
        logger.debug(f"   Dry Run: {self.dry_run}")
        logger.debug(f"   Signal Interval: {self.signal_interval_hours}h")
        logger.debug(f"   Position Update: {self.position_update_interval_seconds}s")
        logger.debug(f"   Monitored Assets: {len(self.monitored_assets)} ({', '.join(self.monitored_assets[:3])}...)")

    def to_dict(self) -> dict:
        """
        Конвертация в словарь

        Returns:
            Словарь с настройками
        """
        return {
            'enabled': self.enabled,
            'dry_run': self.dry_run,
            'signal_interval_hours': self.signal_interval_hours,
            'position_update_interval_seconds': self.position_update_interval_seconds,
            'monitored_assets': self.monitored_assets,
            'monitored_assets_count': len(self.monitored_assets)
        }

    def __repr__(self) -> str:
        """Строковое представление"""
        status = "Enabled" if self.enabled else "Disabled"
        mode = "DRY RUN" if self.dry_run else "LIVE"
        return (
            f"TradingConfig("
            f"status={status}, "
            f"mode={mode}, "
            f"assets={len(self.monitored_assets)}"
            f")"
        )


__all__ = ['TradingConfig']
