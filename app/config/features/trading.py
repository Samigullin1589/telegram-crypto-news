"""
Trading features module
Настройки торговой системы
"""

import logging
from typing import Dict, Any
from .base import BaseFeatureConfig

logger = logging.getLogger(__name__)


class TradingFeatures(BaseFeatureConfig):
    """
    Конфигурация торговой системы
    
    Управляет:
    - Режимами работы (dry run / live)
    - Лимитами позиций и сигналов
    - Параметрами риск-менеджмента
    - Стратегиями торговли
    """
    
    def __init__(self):
        """Инициализация конфигурации торговли"""
        
        # Основные настройки
        self.enabled = self.get_bool_env('TRADING_ENABLED', True)
        self.dry_run = self.get_bool_env('TRADING_DRY_RUN', True)
        self.paper_trading = self.get_bool_env('PAPER_TRADING', True)
        
        # Лимиты сигналов и позиций
        self.max_signals_per_day = self.get_int_env('TRADING_MAX_SIGNALS_PER_DAY', 10)
        self.max_signals_per_hour = self.get_int_env('TRADING_SIGNALS_PER_HOUR', 5)
        self.max_open_positions = self.get_int_env('TRADING_MAX_OPEN_POSITIONS', 5)
        self.max_positions_per_asset = self.get_int_env('TRADING_MAX_POSITIONS_PER_ASSET', 2)
        
        # Риск-менеджмент
        self.default_stop_loss = self.get_float_env('TRADING_DEFAULT_STOP_LOSS', 3.0)
        self.default_take_profit = self.get_float_env('TRADING_DEFAULT_TAKE_PROFIT', 5.0)
        self.max_risk_per_trade = self.get_float_env('TRADING_MAX_RISK_PER_TRADE', 2.0)
        self.max_portfolio_risk = self.get_float_env('TRADING_MAX_PORTFOLIO_RISK', 10.0)
        self.trailing_stop_enabled = self.get_bool_env('TRAILING_STOP_ENABLED', True)
        self.trailing_stop_activation = self.get_float_env('TRAILING_STOP_ACTIVATION', 2.0)
        self.trailing_stop_distance = self.get_float_env('TRAILING_STOP_DISTANCE', 1.0)
        
        # Размер позиции
        self.default_position_size = self.get_float_env('TRADING_DEFAULT_POSITION_SIZE', 100.0)
        self.min_position_size = self.get_float_env('TRADING_MIN_POSITION_SIZE', 10.0)
        self.max_position_size = self.get_float_env('TRADING_MAX_POSITION_SIZE', 1000.0)
        self.position_sizing_method = self.get_str_env('POSITION_SIZING_METHOD', 'fixed')
        
        # Пороги уверенности
        self.min_confidence = self.get_int_env('MIN_TRADING_CONFIDENCE', 75)
        self.min_signal_strength = self.get_int_env('MIN_SIGNAL_STRENGTH', 70)
        self.require_confirmation = self.get_bool_env('REQUIRE_SIGNAL_CONFIRMATION', True)
        
        # Интервалы
        self.check_interval = self.get_int_env('TRADING_CHECK_INTERVAL', 300)
        self.position_update_interval = self.get_int_env('POSITION_UPDATE_INTERVAL', 60)
        self.risk_check_interval = self.get_int_env('RISK_CHECK_INTERVAL', 120)
        
        # Стратегии
        self.strategies_enabled = self._parse_strategies()
        self.default_strategy = self.get_str_env('DEFAULT_TRADING_STRATEGY', 'momentum')
        
        # Индикаторы
        self.technical_indicators_enabled = self.get_bool_env('TECHNICAL_INDICATORS_ENABLED', True)
        self.fundamental_analysis_enabled = self.get_bool_env('FUNDAMENTAL_ANALYSIS_ENABLED', True)
        self.sentiment_analysis_enabled = self.get_bool_env('SENTIMENT_ANALYSIS_ENABLED', True)
        self.ml_predictions_enabled = self.get_bool_env('ML_PREDICTIONS_ENABLED', True)
        
        # Источники данных
        self.use_whale_data = self.get_bool_env('TRADING_USE_WHALE_DATA', True)
        self.use_news_sentiment = self.get_bool_env('TRADING_USE_NEWS_SENTIMENT', True)
        self.use_hot_wallet_data = self.get_bool_env('TRADING_USE_HOT_WALLET_DATA', True)
        
        # Логирование
        self._log_configuration()
    
    def _parse_strategies(self) -> list:
        """Парсинг включенных стратегий"""
        strategies_str = self.get_str_env('ENABLED_STRATEGIES', 'momentum,mean_reversion,breakout')
        return [s.strip().lower() for s in strategies_str.split(',')]
    
    def _log_configuration(self):
        """Логирование конфигурации"""
        mode = "DRY RUN" if self.dry_run else "LIVE TRADING"
        status = "✅ ENABLED" if self.enabled else "❌ DISABLED"
        
        logger.info(f"[TRADING] Status: {status}")
        logger.info(f"[TRADING] Mode: 🧪 {mode}")
        
        if self.enabled:
            logger.info(f"[TRADING] Limits: {self.max_signals_per_day} signals/day, "
                       f"{self.max_open_positions} positions")
            logger.info(f"[TRADING] Risk: SL={self.default_stop_loss}%, "
                       f"TP={self.default_take_profit}%")
            logger.info(f"[TRADING] Confidence: min={self.min_confidence}")
            logger.info(f"[TRADING] Strategies: {', '.join(self.strategies_enabled)}")
    
    def is_strategy_enabled(self, strategy_name: str) -> bool:
        """
        Проверка включена ли стратегия
        
        Args:
            strategy_name: Название стратегии
            
        Returns:
            bool: True если стратегия включена
        """
        return strategy_name.lower() in self.strategies_enabled
    
    def validate_position_size(self, size: float) -> bool:
        """
        Проверка размера позиции
        
        Args:
            size: Размер позиции
            
        Returns:
            bool: True если размер валиден
        """
        return self.min_position_size <= size <= self.max_position_size
    
    def validate_risk_parameters(self, stop_loss: float, take_profit: float) -> bool:
        """
        Проверка параметров риска
        
        Args:
            stop_loss: Стоп-лосс в процентах
            take_profit: Тейк-профит в процентах
            
        Returns:
            bool: True если параметры валидны
        """
        return (0 < stop_loss <= self.max_risk_per_trade and
                stop_loss < take_profit and
                take_profit <= 100)
    
    def get_data_sources(self) -> Dict[str, bool]:
        """
        Получение активных источников данных
        
        Returns:
            Dict: Словарь источников и их статусов
        """
        return {
            'whale_data': self.use_whale_data,
            'news_sentiment': self.use_news_sentiment,
            'hot_wallets': self.use_hot_wallet_data,
            'technical_indicators': self.technical_indicators_enabled,
            'fundamental_analysis': self.fundamental_analysis_enabled,
            'sentiment_analysis': self.sentiment_analysis_enabled,
            'ml_predictions': self.ml_predictions_enabled
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Конвертация в словарь
        
        Returns:
            Dict: Конфигурация торговли
        """
        return {
            'enabled': self.enabled,
            'dry_run': self.dry_run,
            'paper_trading': self.paper_trading,
            'max_signals_per_day': self.max_signals_per_day,
            'max_signals_per_hour': self.max_signals_per_hour,
            'max_open_positions': self.max_open_positions,
            'max_positions_per_asset': self.max_positions_per_asset,
            'default_stop_loss': self.default_stop_loss,
            'default_take_profit': self.default_take_profit,
            'max_risk_per_trade': self.max_risk_per_trade,
            'max_portfolio_risk': self.max_portfolio_risk,
            'trailing_stop_enabled': self.trailing_stop_enabled,
            'min_confidence': self.min_confidence,
            'min_signal_strength': self.min_signal_strength,
            'check_interval': self.check_interval,
            'strategies': self.strategies_enabled,
            'default_strategy': self.default_strategy,
            'data_sources': self.get_data_sources()
        }


__all__ = ['TradingFeatures']