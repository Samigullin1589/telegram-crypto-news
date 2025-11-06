# app/scheduler/trading.py
"""
Trading System Integration
Signal generation and position management
"""

import asyncio
import aiohttp
import logging
import pandas as pd
from datetime import datetime
from typing import Optional, Dict

from app.config import config

logger = logging.getLogger(__name__)

try:
    from app.trading.signal_generator import SignalGenerator
    TRADING_AVAILABLE = True
except ImportError:
    TRADING_AVAILABLE = False
    logger.warning("⚠️ Trading System not available")


class TradingSystem:
    """Торговая система с генерацией сигналов и управлением позициями"""
    
    def __init__(self, components: Dict):
        self.enabled = False
        self.signal_generator = None
        
        if not TRADING_AVAILABLE or not config.is_feature_enabled('trading'):
            logger.info("📈 [TRADING] Disabled")
            return
        
        try:
            coingecko_key = config.get_api_key('coingecko')
            self.signal_generator = SignalGenerator(coingecko_key)
            self.enabled = True
            logger.info("📈 [TRADING] Система активна")
        except Exception as e:
            logger.error(f"❌ [TRADING] Ошибка инициализации: {e}")
    
    async def run_signal_cycle(self) -> Dict:
        """Генерация торговых сигналов"""
        if not self.enabled:
            return {'success': False, 'reason': 'disabled'}
        
        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"📈 [TRADING] Генерация сигналов: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
            logger.info(f"{'='*80}")
            
            signals_generated = 0
            signals_sent = 0
            
            monitored_assets = config.trading.monitored_assets
            
            async with aiohttp.ClientSession() as session:
                for asset in monitored_assets:
                    try:
                        logger.info(f"\n🔍 [TRADING] Анализ {asset}...")
                        
                        price_data = await self._fetch_ohlcv(asset, session)
                        
                        if price_data is None or len(price_data) < 50:
                            logger.warning(f"   ⚠️ Недостаточно данных для {asset}")
                            continue
                        
                        signal = await self.signal_generator.generate_signal(
                            asset=asset,
                            price_data=price_data,
                            session=session
                        )
                        
                        if not signal:
                            logger.warning(f"   ⚠️ Не удалось сгенерировать сигнал для {asset}")
                            continue
                        
                        signals_generated += 1
                        
                        if signal.signal in ['STRONG_BUY', 'BUY', 'STRONG_SELL', 'SELL']:
                            await self._send_signal(signal)
                            signals_sent += 1
                        else:
                            logger.info(f"   ⏸️ {asset}: {signal.signal} (не отправляем)")
                        
                        await asyncio.sleep(10)
                        
                    except Exception as e:
                        logger.error(f"❌ [TRADING] Ошибка для {asset}: {e}")
                        continue
            
            logger.info(f"\n{'='*80}")
            logger.info(f"✅ [TRADING] Цикл завершён")
            logger.info(f"   Сигналов сгенерировано: {signals_generated}")
            logger.info(f"   Сигналов отправлено: {signals_sent}")
            logger.info(f"{'='*80}\n")
            
            return {
                'success': True,
                'signals_generated': signals_generated,
                'signals_sent': signals_sent
            }
            
        except Exception as e:
            logger.error(f"❌ [TRADING] Критическая ошибка: {e}")
            return {'success': False, 'error': str(e)}
    
    async def update_positions(self) -> Dict:
        """Обновление открытых позиций"""
        if not self.enabled:
            return {'success': False, 'reason': 'disabled'}
        
        try:
            open_positions = self.signal_generator.positions.get_open_positions()
            
            if not open_positions:
                return {'success': True, 'positions_updated': 0}
            
            logger.debug(f"\n💼 [POSITIONS] Обновление {len(open_positions)} позиций...")
            
            async with aiohttp.ClientSession() as session:
                prices = {}
                
                for position in open_positions:
                    try:
                        price = await self._fetch_current_price(position.asset, session)
                        if price:
                            prices[position.asset] = price
                    except Exception as e:
                        logger.warning(f"⚠️ [POSITIONS] Ошибка получения цены {position.asset}: {e}")
                
                if prices:
                    await self.signal_generator.positions.update_prices(prices)
            
            return {
                'success': True,
                'positions_updated': len(prices)
            }
            
        except Exception as e:
            logger.error(f"❌ [POSITIONS] Ошибка: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _fetch_ohlcv(self, asset: str, session: aiohttp.ClientSession) -> Optional[pd.DataFrame]:
        """Получение OHLCV данных"""
        try:
            symbol = f"{asset}USDT"
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': symbol,
                'interval': '1h',
                'limit': 200
            }
            
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status != 200:
                    return None
                
                data = await resp.json()
                if not data:
                    return None
                
                df = pd.DataFrame(data, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                    'taker_buy_quote', 'ignore'
                ])
                
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = df[col].astype(float)
                
                return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                
        except Exception as e:
            logger.error(f"⚠️ [OHLCV] Ошибка для {asset}: {e}")
            return None
    
    async def _fetch_current_price(self, asset: str, session: aiohttp.ClientSession) -> Optional[float]:
        """Получение текущей цены"""
        try:
            symbol = f"{asset}USDT"
            url = "https://api.binance.com/api/v3/ticker/price"
            params = {'symbol': symbol}
            
            async with session.get(url, params=params, timeout=5) as resp:
                if resp.status != 200:
                    return None
                
                data = await resp.json()
                return float(data.get('price', 0))
                
        except Exception as e:
            logger.debug(f"⚠️ [PRICE] Ошибка для {asset}: {e}")
            return None
    
    async def _send_signal(self, signal):
        """Отправка сигнала в Telegram"""
        try:
            message = self.signal_generator.format_signal_message(signal)
            
            import telegram
            bot = telegram.Bot(token=config.telegram.token)
            
            await bot.send_message(
                chat_id=config.telegram.channel_id,
                text=message,
                parse_mode='HTML'
            )
            
            logger.info(f"✅ [TRADING] Сигнал отправлен: {signal.asset} - {signal.signal}")
            
        except Exception as e:
            logger.error(f"❌ [TRADING] Ошибка отправки сигнала: {e}")