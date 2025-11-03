"""
SIGNAL GENERATOR v2.0 - PRODUCTION READY
Главный компонент для генерации торговых сигналов
Объединяет технический анализ, фундаментальный анализ, hot wallet tracking и ML
"""

import aiohttp
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import pandas as pd
import numpy as np
from collections import defaultdict
import logging

from .technical_analysis import TechnicalAnalyzer, TechnicalSignal
from .fundamental_analysis import FundamentalAnalyzer, FundamentalData
from .hot_wallet_tracker import HotWalletTracker, WalletMovement
from .ml_predictor import MLPredictor, MLPrediction
from .position_tracker import PositionTracker
from .performance_stats import PerformanceStats

logger = logging.getLogger(__name__)


@dataclass
class TradingSignal:
    """Комплексный торговый сигнал"""
    asset: str
    timestamp: datetime
    
    # Общий сигнал
    signal: str  # 'STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL'
    confidence: float  # 0-100
    
    # Компоненты
    technical: Optional[TechnicalSignal]
    fundamental: Optional[FundamentalData]
    wallet: Optional[Dict]
    ml: Optional[MLPrediction]
    
    # Рекомендации
    entry_price: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    position_size_pct: float
    
    # Reasoning
    reasons: List[str]
    warnings: List[str]
    
    # Метаданные
    signal_id: str = None
    risk_score: float = 0.0
    reward_score: float = 0.0
    risk_reward_ratio: float = 0.0
    expected_duration: str = "medium"
    market_condition: str = "normal"
    
    def __post_init__(self):
        if self.signal_id is None:
            self.signal_id = f"{self.asset}_{self.timestamp.strftime('%Y%m%d%H%M%S')}"
        
        if self.stop_loss and self.take_profit:
            risk = abs(self.entry_price - self.stop_loss)
            reward = abs(self.take_profit - self.entry_price)
            self.risk_score = (risk / self.entry_price) * 100
            self.reward_score = (reward / self.entry_price) * 100
            self.risk_reward_ratio = reward / risk if risk > 0 else 0.0
    
    def to_dict(self) -> dict:
        return {
            'signal_id': self.signal_id,
            'asset': self.asset,
            'timestamp': self.timestamp.isoformat(),
            'signal': self.signal,
            'confidence': self.confidence,
            'technical': self.technical.to_dict() if self.technical else None,
            'fundamental': self.fundamental.to_dict() if self.fundamental else None,
            'wallet': self.wallet,
            'ml': self.ml.to_dict() if self.ml else None,
            'recommendations': {
                'entry_price': self.entry_price,
                'stop_loss': self.stop_loss,
                'take_profit': self.take_profit,
                'position_size_pct': self.position_size_pct,
                'risk_score': self.risk_score,
                'reward_score': self.reward_score,
                'risk_reward_ratio': self.risk_reward_ratio,
                'expected_duration': self.expected_duration
            },
            'reasons': self.reasons,
            'warnings': self.warnings,
            'market_condition': self.market_condition
        }
    
    def is_tradeable(self) -> bool:
        """Проверяет, можно ли торговать по этому сигналу"""
        if self.signal == 'HOLD':
            return False
        
        if self.confidence < 60:
            return False
        
        if self.risk_reward_ratio < 1.5:
            return False
        
        if len(self.warnings) > 3:
            return False
        
        return True
    
    def get_priority_score(self) -> float:
        """Рассчитывает приоритет сигнала для ранжирования"""
        score = self.confidence
        
        if self.signal in ['STRONG_BUY', 'STRONG_SELL']:
            score *= 1.2
        
        if self.risk_reward_ratio >= 3.0:
            score *= 1.15
        elif self.risk_reward_ratio >= 2.0:
            score *= 1.05
        
        if self.wallet and self.wallet.get('dominant_signal') == 'ACCUMULATION':
            if self.wallet.get('net_flow_usd', 0) > 1_000_000:
                score *= 1.1
        
        score -= len(self.warnings) * 2
        
        return max(0, min(100, score))


