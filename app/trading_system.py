# app/trading_system.py
"""
TRADING SYSTEM FACADE v4.0
========================================
Унифицированный интерфейс для модульной Trading System

Этот файл - простой wrapper, который:
1. Импортирует SignalGenerator из app.trading
2. Проверяет TRADING_ENABLED
3. Предоставляет единый интерфейс для scheduler
"""

import asyncio
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime

# Settings
from app.settings import (
    TRADING_ENABLED,
    TRADING_MIN_CONFIDENCE,
    TRADING_MAX_SIGNALS_PER_DAY,
    TRADING_SIGNAL_COOLDOWN_MINUTES,
    TRADING_MAX_POSITION_SIZE_USD,
    TRADING_MAX_OPEN_POSITIONS,
    TRADING_DEFAULT_STOP_LOSS_PERCENT,
    TRADING_DEFAULT_TAKE_PROFIT_PERCENT,
    TRADING_MIN_TECHNICAL_SCORE,
    TRADING_MIN_FUNDAMENTAL_SCORE,
    TRADING_MIN_ML_CONFIDENCE,
    TRADING_DRY_RUN,
    COINGECKO_API_KEY,
)

# Модульная Trading System
try:
    from app.trading.signal_generator import SignalGenerator, TradingSignal
    from app.trading.position_tracker import PositionTracker
    from app.trading.performance_stats import PerformanceStats
    TRADING_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ [TRADING_SYSTEM] Модули не найдены: {e}")
    TRADING_AVAILABLE = False
    SignalGenerator = None
    TradingSignal = None
    PositionTracker = None
    PerformanceStats = None


