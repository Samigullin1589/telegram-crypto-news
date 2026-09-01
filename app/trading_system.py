# app/trading_system.py
"""
Trading System Facade v5.0
Унифицированный интерфейс для Trading System с улучшенной архитектурой
"""

import asyncio
import html
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List

import aiohttp
import pandas as pd
import telegram

from app.config import config

logger = logging.getLogger(__name__)


class TradingSystem:
    """
    Фасад для Trading System
    
    Улучшения v5.0:
    - Использует app.config вместо app.settings
    - Модульная архитектура
    - Улучшенная обработка ошибок
    - Безопасная инициализация
    """
    
    def __init__(self):
        """Инициализация Trading System"""
        
        # Проверка включен ли trading в конфигурации
        self.enabled = config.is_feature_enabled('trading')
        
        # Получение конфигурации
        self.trading_config = config.features.get_trading_config()
        self.dry_run = self.trading_config.get('dry_run', True)
        
        # Компоненты
        self.signal_generator = None
        self.positions = None
        self.performance = None
        self._initialized = False
        self._published_at: Dict[str, datetime] = {}
        self._daily_publications: List[datetime] = []
        
        # Попытка инициализации компонентов
        if self.enabled:
            self._initialize_components()
        else:
            logger.info("📈 [TRADING] Trading System disabled in configuration")
            self._log_disabled_status()
    
    def _initialize_components(self):
        """Инициализация компонентов Trading System"""
        try:
            # Импорт модулей trading
            from app.trading.signal_generator import SignalGenerator
            from app.trading.position_tracker import PositionTracker
            from app.trading.performance_stats import PerformanceStats
            
            # Получение CoinGecko API key
            coingecko_key = getattr(config.api, 'coingecko_api_key', None)
            
            # Инициализация компонентов
            self.signal_generator = SignalGenerator(coingecko_key=coingecko_key)
            self.positions = self.signal_generator.positions
            self.performance = self.signal_generator.performance
            
            self._initialized = True
            
            self._log_initialization_success()
        
        except ImportError as e:
            logger.warning(f"⚠️  [TRADING] Trading modules not available: {e}")
            self.enabled = False
            self._log_modules_unavailable()
        
        except Exception as e:
            logger.error(f"❌ [TRADING] Initialization error: {e}", exc_info=True)
            self.enabled = False
    
    def _log_initialization_success(self):
        """Логирование успешной инициализации"""
        logger.info("\n" + "="*80)
        logger.info("📈 TRADING SYSTEM v5.0 - INITIALIZED")
        logger.info("="*80)
        logger.info(f"Status: ✅ ENABLED")
        logger.info(f"Mode: {'🧪 DRY RUN' if self.dry_run else '💰 LIVE'}")
        logger.info(f"Min Confidence: {self.trading_config.get('min_confidence', 75)}/100")
        logger.info(f"Max Signals/Day: {self.trading_config.get('max_signals_per_day', 10)}")
        logger.info(f"Max Open Positions: {self.trading_config.get('max_open_positions', 5)}")
        logger.info(f"Stop Loss: {self.trading_config.get('default_stop_loss', 3.0)}%")
        logger.info(f"Take Profit: {self.trading_config.get('default_take_profit', 5.0)}%")
        logger.info("="*80 + "\n")
    
    def _log_disabled_status(self):
        """Логирование отключенного статуса"""
        logger.info("\n" + "="*80)
        logger.info("📈 TRADING SYSTEM v5.0")
        logger.info("="*80)
        logger.info("Status: ❌ DISABLED")
        logger.info("Reason: TRADING_ENABLED=false in configuration")
        logger.info("="*80 + "\n")
    
    def _log_modules_unavailable(self):
        """Логирование недоступности модулей"""
        logger.info("\n" + "="*80)
        logger.info("📈 TRADING SYSTEM v5.0")
        logger.info("="*80)
        logger.info("Status: ❌ DISABLED")
        logger.info("Reason: Trading modules not available")
        logger.info("="*80 + "\n")
    
    def is_enabled(self) -> bool:
        """
        Проверка включен ли Trading System
        
        Returns:
            True если система включена и инициализирована
        """
        return self.enabled and self._initialized and self.signal_generator is not None
    
    async def generate_signal(
        self,
        symbol: str,
        price_data: Any,
        session: Any
    ) -> Optional[Any]:
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
            logger.debug(f"[TRADING] System not enabled, skipping signal for {symbol}")
            return None

        try:
            return await self.signal_generator.generate_signal(
                asset=symbol,
                price_data=price_data,
                session=session,
            )
        except Exception:
            logger.exception(
                "❌ [TRADING] Ошибка генерации сигнала для %s",
                symbol,
            )
            return None

    async def run_signal_cycle(self) -> Dict[str, Any]:
        """Получить рыночные данные, сгенерировать и опубликовать сигналы."""
        result = {
            'success': False,
            'assets_checked': 0,
            'signals_generated': 0,
            'signals_actionable': 0,
            'signals_filtered': 0,
            'filter_reasons': {},
            'signals_sent': 0,
            'errors': 0,
        }
        if not self.is_enabled():
            result['reason'] = 'disabled'
            return result

        assets = self.trading_config.get('monitored_assets') or ['BTC', 'ETH']
        logger.info(
            "📈 [TRADING] Запуск сигнального цикла для %d активов",
            len(assets),
        )

        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for asset in assets:
                result['assets_checked'] += 1
                try:
                    price_data = await self._fetch_ohlcv(asset, session)
                    if price_data is None or len(price_data) < 50:
                        logger.warning(
                            "⚠️ [TRADING] Недостаточно OHLCV данных для %s",
                            asset,
                        )
                        continue

                    signal = await asyncio.wait_for(
                        self.generate_signal(asset, price_data, session),
                        timeout=max(
                            5,
                            int(self.trading_config.get('asset_timeout', 45)),
                        ),
                    )
                    if signal is None:
                        result['errors'] += 1
                        logger.error(
                            "❌ [TRADING] Генератор не вернул сигнал для %s",
                            asset,
                        )
                        continue

                    result['signals_generated'] += 1
                    filter_reason = self._signal_publication_block_reason(signal)
                    if filter_reason:
                        result['signals_filtered'] += 1
                        result['filter_reasons'][filter_reason] = (
                            result['filter_reasons'].get(filter_reason, 0) + 1
                        )
                        logger.info(
                            "⏸️ [TRADING] %s: %s, confidence=%.1f — фильтр=%s",
                            asset,
                            getattr(signal, 'signal', 'UNKNOWN'),
                            float(getattr(signal, 'confidence', 0)),
                            filter_reason,
                        )
                        continue

                    result['signals_actionable'] += 1
                    if await self._publish_signal(signal):
                        self._record_publication(signal)
                        result['signals_sent'] += 1
                    else:
                        result['errors'] += 1
                except asyncio.TimeoutError:
                    result['errors'] += 1
                    logger.error(
                        "❌ [TRADING] Анализ %s превысил допустимое время",
                        asset,
                    )
                except Exception:
                    result['errors'] += 1
                    logger.exception("❌ [TRADING] Ошибка обработки %s", asset)

        result['success'] = result['errors'] < result['assets_checked']
        logger.info(
            "✅ [TRADING] Цикл завершён: проверено=%d, проанализировано=%d, готово=%d, отфильтровано=%d, опубликовано=%d, ошибок=%d",
            result['assets_checked'],
            result['signals_generated'],
            result['signals_actionable'],
            result['signals_filtered'],
            result['signals_sent'],
            result['errors'],
        )
        return result

    async def _fetch_ohlcv(
        self,
        asset: str,
        session: aiohttp.ClientSession,
    ) -> Optional[pd.DataFrame]:
        """Загрузить последние часовые свечи Binance."""
        params = {
            'symbol': f'{asset.upper()}USDT',
            'interval': '1h',
            'limit': 200,
        }
        async with session.get(
            'https://api.binance.com/api/v3/klines',
            params=params,
        ) as response:
            if response.status != 200:
                logger.warning(
                    "⚠️ [TRADING] Binance OHLCV для %s вернул HTTP %s",
                    asset,
                    response.status,
                )
                return None

            data = await response.json()
            if not isinstance(data, list) or not data:
                return None

        frame = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore',
        ])
        frame['timestamp'] = pd.to_datetime(frame['timestamp'], unit='ms', utc=True)
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        frame[numeric_columns] = frame[numeric_columns].apply(
            pd.to_numeric,
            errors='coerce',
        )
        frame = frame.dropna(subset=numeric_columns)
        return frame[['timestamp', *numeric_columns]]

    def _signal_publication_block_reason(self, signal: Any) -> Optional[str]:
        direction = getattr(signal, 'signal', '')
        if direction not in {'STRONG_BUY', 'BUY', 'SELL', 'STRONG_SELL'}:
            return 'non_actionable_direction'

        min_confidence = float(self.trading_config.get('min_confidence', 75))
        if float(getattr(signal, 'confidence', 0)) < min_confidence:
            return 'low_confidence'

        if hasattr(signal, 'is_tradeable') and not signal.is_tradeable():
            return 'not_tradeable'

        now = datetime.now(timezone.utc)
        self._daily_publications = [
            published for published in self._daily_publications
            if published.date() == now.date()
        ]
        max_per_day = int(self.trading_config.get('max_signals_per_day', 10))
        if len(self._daily_publications) >= max_per_day:
            return 'daily_limit'

        hour_ago = now - timedelta(hours=1)
        max_per_hour = int(self.trading_config.get('max_signals_per_hour', 5))
        if sum(published >= hour_ago for published in self._daily_publications) >= max_per_hour:
            return 'hourly_limit'

        asset = str(getattr(signal, 'asset', '')).upper()
        last_published = self._published_at.get(asset)
        cooldown = timedelta(
            hours=float(self.trading_config.get('signal_interval_hours', 1.0))
        )
        if last_published is not None and now - last_published < cooldown:
            return 'asset_cooldown'
        return None

    def _should_publish_signal(self, signal: Any) -> bool:
        return self._signal_publication_block_reason(signal) is None

    def _record_publication(self, signal: Any) -> None:
        published_at = datetime.now(timezone.utc)
        asset = str(getattr(signal, 'asset', '')).upper()
        self._published_at[asset] = published_at
        self._daily_publications.append(published_at)

    async def _publish_signal(self, signal: Any) -> bool:
        """Опубликовать информационный сигнал и подтвердить ответ Telegram."""
        message = self.format_signal_for_telegram(signal)
        if not message:
            return False

        try:
            async with telegram.Bot(token=config.telegram.bot_token) as bot:
                await bot.send_message(
                    chat_id=config.telegram.channel_id,
                    text=message,
                    parse_mode='HTML',
                    disable_web_page_preview=True,
                )
            logger.info(
                "✅ [TRADING] Сигнал опубликован: %s — %s",
                getattr(signal, 'asset', 'UNKNOWN'),
                getattr(signal, 'signal', 'UNKNOWN'),
            )
            return True
        except Exception:
            logger.exception(
                "❌ [TRADING] Telegram не принял сигнал %s",
                getattr(signal, 'asset', 'UNKNOWN'),
            )
            return False
        
        try:
            # Генерация сигнала
            signal = await self.signal_generator.generate_signal(
                asset=symbol,
                price_data=price_data,
                session=session
            )
            
            if not signal:
                return None
            
            # Фильтрация по confidence
            min_confidence = self.trading_config.get('min_confidence', 75)
            if signal.confidence < min_confidence:
                logger.debug(
                    f"[TRADING] Signal {symbol} filtered: "
                    f"confidence {signal.confidence:.1f} < {min_confidence}"
                )
                return None
            
            # Конвертация в dict
            return signal.to_dict()
        
        except Exception as e:
            logger.error(f"❌ [TRADING] Error generating signal for {symbol}: {e}")
            return None
    
    async def get_open_positions(self) -> List[Dict[str, Any]]:
        """
        Получение открытых позиций
        
        Returns:
            Список открытых позиций
        """
        if not self.is_enabled() or not self.positions:
            return []
        
        try:
            open_pos = self.positions.get_open_positions()
            return [pos.to_dict() for pos in open_pos]
        except Exception as e:
            logger.error(f"❌ [TRADING] Error getting positions: {e}")
            return []
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """
        Получение статистики производительности
        
        Returns:
            Dict со статистикой
        """
        if not self.is_enabled() or not self.performance:
            return {
                'total_signals': 0,
                'total_trades': 0,
                'win_rate': 0.0,
                'avg_profit': 0.0,
                'total_pnl': 0.0
            }
        
        try:
            metrics = await self.performance.calculate_metrics()
            return {
                'total_signals': 0,
                'total_trades': metrics.total_trades,
                'win_rate': metrics.win_rate,
                'avg_profit': metrics.avg_pnl_per_trade_pct,
                'total_pnl': metrics.total_pnl_usd
            }
        except Exception as e:
            logger.error(f"❌ [TRADING] Error getting stats: {e}")
            return {
                'total_signals': 0,
                'total_trades': 0,
                'win_rate': 0.0,
                'avg_profit': 0.0,
                'total_pnl': 0.0
            }
    
    async def update_positions(self, price_provider: Any = None) -> List[Dict[str, Any]]:
        """
        Обновление позиций (проверка SL/TP)
        
        Args:
            price_provider: Provider для получения текущих цен
            
        Returns:
            Список закрытых позиций
        """
        if not self.is_enabled() or not self.positions:
            return []
        
        try:
            closed = []
            open_positions = self.positions.get_open_positions()
            
            for position in open_positions:
                # Получение текущей цены
                if price_provider and hasattr(price_provider, 'get_price'):
                    try:
                        current_price = await price_provider.get_price(position.asset)
                        
                        # Обновление позиции
                        updated = self.positions.update_position(
                            position.id,
                            current_price
                        )
                        
                        # Проверка закрытия
                        if updated and updated.status != 'OPEN':
                            closed.append(updated.to_dict())
                    
                    except Exception as e:
                        logger.warning(
                            f"⚠️  [TRADING] Error updating position {position.asset}: {e}"
                        )
            
            return closed
        
        except Exception as e:
            logger.error(f"❌ [TRADING] Error updating positions: {e}")
            return []
    
    def format_signal_for_telegram(self, signal: Any) -> str:
        """
        Форматирование сигнала для Telegram
        
        Args:
            signal: Signal dict
            
        Returns:
            Formatted message (HTML)
        """
        if not self.is_enabled():
            return ""
        
        try:
            value = lambda name, default=None: (
                signal.get(name, default)
                if isinstance(signal, dict)
                else getattr(signal, name, default)
            )
            direction = value('signal', '')
            labels = {
                'STRONG_BUY': ('🟢🔥', 'СИЛЬНАЯ ПОКУПКА'),
                'BUY': ('🟢', 'ПОКУПКА'),
                'SELL': ('🔴', 'ПРОДАЖА'),
                'STRONG_SELL': ('🔴🔥', 'СИЛЬНАЯ ПРОДАЖА'),
            }
            emoji, label = labels.get(direction, ('⚪', 'НАБЛЮДЕНИЕ'))
            asset = html.escape(str(value('asset', 'UNKNOWN')))
            confidence = float(value('confidence', 0))
            entry_price = float(value('entry_price', 0))
            stop_loss = value('stop_loss')
            take_profit = value('take_profit')
            risk_reward = float(value('risk_reward_ratio', 0))
            reasons = [
                str(reason)
                for reason in (value('reasons', []) or [])
                if re.search(r'[А-Яа-яЁё]', str(reason))
            ][:3]
            if not reasons:
                reasons = [
                    'Сигнал подтверждён совокупностью доступных рыночных индикаторов.'
                ]

            lines = [
                f"{emoji} <b>Торговый сигнал: {asset}</b>",
                '',
                f"<b>Направление:</b> {label}",
                f"<b>Уверенность:</b> {confidence:.1f}%",
                f"<b>Цена входа:</b> ${entry_price:,.4f}",
            ]
            if stop_loss:
                lines.append(f"<b>Стоп-лосс:</b> ${float(stop_loss):,.4f}")
            if take_profit:
                lines.append(f"<b>Тейк-профит:</b> ${float(take_profit):,.4f}")
            if risk_reward:
                lines.append(f"<b>Риск/прибыль:</b> 1:{risk_reward:.2f}")
            if reasons:
                lines.extend(['', '<b>Ключевые факторы:</b>'])
                lines.extend(
                    f"• {html.escape(str(reason))}"
                    for reason in reasons
                )
            lines.extend([
                '',
                '⚠️ Не является индивидуальной инвестиционной рекомендацией.',
                '#крипто #трейдинг',
            ])
            return '\n'.join(lines)
        except Exception:
            logger.exception("❌ [TRADING] Ошибка форматирования сигнала")
            return ""
    
    def get_config(self) -> Dict[str, Any]:
        """
        Получение текущей конфигурации
        
        Returns:
            Dict с конфигурацией
        """
        return {
            'enabled': self.enabled,
            'initialized': self._initialized,
            **self.trading_config
        }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение статуса системы
        
        Returns:
            Dict со статусом
        """
        return {
            'enabled': self.enabled,
            'initialized': self._initialized,
            'dry_run': self.dry_run,
            'has_signal_generator': self.signal_generator is not None,
            'has_positions': self.positions is not None,
            'has_performance': self.performance is not None
        }
    
    async def cleanup(self):
        """Очистка ресурсов"""
        logger.info("🧹 [TRADING] Cleanup...")
        
        try:
            if self.signal_generator and hasattr(self.signal_generator, 'cleanup'):
                await self.signal_generator.cleanup()
            
            self._initialized = False
            logger.info("✅ [TRADING] Cleanup completed")
        
        except Exception as e:
            logger.error(f"⚠️  [TRADING] Cleanup error: {e}")


__all__ = ['TradingSystem']