class SignalGenerator:
    """
    Главный генератор торговых сигналов
    
    Объединяет:
    - Технический анализ (50+ индикаторов)
    - Фундаментальный анализ (токеномика, метрики)
    - Hot wallet движения (accumulation/distribution)
    - ML предсказания (4 временных интервала)
    
    Управляет:
    - Position Tracker (открытие/закрытие позиций)
    - Performance Stats (метрики эффективности)
    """
    
    def __init__(self, coingecko_key: Optional[str] = None):
        # Аналитические компоненты
        self.technical = TechnicalAnalyzer()
        self.fundamental = FundamentalAnalyzer(coingecko_key)
        self.hot_wallet = HotWalletTracker(coingecko_key)
        self.ml = MLPredictor()
        
        # Управление позициями
        self.positions = PositionTracker()
        self.performance = PerformanceStats(self.positions)
        
        # Кэш для оптимизации
        self.signal_cache: Dict[str, Tuple[TradingSignal, datetime]] = {}
        self.cache_ttl_minutes = 5
        
        self.price_cache: Dict[str, Tuple[float, datetime]] = {}
        self.price_cache_ttl = timedelta(minutes=1)
        
        # История сгенерированных сигналов
        self.signal_history: List[TradingSignal] = []
        self.max_history_size = 1000
        
        # Статистика
        self.stats = {
            'total_signals_generated': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0,
            'last_signal_at': None
        }
        
        # Веса компонентов (динамические, могут обновляться)
        self.component_weights = {
            'technical': 0.30,
            'fundamental': 0.20,
            'wallet': 0.25,
            'ml': 0.25
        }
        
        logger.info("🚀 [SIGNAL_GENERATOR] Инициализирован")
        logger.info("   • Technical Analysis: ✓")
        logger.info("   • Fundamental Analysis: ✓")
        logger.info("   • Hot Wallet Tracker: ✓")
        logger.info("   • ML Predictor: ✓")
        logger.info("   • Position Tracker: ✓")
        logger.info("   • Performance Stats: ✓")
    
    async def generate_signal(
        self,
        asset: str,
        price_data: pd.DataFrame,
        session: aiohttp.ClientSession,
        force_refresh: bool = False
    ) -> Optional[TradingSignal]:
        """
        Генерация комплексного торгового сигнала
        
        Args:
            asset: Символ актива (BTC, ETH, etc)
            price_data: DataFrame с OHLCV данными
            session: aiohttp session
            force_refresh: Игнорировать кэш
        
        Returns:
            TradingSignal или None если недостаточно данных
        """
        
        # Проверяем кэш
        if not force_refresh:
            cached_signal = self._get_from_cache(asset)
            if cached_signal:
                self.stats['cache_hits'] += 1
                logger.debug(f"[SIGNAL_GEN] Возврат из кэша: {asset}")
                return cached_signal
        
        self.stats['cache_misses'] += 1
        
        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"🔍 [SIGNAL_GEN] Анализ {asset}")
            logger.info(f"{'='*80}")
            
            # Валидация входных данных
            if not self._validate_price_data(price_data):
                logger.error(f"❌ [SIGNAL_GEN] Невалидные price данные для {asset}")
                self.stats['errors'] += 1
                return None
            
            # 1. Технический анализ
            logger.info(f"📊 [1/4] Технический анализ...")
            technical_signal = await self._safe_technical_analysis(asset, price_data)
            
            if not technical_signal:
                logger.error(f"❌ [SIGNAL_GEN] Недостаточно данных для технического анализа {asset}")
                self.stats['errors'] += 1
                return None
            
            logger.info(f"   ✓ Signal: {technical_signal.signal_type}")
            logger.info(f"   ✓ Strength: {technical_signal.strength:.1f}")
            logger.info(f"   ✓ RSI: {technical_signal.rsi:.1f}")
            logger.info(f"   ✓ Trend: {technical_signal.trend}")
            
            # 2. Фундаментальный анализ
            logger.info(f"📈 [2/4] Фундаментальный анализ...")
            fundamental_data = await self._safe_fundamental_analysis(asset, session)
            
            if fundamental_data:
                logger.info(f"   ✓ Rating: {fundamental_data.rating}")
                logger.info(f"   ✓ Score: {fundamental_data.fundamental_score:.1f}/100")
                if fundamental_data.market_cap_rank:
                    logger.info(f"   ✓ Rank: #{fundamental_data.market_cap_rank}")
            else:
                logger.warning(f"   ⚠️ Фундаментальные данные недоступны")
            
            # 3. Hot wallet анализ
            logger.info(f"🔥 [3/4] Анализ wallet движений...")
            wallet_analysis = await self._safe_wallet_analysis(asset)
            
            if wallet_analysis:
                logger.info(f"   ✓ Signal: {wallet_analysis['dominant_signal']}")
                logger.info(f"   ✓ Net Flow: ${wallet_analysis['net_flow_usd']:,.0f}")
                logger.info(f"   ✓ Movements: {wallet_analysis['total_moves']}")
            else:
                logger.info(f"   ⚠️ Нет wallet активности")
            
            # 4. ML предсказание
            logger.info(f"🤖 [4/4] ML предсказание...")
            ml_prediction = await self._safe_ml_prediction(
                asset,
                technical_signal,
                fundamental_data,
                wallet_analysis
            )
            
            if ml_prediction:
                logger.info(f"   ✓ Prediction: {ml_prediction.prediction}")
                logger.info(f"   ✓ Confidence: {ml_prediction.confidence:.1f}%")
                logger.info(f"   ✓ Expected 1h: {ml_prediction.expected_change_1h:+.2f}%")
                logger.info(f"   ✓ Expected 24h: {ml_prediction.expected_change_24h:+.2f}%")
                logger.info(f"   ✓ Expected 7d: {ml_prediction.expected_change_7d:+.2f}%")
            else:
                logger.warning(f"   ⚠️ ML предсказание недоступно")
            
            # 5. Определяем рыночные условия
            market_condition = self._assess_market_condition(
                technical_signal,
                fundamental_data,
                wallet_analysis
            )
            
            logger.info(f"\n🌍 Рыночные условия: {market_condition}")
            
            # 6. Комбинируем сигналы
            logger.info(f"\n⚡ Комбинирование сигналов...")
            final_signal, confidence, reasons, warnings = self._combine_signals(
                technical_signal,
                fundamental_data,
                wallet_analysis,
                ml_prediction,
                market_condition
            )
            
            logger.info(f"   ✓ Final Signal: {final_signal}")
            logger.info(f"   ✓ Confidence: {confidence:.1f}%")
            
            # 7. Рассчитываем рекомендации
            logger.info(f"\n💡 Расчёт рекомендаций...")
            entry_price = technical_signal.price
            stop_loss, take_profit, position_size, expected_duration = self._calculate_recommendations(
                asset,
                entry_price,
                final_signal,
                technical_signal,
                ml_prediction,
                market_condition
            )
            
            if stop_loss:
                sl_pct = abs((stop_loss - entry_price) / entry_price * 100)
                logger.info(f"   ✓ Stop-Loss: ${stop_loss:,.2f} (-{sl_pct:.1f}%)")
            
            if take_profit:
                tp_pct = abs((take_profit - entry_price) / entry_price * 100)
                logger.info(f"   ✓ Take-Profit: ${take_profit:,.2f} (+{tp_pct:.1f}%)")
            
            logger.info(f"   ✓ Position Size: {position_size:.1f}% of capital")
            logger.info(f"   ✓ Expected Duration: {expected_duration}")
            
            # 8. Создаем сигнал
            signal = TradingSignal(
                asset=asset,
                timestamp=datetime.utcnow(),
                signal=final_signal,
                confidence=confidence,
                technical=technical_signal,
                fundamental=fundamental_data,
                wallet=wallet_analysis,
                ml=ml_prediction,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                position_size_pct=position_size,
                reasons=reasons,
                warnings=warnings,
                expected_duration=expected_duration,
                market_condition=market_condition
            )
            
            # 9. Валидация финального сигнала
            validation_warnings = self._validate_signal(signal)
            if validation_warnings:
                signal.warnings.extend(validation_warnings)
            
            logger.info(f"\n{'='*80}")
            logger.info(f"✅ [SIGNAL_GEN] Сигнал сгенерирован для {asset}")
            logger.info(f"   Priority Score: {signal.get_priority_score():.1f}")
            logger.info(f"   Tradeable: {'Yes' if signal.is_tradeable() else 'No'}")
            logger.info(f"{'='*80}\n")
            
            # Кэшируем
            self._add_to_cache(asset, signal)
            
            # Добавляем в историю
            self._add_to_history(signal)
            
            # Обновляем статистику
            self.stats['total_signals_generated'] += 1
            self.stats['last_signal_at'] = datetime.utcnow()
            
            return signal
            
        except Exception as e:
            logger.error(f"❌ [SIGNAL_GEN] Ошибка генерации сигнала для {asset}: {e}")
            import traceback
            traceback.print_exc()
            self.stats['errors'] += 1
            return None
    
    async def generate_signals_batch(
        self,
        assets: List[str],
        price_data_dict: Dict[str, pd.DataFrame],
        session: aiohttp.ClientSession,
        max_concurrent: int = 5
    ) -> List[TradingSignal]:
        """
        Генерация сигналов для нескольких активов параллельно
        
        Args:
            assets: Список символов активов
            price_data_dict: {asset: price_dataframe}
            session: aiohttp session
            max_concurrent: Максимум одновременных запросов
        
        Returns:
            Список TradingSignal
        """
        
        import asyncio
        
        signals = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def generate_with_semaphore(asset: str):
            async with semaphore:
                price_data = price_data_dict.get(asset)
                if price_data is None:
                    logger.warning(f"⚠️ Нет price данных для {asset}")
                    return None
                
                return await self.generate_signal(asset, price_data, session)
        
        tasks = [generate_with_semaphore(asset) for asset in assets]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, TradingSignal):
                signals.append(result)
            elif isinstance(result, Exception):
                logger.error(f"❌ Ошибка генерации: {result}")
        
        # Сортируем по приоритету
        signals.sort(key=lambda s: s.get_priority_score(), reverse=True)
        
        return signals
    
    def _validate_price_data(self, df: pd.DataFrame) -> bool:
        """Валидация price данных"""
        if df is None or df.empty:
            return False
        
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_columns):
            return False
        
        if len(df) < 20:
            return False
        
        if df[required_columns].isnull().any().any():
            return False
        
        if (df[['open', 'high', 'low', 'close', 'volume']] <= 0).any().any():
            return False
        
        return True
    
    async def _safe_technical_analysis(
        self,
        asset: str,
        price_data: pd.DataFrame
    ) -> Optional[TechnicalSignal]:
        """Технический анализ с обработкой ошибок"""
        try:
            return await self.technical.analyze(asset, price_data)
        except Exception as e:
            logger.error(f"❌ Ошибка технического анализа для {asset}: {e}")
            return None
    
    async def _safe_fundamental_analysis(
        self,
        asset: str,
        session: aiohttp.ClientSession
    ) -> Optional[FundamentalData]:
        """Фундаментальный анализ с обработкой ошибок"""
        try:
            return await self.fundamental.analyze(asset, session)
        except Exception as e:
            logger.warning(f"⚠️ Ошибка фундаментального анализа для {asset}: {e}")
            return None
    
    async def _safe_wallet_analysis(self, asset: str) -> Optional[Dict]:
        """Wallet анализ с обработкой ошибок"""
        try:
            return self.hot_wallet.get_cluster_analysis(asset, hours=6)
        except Exception as e:
            logger.warning(f"⚠️ Ошибка wallet анализа для {asset}: {e}")
            return None
    
    async def _safe_ml_prediction(
        self,
        asset: str,
        technical: Optional[TechnicalSignal],
        fundamental: Optional[FundamentalData],
        wallet: Optional[Dict]
    ) -> Optional[MLPrediction]:
        """ML предсказание с обработкой ошибок"""
        try:
            if not technical:
                return None
            
            technical_data = technical.indicators if technical else {}
            fundamental_data = fundamental.to_dict() if fundamental else {}
            
            return await self.ml.predict(
                asset=asset,
                technical_data=technical_data,
                fundamental_data=fundamental_data,
                wallet_data=wallet
            )
        except Exception as e:
            logger.warning(f"⚠️ Ошибка ML предсказания для {asset}: {e}")
            return None
    
    def _assess_market_condition(
        self,
        technical: TechnicalSignal,
        fundamental: Optional[FundamentalData],
        wallet: Optional[Dict]
    ) -> str:
        """
        Оценка рыночных условий
        
        Returns:
            'bull_market', 'bear_market', 'ranging', 'volatile', 'normal'
        """
        
        volatility_score = 0
        trend_score = 0
        
        # Анализ технических данных
        if technical:
            atr_pct = (technical.indicators.get('atr', 0) / technical.price) * 100
            
            if atr_pct > 5:
                volatility_score += 2
            elif atr_pct > 3:
                volatility_score += 1
            
            if technical.trend == 'strong_uptrend':
                trend_score += 2
            elif technical.trend == 'uptrend':
                trend_score += 1
            elif technical.trend == 'strong_downtrend':
                trend_score -= 2
            elif technical.trend == 'downtrend':
                trend_score -= 1
            
            if technical.volume_trend == 'increasing':
                trend_score += 0.5
            elif technical.volume_trend == 'decreasing':
                trend_score -= 0.5
        
        # Анализ фундаментальных данных
        if fundamental:
            if fundamental.price_change_24h:
                if abs(fundamental.price_change_24h) > 10:
                    volatility_score += 1
            
            if fundamental.price_change_7d:
                if fundamental.price_change_7d > 20:
                    trend_score += 1
                elif fundamental.price_change_7d < -20:
                    trend_score -= 1
        
        # Анализ wallet активности
        if wallet:
            if wallet.get('dominant_signal') == 'ACCUMULATION':
                trend_score += 0.5
            elif wallet.get('dominant_signal') == 'DISTRIBUTION':
                trend_score -= 0.5
        
        # Определяем условия
        if volatility_score >= 3:
            return 'volatile'
        elif trend_score >= 2:
            return 'bull_market'
        elif trend_score <= -2:
            return 'bear_market'
        elif abs(trend_score) < 1 and volatility_score < 2:
            return 'ranging'
        else:
            return 'normal'
    
    def _combine_signals(
        self,
        technical: TechnicalSignal,
        fundamental: Optional[FundamentalData],
        wallet: Optional[Dict],
        ml: Optional[MLPrediction],
        market_condition: str
    ) -> Tuple[str, float, List[str], List[str]]:
        """
        Комбинирование сигналов в финальный
        
        Веса адаптируются к рыночным условиям:
        - Bull market: больше вес на momentum индикаторы
        - Bear market: больше вес на защиту
        - Volatile: больше вес на технический анализ
        - Ranging: больше вес на mean reversion
        
        Returns:
            (signal, confidence, reasons, warnings)
        """
        
        signals = []
        weights = []
        reasons = []
        warnings = []
        
        # Адаптируем веса к рыночным условиям
        adapted_weights = self._adapt_weights_to_market(market_condition)
        
        # 1. Технический сигнал
        tech_score = self._signal_to_score(technical.signal_type)
        signals.append(tech_score)
        weights.append(adapted_weights['technical'])
        
        # Добавляем причины
        top_reasons = technical.reasons[:3]
        for reason in top_reasons:
            reasons.append(f"[TECH] {reason}")
        
        # Предупреждения
        for warning in technical.warnings:
            warnings.append(f"[TECH] {warning}")
        
        # Дополнительная информация о силе тренда
        if technical.trend in ['strong_uptrend', 'strong_downtrend']:
            reasons.append(f"[TECH] Strong trend detected: {technical.trend.replace('_', ' ').title()}")
        
        # 2. Фундаментальный анализ
        if fundamental:
            fund_score = self._rating_to_score(fundamental.rating)
            signals.append(fund_score)
            weights.append(adapted_weights['fundamental'])
            
            reasons.append(f"[FUND] Rating: {fundamental.rating}, Score: {fundamental.fundamental_score:.1f}/100")
            
            if fundamental.market_cap_rank and fundamental.market_cap_rank <= 20:
                reasons.append(f"[FUND] Top-20 asset by market cap (#{fundamental.market_cap_rank})")
                fund_score *= 1.05
            
            if fundamental.market_cap_rank and fundamental.market_cap_rank > 200:
                warnings.append(f"[FUND] Low market cap rank (#{fundamental.market_cap_rank}) - higher risk")
            
            if fundamental.developer_score and fundamental.developer_score > 70:
                reasons.append(f"[FUND] Strong developer activity ({fundamental.developer_score:.0f}/100)")
            elif fundamental.developer_score and fundamental.developer_score < 30:
                warnings.append(f"[FUND] Low developer activity ({fundamental.developer_score:.0f}/100)")
            
            if fundamental.community_score and fundamental.community_score > 70:
                reasons.append(f"[FUND] Active community ({fundamental.community_score:.0f}/100)")
            
            if fundamental.price_change_7d and abs(fundamental.price_change_7d) > 10:
                reasons.append(f"[FUND] Strong 7d momentum ({fundamental.price_change_7d:+.1f}%)")
            
            if fundamental.volume_24h and fundamental.market_cap:
                volume_ratio = fundamental.volume_24h / fundamental.market_cap
                if volume_ratio > 0.5:
                    reasons.append(f"[FUND] High volume/mcap ratio ({volume_ratio:.2f}) - strong activity")
                elif volume_ratio < 0.05:
                    warnings.append(f"[FUND] Low volume/mcap ratio ({volume_ratio:.2f}) - low liquidity")
        
        # 3. Hot wallet движения
        if wallet:
            wallet_score = 0
            
            if wallet.get('dominant_signal') == 'ACCUMULATION':
                wallet_score = 1.0
                net_flow = wallet.get('net_flow_usd', 0)
                acc_signals = wallet.get('accumulation_signals', 0)
                reasons.append(f"[WALLET] 🔥 Accumulation detected: ${net_flow:,.0f} net inflow ({acc_signals} signals)")
                
                if net_flow > 5_000_000:
                    reasons.append(f"[WALLET] 🐋 MASSIVE accumulation: $5M+ inflow")
                    wallet_score = 1.2
                elif net_flow > 1_000_000:
                    reasons.append(f"[WALLET] 💎 Strong accumulation: $1M+ inflow")
                    wallet_score = 1.1
            
            elif wallet.get('dominant_signal') == 'DISTRIBUTION':
                wallet_score = -1.0
                net_flow = wallet.get('net_flow_usd', 0)
                dist_signals = wallet.get('distribution_signals', 0)
                reasons.append(f"[WALLET] ⚠️ Distribution detected: ${abs(net_flow):,.0f} net outflow ({dist_signals} signals)")
                
                if abs(net_flow) > 5_000_000:
                    reasons.append(f"[WALLET] 🚨 MASSIVE distribution: $5M+ outflow")
                    wallet_score = -1.2
                elif abs(net_flow) > 1_000_000:
                    reasons.append(f"[WALLET] ⚠️ Strong distribution: $1M+ outflow")
                    wallet_score = -1.1
            
            else:
                wallet_score = 0
                if wallet.get('total_moves', 0) > 0:
                    reasons.append(f"[WALLET] Neutral flow ({wallet.get('total_moves')} movements)")
                else:
                    warnings.append(f"[WALLET] No significant wallet activity detected")
            
            signals.append(wallet_score)
            weights.append(adapted_weights['wallet'])
        else:
            warnings.append(f"[WALLET] No wallet data available")
        
        # 4. ML предсказание
        if ml:
            ml_score = self._signal_to_score(ml.prediction)
            signals.append(ml_score)
            weights.append(adapted_weights['ml'])
            
            reasons.append(f"[ML] {ml.prediction} (confidence: {ml.confidence:.1f}%)")
            
            if abs(ml.expected_change_1h) > 1:
                reasons.append(f"[ML] Short-term 1h: {ml.expected_change_1h:+.2f}%")
            
            if abs(ml.expected_change_24h) > 3:
                reasons.append(f"[ML] Medium-term 24h: {ml.expected_change_24h:+.2f}%")
            
            if abs(ml.expected_change_7d) > 10:
                reasons.append(f"[ML] Long-term 7d: {ml.expected_change_7d:+.2f}%")
            
            if ml.model_accuracy < 0.6:
                warnings.append(f"[ML] Low model accuracy ({ml.model_accuracy:.1%})")
            elif ml.model_accuracy > 0.75:
                reasons.append(f"[ML] High model accuracy ({ml.model_accuracy:.1%})")
            
            if ml.top_factors:
                top_factor = ml.top_factors[0]
                reasons.append(f"[ML] Key factor: {top_factor[0].replace('_', ' ').title()} ({top_factor[1]:.3f})")
        else:
            warnings.append(f"[ML] ML prediction unavailable")
        
        # Нормализуем веса
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        
        # Взвешенная сумма
        weighted_score = sum(s * w for s, w in zip(signals, weights))
        
        # Корректировка на основе рыночных условий
        if market_condition == 'bull_market':
            if weighted_score > 0:
                weighted_score *= 1.1
                reasons.append(f"[MARKET] Bull market conditions favor long positions")
        elif market_condition == 'bear_market':
            if weighted_score < 0:
                weighted_score *= 1.1
                reasons.append(f"[MARKET] Bear market conditions favor short positions")
        elif market_condition == 'volatile':
            warnings.append(f"[MARKET] High volatility - use tighter stops")
            if abs(weighted_score) < 0.3:
                weighted_score = 0
                warnings.append(f"[MARKET] Insufficient signal strength in volatile conditions")
        elif market_condition == 'ranging':
            if abs(weighted_score) < 0.4:
                weighted_score = 0
                reasons.append(f"[MARKET] Ranging market - waiting for clearer direction")
        
        # Конвертируем в сигнал и confidence
        if weighted_score > 0.6:
            final_signal = 'STRONG_BUY'
            confidence = min(95, 50 + weighted_score * 50)
        elif weighted_score > 0.2:
            final_signal = 'BUY'
            confidence = min(85, 50 + weighted_score * 40)
        elif weighted_score < -0.6:
            final_signal = 'STRONG_SELL'
            confidence = min(95, 50 + abs(weighted_score) * 50)
        elif weighted_score < -0.2:
            final_signal = 'SELL'
            confidence = min(85, 50 + abs(weighted_score) * 40)
        else:
            final_signal = 'HOLD'
            confidence = 50
            reasons.append("Mixed signals - recommend waiting for clearer confirmation")
        
        # Добавляем информацию о весах
        reasons.append(f"[ANALYSIS] Component weights: Tech {adapted_weights['technical']:.0%}, "
                      f"Fund {adapted_weights['fundamental']:.0%}, "
                      f"Wallet {adapted_weights['wallet']:.0%}, "
                      f"ML {adapted_weights['ml']:.0%}")
        
        return final_signal, confidence, reasons, warnings
    
    def _adapt_weights_to_market(self, market_condition: str) -> Dict[str, float]:
        """
        Адаптация весов компонентов к рыночным условиям
        
        Args:
            market_condition: Рыночные условия
        
        Returns:
            Адаптированные веса
        """
        
        base_weights = self.component_weights.copy()
        
        if market_condition == 'bull_market':
            base_weights['technical'] = 0.25
            base_weights['fundamental'] = 0.25
            base_weights['wallet'] = 0.30
            base_weights['ml'] = 0.20
        
        elif market_condition == 'bear_market':
            base_weights['technical'] = 0.35
            base_weights['fundamental'] = 0.15
            base_weights['wallet'] = 0.30
            base_weights['ml'] = 0.20
        
        elif market_condition == 'volatile':
            base_weights['technical'] = 0.40
            base_weights['fundamental'] = 0.15
            base_weights['wallet'] = 0.20
            base_weights['ml'] = 0.25
        
        elif market_condition == 'ranging':
            base_weights['technical'] = 0.35
            base_weights['fundamental'] = 0.20
            base_weights['wallet'] = 0.20
            base_weights['ml'] = 0.25
        
        return base_weights
    
    def _signal_to_score(self, signal: str) -> float:
        """Конвертация сигнала в числовой score (-1 до 1)"""
        mapping = {
            'STRONG_BUY': 1.0,
            'BUY': 0.5,
            'HOLD': 0.0,
            'SELL': -0.5,
            'STRONG_SELL': -1.0
        }
        return mapping.get(signal, 0.0)
    
    def _rating_to_score(self, rating: str) -> float:
        """Конвертация фундаментального рейтинга в score (-1 до 1)"""
        mapping = {
            'STRONG_BUY': 1.0,
            'BUY': 0.5,
            'NEUTRAL': 0.0,
            'SELL': -0.5,
            'STRONG_SELL': -1.0
        }
        return mapping.get(rating, 0.0)
    
    def _calculate_recommendations(
        self,
        asset: str,
        entry_price: float,
        signal: str,
        technical: TechnicalSignal,
        ml: Optional[MLPrediction],
        market_condition: str
    ) -> Tuple[Optional[float], Optional[float], float, str]:
        """
        Расчёт stop-loss, take-profit, размера позиции и ожидаемой длительности
        
        Stop-Loss:
        - Основан на ATR (Average True Range)
        - Учитывает уровни поддержки/сопротивления
        - Адаптируется к волатильности
        
        Take-Profit:
        - Основан на уровнях сопротивления/поддержки
        - Учитывает ML предсказания
        - Risk/Reward минимум 2:1
        
        Position Size:
        - Адаптируется к уверенности сигнала
        - Учитывает рыночные условия
        - Максимум 15% капитала
        
        Returns:
            (stop_loss, take_profit, position_size_pct, expected_duration)
        """
        
        # ATR для волатильности
        atr = technical.indicators.get('atr', entry_price * 0.02)
        
        # Уровни поддержки/сопротивления
        support = technical.support_level
        resistance = technical.resistance_level
        
        stop_loss = None
        take_profit = None
        position_size = 0.0
        expected_duration = "medium"
        
        # Мультипликатор ATR в зависимости от рыночных условий
        atr_multiplier = 2.0
        if market_condition == 'volatile':
            atr_multiplier = 2.5
        elif market_condition == 'ranging':
            atr_multiplier = 1.5
        
        if signal in ['BUY', 'STRONG_BUY']:
            # LONG позиция
            
            # Stop-Loss: чуть ниже поддержки или ATR
            stop_loss_atr = entry_price - (atr_multiplier * atr)
            stop_loss_support = support * 0.98
            
            stop_loss = max(stop_loss_atr, stop_loss_support)
            
            # Минимальный stop-loss
            min_stop_pct = 0.02
            if market_condition == 'volatile':
                min_stop_pct = 0.03
            
            min_stop_loss = entry_price * (1 - min_stop_pct)
            stop_loss = min(stop_loss, min_stop_loss)
            
            # Максимальный stop-loss
            max_stop_pct = 0.05
            if market_condition == 'volatile':
                max_stop_pct = 0.07
            
            max_stop_loss = entry_price * (1 - max_stop_pct)
            stop_loss = max(stop_loss, max_stop_loss)
            
            # Take-Profit
            take_profit_resistance = resistance * 0.98
            
            if ml and ml.expected_change_24h > 0:
                ml_target_24h = entry_price * (1 + ml.expected_change_24h / 100)
                
                ml_range = ml.change_24h_range
                if ml_range:
                    conservative_target = (ml_target_24h + entry_price * (1 + ml_range[0] / 100)) / 2
                    take_profit = min(take_profit_resistance, conservative_target)
                else:
                    take_profit = min(take_profit_resistance, ml_target_24h)
                
                # Если есть 7d прогноз и он сильно отличается
                if ml.expected_change_7d > ml.expected_change_24h * 2:
                    expected_duration = "long"
                    ml_target_7d = entry_price * (1 + ml.expected_change_7d / 100)
                    take_profit = (take_profit + ml_target_7d) / 2
            else:
                take_profit = take_profit_resistance
            
            # Проверяем Risk/Reward ratio
            min_rr = 2.0
            if market_condition == 'volatile':
                min_rr = 2.5
            elif signal == 'STRONG_BUY':
                min_rr = 1.8
            
            risk = entry_price - stop_loss
            reward = take_profit - entry_price
            
            if reward < risk * min_rr:
                take_profit = entry_price + (risk * min_rr)
            
            # Position size
            base_size = 10.0 if signal == 'STRONG_BUY' else 5.0
            
            if market_condition == 'volatile':
                base_size *= 0.7
            elif market_condition == 'bull_market':
                base_size *= 1.2
            
            position_size = min(15.0, base_size)
            
            # Expected duration
            if ml and abs(ml.expected_change_1h) > abs(ml.expected_change_24h) * 0.5:
                expected_duration = "short"
            elif ml and abs(ml.expected_change_7d) > abs(ml.expected_change_24h) * 3:
                expected_duration = "long"
        
        elif signal in ['SELL', 'STRONG_SELL']:
            # SHORT позиция
            
            # Stop-Loss: чуть выше сопротивления или ATR
            stop_loss_atr = entry_price + (atr_multiplier * atr)
            stop_loss_resistance = resistance * 1.02
            
            stop_loss = min(stop_loss_atr, stop_loss_resistance)
            
            # Максимальный stop-loss
            max_stop_pct = 0.02
            if market_condition == 'volatile':
                max_stop_pct = 0.03
            
            max_stop_loss = entry_price * (1 + max_stop_pct)
            stop_loss = max(stop_loss, max_stop_loss)
            
            # Минимальный stop-loss
            min_stop_pct = 0.05
            if market_condition == 'volatile':
                min_stop_pct = 0.07
            
            min_stop_loss = entry_price * (1 + min_stop_pct)
            stop_loss = min(stop_loss, min_stop_loss)
            
            # Take-Profit
            take_profit_support = support * 1.02
            
            if ml and ml.expected_change_24h < 0:
                ml_target_24h = entry_price * (1 + ml.expected_change_24h / 100)
                
                ml_range = ml.change_24h_range
                if ml_range:
                    conservative_target = (ml_target_24h + entry_price * (1 + ml_range[1] / 100)) / 2
                    take_profit = max(take_profit_support, conservative_target)
                else:
                    take_profit = max(take_profit_support, ml_target_24h)
                
                if ml.expected_change_7d < ml.expected_change_24h * 2:
                    expected_duration = "long"
                    ml_target_7d = entry_price * (1 + ml.expected_change_7d / 100)
                    take_profit = (take_profit + ml_target_7d) / 2
            else:
                take_profit = take_profit_support
            
            # Проверяем Risk/Reward ratio
            min_rr = 2.0
            if market_condition == 'volatile':
                min_rr = 2.5
            elif signal == 'STRONG_SELL':
                min_rr = 1.8
            
            risk = stop_loss - entry_price
            reward = entry_price - take_profit
            
            if reward < risk * min_rr:
                take_profit = entry_price - (risk * min_rr)
            
            # Position size
            base_size = 10.0 if signal == 'STRONG_SELL' else 5.0
            
            if market_condition == 'volatile':
                base_size *= 0.7
            elif market_condition == 'bear_market':
                base_size *= 1.2
            
            position_size = min(15.0, base_size)
            
            # Expected duration
            if ml and abs(ml.expected_change_1h) > abs(ml.expected_change_24h) * 0.5:
                expected_duration = "short"
            elif ml and abs(ml.expected_change_7d) > abs(ml.expected_change_24h) * 3:
                expected_duration = "long"
        
        else:
            # HOLD - не открываем позицию
            stop_loss = None
            take_profit = None
            position_size = 0.0
            expected_duration = "none"
        
        return stop_loss, take_profit, position_size, expected_duration
    
    def _validate_signal(self, signal: TradingSignal) -> List[str]:
        """
        Финальная валидация сигнала
        
        Returns:
            Список дополнительных предупреждений
        """
        
        warnings = []
        
        # Проверка 1: Risk/Reward слишком низкий
        if signal.risk_reward_ratio > 0 and signal.risk_reward_ratio < 1.5:
            warnings.append(f"[VALIDATION] Low R/R ratio ({signal.risk_reward_ratio:.2f}) - consider skipping")
        
        # Проверка 2: Слишком много предупреждений
        if len(signal.warnings) >= 5:
            warnings.append(f"[VALIDATION] Multiple warnings detected ({len(signal.warnings)}) - high risk signal")
        
        # Проверка 3: Недостаточно причин для сильного сигнала
        if signal.signal in ['STRONG_BUY', 'STRONG_SELL'] and len(signal.reasons) < 5:
            warnings.append(f"[VALIDATION] Strong signal with limited supporting factors")
        
        # Проверка 4: Противоречия между компонентами
        components_signals = []
        if signal.technical:
            components_signals.append(self._signal_to_score(signal.technical.signal_type))
        if signal.ml:
            components_signals.append(self._signal_to_score(signal.ml.prediction))
        
        if len(components_signals) >= 2:
            if max(components_signals) - min(components_signals) > 1.5:
                warnings.append(f"[VALIDATION] Conflicting signals between components")
        
        # Проверка 5: Размер позиции vs уверенность
        if signal.position_size_pct > 10 and signal.confidence < 70:
            warnings.append(f"[VALIDATION] Large position size with moderate confidence")
        
        # Проверка 6: Экстремальные рыночные условия
        if signal.market_condition == 'volatile' and signal.position_size_pct > 7:
            warnings.append(f"[VALIDATION] Consider reducing position size in volatile market")
        
        return warnings
    
    def _get_from_cache(self, asset: str) -> Optional[TradingSignal]:
        """Получить сигнал из кэша"""
        cache_key = f"{asset}_{datetime.utcnow().strftime('%Y%m%d%H%M')}"
        
        if cache_key in self.signal_cache:
            signal, cached_at = self.signal_cache[cache_key]
            age_minutes = (datetime.utcnow() - cached_at).seconds / 60
            
            if age_minutes < self.cache_ttl_minutes:
                return signal
        
        return None
    
    def _add_to_cache(self, asset: str, signal: TradingSignal):
        """Добавить сигнал в кэш"""
        cache_key = f"{asset}_{datetime.utcnow().strftime('%Y%m%d%H%M')}"
        self.signal_cache[cache_key] = (signal, datetime.utcnow())
        
        # Очистка старых записей
        if len(self.signal_cache) > 100:
            oldest_keys = sorted(
                self.signal_cache.keys(),
                key=lambda k: self.signal_cache[k][1]
            )[:50]
            
            for key in oldest_keys:
                del self.signal_cache[key]
    
    def _add_to_history(self, signal: TradingSignal):
        """Добавить сигнал в историю"""
        self.signal_history.append(signal)
        
        if len(self.signal_history) > self.max_history_size:
            self.signal_history = self.signal_history[-self.max_history_size:]
    
    def get_signal_history(
        self,
        asset: Optional[str] = None,
        hours: int = 24,
        min_confidence: float = 0.0
    ) -> List[TradingSignal]:
        """
        Получить историю сигналов с фильтрацией
        
        Args:
            asset: Фильтр по активу (опционально)
            hours: Период в часах
            min_confidence: Минимальная уверенность
        
        Returns:
            Список TradingSignal
        """
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        filtered = [
            s for s in self.signal_history
            if s.timestamp >= cutoff and s.confidence >= min_confidence
        ]
        
        if asset:
            filtered = [s for s in filtered if s.asset == asset]
        
        return filtered
    
    def get_stats(self) -> Dict:
        """Получить статистику генератора"""
        return {
            **self.stats,
            'cache_size': len(self.signal_cache),
            'history_size': len(self.signal_history),
            'cache_hit_rate': (
                self.stats['cache_hits'] / 
                (self.stats['cache_hits'] + self.stats['cache_misses'])
                if (self.stats['cache_hits'] + self.stats['cache_misses']) > 0 else 0
            )
        }
    
    def update_component_weights(self, new_weights: Dict[str, float]):
        """
        Обновить веса компонентов
        
        Args:
            new_weights: {'technical': 0.3, 'fundamental': 0.2, ...}
        """
        
        total = sum(new_weights.values())
        if abs(total - 1.0) > 0.01:
            logger.warning(f"⚠️ Веса не суммируются в 1.0 (сумма: {total}), нормализация...")
            new_weights = {k: v/total for k, v in new_weights.items()}
        
        self.component_weights.update(new_weights)
        logger.info(f"✅ Веса компонентов обновлены: {self.component_weights}")
    
    def format_signal_message(self, signal: TradingSignal) -> str:
        """
        Форматирование сигнала для Telegram
        
        Включает все компоненты анализа и disclaimer
        """
        
        # Эмодзи для сигналов
        signal_emoji = {
            'STRONG_BUY': '🟢🔥',
            'BUY': '🟢',
            'HOLD': '⚪',
            'SELL': '🔴',
            'STRONG_SELL': '🔴🔥'
        }
        
        emoji = signal_emoji.get(signal.signal, '⚪')
        
        # Заголовок
        message = f"""
{emoji} <b>TRADING SIGNAL: {signal.asset}</b>

<b>📊 OVERALL SIGNAL: {signal.signal}</b>
<b>Confidence:</b> {signal.confidence:.1f}%
<b>Priority Score:</b> {signal.get_priority_score():.1f}/100
<b>Entry Price:</b> ${signal.entry_price:,.2f}
<b>Market Condition:</b> {signal.market_condition.replace('_', ' ').title()}
<b>Timestamp:</b> {signal.timestamp.strftime('%Y-%m-%d %H:%M UTC')}

"""
        
        # Рекомендации
        if signal.stop_loss or signal.take_profit or signal.position_size_pct > 0:
            message += "<b>💡 TRADE RECOMMENDATIONS:</b>\n"
            
            if signal.stop_loss:
                message += f"<b>Stop-Loss:</b> ${signal.stop_loss:,.2f} (-{signal.risk_score:.2f}%)\n"
            
            if signal.take_profit:
                message += f"<b>Take-Profit:</b> ${signal.take_profit:,.2f} (+{signal.reward_score:.2f}%)\n"
            
            if signal.position_size_pct > 0:
                message += f"<b>Position Size:</b> {signal.position_size_pct:.1f}% of capital\n"
            
            # Risk/Reward
            if signal.risk_reward_ratio > 0:
                message += f"<b>Risk/Reward Ratio:</b> 1:{signal.risk_reward_ratio:.2f}\n"
            
            message += f"<b>Expected Duration:</b> {signal.expected_duration.title()}\n"
            message += f"<b>Tradeable:</b> {'✅ Yes' if signal.is_tradeable() else '❌ No'}\n"
            
            message += "\n"
        
        # Технический анализ
        if signal.technical:
            t = signal.technical
            message += f"""<b>📈 TECHNICAL ANALYSIS:</b>
<b>Signal:</b> {t.signal_type} (Strength: {t.strength:.1f}/100)
<b>Trend:</b> {t.trend.replace('_', ' ').title()}
<b>Volume Trend:</b> {t.volume_trend.title()}

<b>Key Indicators:</b>
- RSI: {t.rsi:.1f} ({self._rsi_interpretation(t.rsi)})
- MACD: {t.macd_signal.title()}
- Bollinger Bands: {t.bollinger_position.title()}

<b>Support/Resistance:</b>
- Support: ${t.support_level:,.2f}
- Resistance: ${t.resistance_level:,.2f}

"""
        
        # ML предсказание
        if signal.ml:
            ml = signal.ml
            message += f"""<b>🤖 ML PREDICTION:</b>
<b>Direction:</b> {ml.prediction} (Confidence: {ml.confidence:.1f}%)

<b>Expected Price Changes:</b>
- 1 Hour: {ml.expected_change_1h:+.2f}% (range: {ml.change_1h_range[0]:+.2f}% to {ml.change_1h_range[1]:+.2f}%)
- 4 Hours: {ml.expected_change_4h:+.2f}% (range: {ml.change_4h_range[0]:+.2f}% to {ml.change_4h_range[1]:+.2f}%)
- 24 Hours: {ml.expected_change_24h:+.2f}% (range: {ml.change_24h_range[0]:+.2f}% to {ml.change_24h_range[1]:+.2f}%)
- 7 Days: {ml.expected_change_7d:+.2f}% (range: {ml.change_7d_range[0]:+.2f}% to {ml.change_7d_range[1]:+.2f}%)

<b>Model Performance:</b>
- Classification Accuracy: {ml.model_accuracy:.1%}
- MAE 1h: {ml.model_mae_1h:.3f}%
- MAE 24h: {ml.model_mae_24h:.3f}%

"""
            
            # Топ факторы влияния
            if ml.top_factors:
                message += "<b>Top Factors:</b>\n"
                for i, (factor, importance) in enumerate(ml.top_factors[:3], 1):
                    message += f"{i}. {factor.replace('_', ' ').title()}: {importance:.3f}\n"
                message += "\n"
        
        # Фундаментальный анализ
        if signal.fundamental:
            f = signal.fundamental
            message += f"""<b>📊 FUNDAMENTAL ANALYSIS:</b>
<b>Rating:</b> {f.rating}
<b>Fundamental Score:</b> {f.fundamental_score:.1f}/100
"""
            
            if f.market_cap_rank:
                message += f"<b>Market Cap Rank:</b> #{f.market_cap_rank}\n"
            
            if f.market_cap:
                if f.market_cap >= 1e9:
                    message += f"<b>Market Cap:</b> ${f.market_cap/1e9:.2f}B\n"
                else:
                    message += f"<b>Market Cap:</b> ${f.market_cap/1e6:.1f}M\n"
            
            if f.volume_24h:
                if f.volume_24h >= 1e9:
                    message += f"<b>24h Volume:</b> ${f.volume_24h/1e9:.2f}B\n"
                else:
                    message += f"<b>24h Volume:</b> ${f.volume_24h/1e6:.1f}M\n"
            
            if f.price_change_24h is not None:
                message += f"<b>24h Change:</b> {f.price_change_24h:+.2f}%\n"
            
            if f.price_change_7d is not None:
                message += f"<b>7d Change:</b> {f.price_change_7d:+.2f}%\n"
            
            # Developer & Community scores
            if f.developer_score or f.community_score:
                message += "\n<b>Activity Scores:</b>\n"
                if f.developer_score:
                    message += f"• Developer: {f.developer_score:.0f}/100\n"
                if f.community_score:
                    message += f"• Community: {f.community_score:.0f}/100\n"
            
            message += "\n"
        
        # Hot wallet движения
        if signal.wallet:
            w = signal.wallet
            message += f"""<b>🔥 HOT WALLET ACTIVITY:</b>
<b>Dominant Signal:</b> {w['dominant_signal']}
<b>Confidence:</b> {w['confidence']:.1f}%
<b>Net Flow (6h):</b> ${w['net_flow_usd']:,.0f}

<b>Movement Details:</b>
- Total Movements: {w['total_moves']}
- Inflows: ${w['inflow_usd']:,.0f}
- Outflows: ${w['outflow_usd']:,.0f}
- Accumulation Signals: {w['accumulation_signals']}
- Distribution Signals: {w['distribution_signals']}

"""
        
        # Ключевые причины
        if signal.reasons:
            message += "<b>📝 KEY ANALYSIS POINTS:</b>\n"
            for i, reason in enumerate(signal.reasons[:10], 1):
                message += f"{i}. {reason}\n"
            message += "\n"
        
        # Предупреждения
        if signal.warnings:
            message += "<b>⚠️ WARNINGS & CONSIDERATIONS:</b>\n"
            for i, warning in enumerate(signal.warnings[:7], 1):
                message += f"{i}. {warning}\n"
            message += "\n"
        
        # Разделитель
        message += "─" * 40 + "\n\n"
        
        # КРИТИЧЕСКИЙ ДИСКЛЕЙМЕР
        message += """<b>⚠️ IMPORTANT DISCLAIMER:</b>

<b>This is NOT financial advice.</b>

This signal is generated by an automated AI system for <b>informational and educational purposes only</b>. This is not a recommendation to buy, sell, or hold any cryptocurrency or financial instrument.

<b>Key Points:</b>
- Trading cryptocurrencies involves substantial risk
- You may lose all invested capital
- Past performance does not guarantee future results
- Always conduct your own research (DYOR)
- Consult with a licensed financial advisor before investing
- Never invest more than you can afford to lose

<b>No Guarantee:</b> The accuracy of predictions and analysis cannot be guaranteed. Markets are unpredictable and subject to rapid changes.

<b>By using this information, you acknowledge these risks and agree that you alone are responsible for your investment decisions.</b>

Signal ID: {signal.signal_id}
"""
        
        return message
    
    def _rsi_interpretation(self, rsi: float) -> str:
        """Интерпретация RSI"""
        if rsi < 20:
            return "Extremely Oversold 🔥"
        elif rsi < 30:
            return "Oversold"
        elif rsi < 40:
            return "Slightly Oversold"
        elif rsi < 60:
            return "Neutral"
        elif rsi < 70:
            return "Slightly Overbought"
        elif rsi < 80:
            return "Overbought"
        else:
            return "Extremely Overbought 🔥"
    
    def clear_cache(self):
        """Очистить кэш"""
        self.signal_cache.clear()
        self.price_cache.clear()
        logger.info("🧹 Кэш очищен")
    
    def clear_history(self):
        """Очистить историю"""
        self.signal_history.clear()
        logger.info("🧹 История очищена")
    
    def reset_stats(self):
        """Сбросить статистику"""
        self.stats = {
            'total_signals_generated': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0,
            'last_signal_at': None
        }
        logger.info("🔄 Статистика сброшена")