class TradingSystem:
    """
    Facade для Trading System
    
    Простой wrapper вокруг SignalGenerator с дополнительными проверками
    """
    
    def __init__(self):
        """Инициализация Trading System"""
        
        self.enabled = TRADING_ENABLED and TRADING_AVAILABLE
        self.dry_run = TRADING_DRY_RUN
        
        # Настройки
        self.min_confidence = TRADING_MIN_CONFIDENCE
        self.max_signals_per_day = TRADING_MAX_SIGNALS_PER_DAY
        self.cooldown_minutes = TRADING_SIGNAL_COOLDOWN_MINUTES
        
        # Компоненты
        self.signal_generator = None
        self.positions = None
        self.performance = None
        
        if self.enabled and TRADING_AVAILABLE:
            try:
                # Инициализируем SignalGenerator
                self.signal_generator = SignalGenerator(coingecko_key=COINGECKO_API_KEY)
                
                # Получаем ссылки на компоненты
                self.positions = self.signal_generator.positions
                self.performance = self.signal_generator.performance
                
                print(f"\n{'='*80}")
                print(f"📈 TRADING SYSTEM v4.0 - INITIALIZED")
                print(f"{'='*80}")
                print(f"Status: ✅ ENABLED")
                print(f"Mode: {'🧪 DRY RUN' if self.dry_run else '💰 LIVE'}")
                print(f"Min Confidence: {self.min_confidence}/100")
                print(f"Max Signals/Day: {self.max_signals_per_day}")
                print(f"Cooldown: {self.cooldown_minutes} minutes")
                print(f"Technical Score Filter: ≥{TRADING_MIN_TECHNICAL_SCORE}")
                print(f"Fundamental Score Filter: ≥{TRADING_MIN_FUNDAMENTAL_SCORE}")
                print(f"ML Confidence Filter: ≥{TRADING_MIN_ML_CONFIDENCE}%")
                print(f"{'='*80}\n")
                
            except Exception as e:
                print(f"❌ [TRADING_SYSTEM] Ошибка инициализации: {e}")
                import traceback
                traceback.print_exc()
                self.enabled = False
        else:
            print(f"\n{'='*80}")
            print(f"📈 TRADING SYSTEM v4.0")
            print(f"{'='*80}")
            if not TRADING_ENABLED:
                print(f"Status: ❌ DISABLED (TRADING_ENABLED=false)")
            elif not TRADING_AVAILABLE:
                print(f"Status: ❌ DISABLED (модули не найдены)")
            print(f"{'='*80}\n")
    
    def is_enabled(self) -> bool:
        """Проверка включен ли Trading System"""
        return self.enabled and self.signal_generator is not None
    
    async def generate_signal(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        session
    ) -> Optional[Dict]:
        """
        Генерация торгового сигнала
        
        Args:
            symbol: Тикер актива
            price_data: DataFrame с OHLCV данными
            session: aiohttp session
        
        Returns:
            Signal dict или None
        """
        if not self.is_enabled():
            return None
        
        try:
            # Генерируем сигнал через SignalGenerator
            signal = await self.signal_generator.generate_signal(
                asset=symbol,
                price_data=price_data,
                session=session
            )
            
            if not signal:
                return None
            
            # Фильтруем по confidence
            if signal.confidence < self.min_confidence:
                print(f"⚠️ [TRADING] Сигнал {symbol} отфильтрован: confidence {signal.confidence:.1f} < {self.min_confidence}")
                return None
            
            # Конвертируем в dict для совместимости
            return signal.to_dict()
            
        except Exception as e:
            print(f"❌ [TRADING_SYSTEM] Ошибка генерации сигнала {symbol}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def get_open_positions(self) -> List[Dict]:
        """Получить открытые позиции"""
        if not self.is_enabled() or not self.positions:
            return []
        
        try:
            open_pos = self.positions.get_open_positions()
            return [pos.to_dict() for pos in open_pos]
        except Exception as e:
            print(f"❌ [TRADING_SYSTEM] Ошибка получения позиций: {e}")
            return []
    
    async def get_performance_stats(self) -> Dict:
        """Получить статистику производительности"""
        if not self.is_enabled() or not self.performance:
            return {
                'total_signals': 0,
                'total_trades': 0,
                'win_rate': 0,
                'avg_profit': 0,
                'total_pnl': 0
            }
        
        try:
            return self.performance.get_summary_stats()
        except Exception as e:
            print(f"❌ [TRADING_SYSTEM] Ошибка получения статистики: {e}")
            return {
                'total_signals': 0,
                'total_trades': 0,
                'win_rate': 0,
                'avg_profit': 0,
                'total_pnl': 0
            }
    
    async def update_positions(self, price_provider=None) -> List[Dict]:
        """
        Обновить позиции (проверить SL/TP)
        
        Args:
            price_provider: Provider для получения текущих цен
        
        Returns:
            Список закрытых позиций
        """
        if not self.is_enabled() or not self.positions:
            return []
        
        try:
            # Обновляем позиции
            closed = []
            open_positions = self.positions.get_open_positions()
            
            for position in open_positions:
                # Получаем текущую цену
                if price_provider and hasattr(price_provider, 'get_price'):
                    try:
                        current_price = await price_provider.get_price(position.asset)
                        
                        # Обновляем позицию
                        updated = self.positions.update_position(position.id, current_price)
                        
                        # Если позиция закрылась - добавляем в список
                        if updated and updated.status != 'OPEN':
                            closed.append(updated.to_dict())
                    except Exception as e:
                        print(f"⚠️ [TRADING] Ошибка обновления позиции {position.asset}: {e}")
            
            return closed
            
        except Exception as e:
            print(f"❌ [TRADING_SYSTEM] Ошибка обновления позиций: {e}")
            return []
    
    def format_signal_for_telegram(self, signal: Dict) -> str:
        """
        Форматировать сигнал для Telegram
        
        Args:
            signal: Signal dict
        
        Returns:
            Formatted message (HTML)
        """
        if not self.is_enabled():
            return ""
        
        try:
            # Если signal уже TradingSignal объект
            if hasattr(signal, 'format_signal_message'):
                return signal.format_signal_message()
            
            # Если dict - используем SignalGenerator
            if self.signal_generator:
                # Создаем TradingSignal из dict (упрощенно)
                from app.trading.signal_generator import TradingSignal as TS
                
                ts = TS(
                    asset=signal.get('asset', 'UNKNOWN'),
                    timestamp=datetime.fromisoformat(signal.get('timestamp', datetime.utcnow().isoformat())),
                    signal=signal.get('signal', 'HOLD'),
                    confidence=signal.get('confidence', 0),
                    technical=signal.get('technical'),
                    fundamental=signal.get('fundamental'),
                    wallet=signal.get('wallet'),
                    ml=signal.get('ml'),
                    entry_price=signal.get('recommendations', {}).get('entry_price', 0),
                    stop_loss=signal.get('recommendations', {}).get('stop_loss'),
                    take_profit=signal.get('recommendations', {}).get('take_profit'),
                    position_size_pct=signal.get('recommendations', {}).get('position_size_pct', 0),
                    reasons=signal.get('reasons', []),
                    warnings=signal.get('warnings', [])
                )
                
                return self.signal_generator.format_signal_message(ts)
            
        except Exception as e:
            print(f"❌ [TRADING_SYSTEM] Ошибка форматирования: {e}")
            import traceback
            traceback.print_exc()
        
        return ""
    
    def get_config(self) -> Dict:
        """Получить текущую конфигурацию"""
        return {
            'enabled': self.enabled,
            'dry_run': self.dry_run,
            'min_confidence': self.min_confidence,
            'max_signals_per_day': self.max_signals_per_day,
            'cooldown_minutes': self.cooldown_minutes,
            'min_technical_score': TRADING_MIN_TECHNICAL_SCORE,
            'min_fundamental_score': TRADING_MIN_FUNDAMENTAL_SCORE,
            'min_ml_confidence': TRADING_MIN_ML_CONFIDENCE,
            'max_position_size': TRADING_MAX_POSITION_SIZE_USD,
            'max_open_positions': TRADING_MAX_OPEN_POSITIONS,
            'default_stop_loss': TRADING_DEFAULT_STOP_LOSS_PERCENT,
            'default_take_profit': TRADING_DEFAULT_TAKE_PROFIT_PERCENT,
        }


# ============================================================================
# INITIALIZATION CHECK
# ============================================================================

if TRADING_AVAILABLE:
    print("✅ [TRADING_SYSTEM] Trading System modules loaded successfully")
else:
    print("⚠️ [TRADING_SYSTEM] Trading System modules not available")