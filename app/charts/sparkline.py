# app/charts/sparkline.py
"""
Sparkline Chart Renderer
Renders price charts using matplotlib and CCXT
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime
from typing import Optional, List
import ccxt
import asyncio

from app.config import config


class SparklineRenderer:
    """Рендерер графиков (matplotlib + CCXT)"""
    
    def __init__(self):
        self.exchange_preference = self._get_exchange_preference()
        self.chart_theme = self._get_chart_theme()
    
    def _get_exchange_preference(self) -> List[str]:
        """Получает список предпочитаемых бирж"""
        try:
            if hasattr(config, 'EXCHANGE_PREFERENCE'):
                return config.EXCHANGE_PREFERENCE
        except:
            pass
        
        return ['binance', 'okx', 'bybit', 'coinbase', 'kraken']
    
    def _get_chart_theme(self) -> str:
        """Получает тему графика"""
        try:
            if hasattr(config, 'CHART_THEME'):
                return config.CHART_THEME
        except:
            pass
        
        return 'dark'
    
    async def render(self, asset: str, tx_time: datetime, output_path: str) -> bool:
        """Создаёт график с 30s timeout"""
        try:
            return await asyncio.wait_for(
                self._render_internal(asset, tx_time, output_path),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            print(f"⏱️  [CHART] Timeout {asset} (>30s)")
            return False
        except Exception as e:
            print(f"❌ [CHART] Ошибка: {e}")
            return False
    
    async def _render_internal(self, asset: str, tx_time: datetime, output_path: str) -> bool:
        """Внутренний метод рендеринга"""
        try:
            ohlcv = await self._fetch_ohlcv(asset)
            
            if not ohlcv:
                print(f"⚠️  [CHART] Нет данных для {asset}")
                return False
            
            timestamps = [datetime.fromtimestamp(candle[0] / 1000) for candle in ohlcv]
            closes = [candle[4] for candle in ohlcv]
            
            fig, ax = plt.subplots(figsize=(10, 4))
            
            if self.chart_theme == 'dark':
                fig.patch.set_facecolor('#1e1e1e')
                ax.set_facecolor('#2d2d2d')
                text_color = '#ffffff'
                line_color = '#00d9ff'
            else:
                fig.patch.set_facecolor('#ffffff')
                ax.set_facecolor('#f5f5f5')
                text_color = '#000000'
                line_color = '#0088cc'
            
            ax.plot(timestamps, closes, color=line_color, linewidth=2)
            
            closest_idx = min(range(len(timestamps)), key=lambda i: abs((timestamps[i] - tx_time).total_seconds()))
            ax.scatter([timestamps[closest_idx]], [closes[closest_idx]], 
                      color='#ff0000', s=100, zorder=5, marker='o')
            
            ax.tick_params(colors=text_color)
            ax.spines['bottom'].set_color(text_color)
            ax.spines['left'].set_color(text_color)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            title = f"{asset}/USDT • 5m • 24h"
            ax.set_title(title, color=text_color, fontsize=14, pad=20)
            
            ax.grid(True, alpha=0.2, color=text_color)
            
            ax.set_xlabel('Время', color=text_color)
            ax.set_ylabel('Цена (USDT)', color=text_color)
            
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            plt.savefig(output_path, dpi=100, facecolor=fig.get_facecolor())
            plt.close()
            
            print(f"📊 [CHART] График создан: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ [CHART] Ошибка рендеринга: {e}")
            return False
    
    async def _fetch_ohlcv(self, asset: str) -> Optional[List]:
        """Получает OHLCV через CCXT"""
        symbol = f"{asset}/USDT"
        timeframe = '5m'
        limit = 288
        
        for exchange_id in self.exchange_preference:
            try:
                print(f"📡 [CHART] Пробуем {exchange_id} для {symbol}")
                
                exchange_class = getattr(ccxt, exchange_id)
                exchange = exchange_class({
                    'enableRateLimit': True,
                    'timeout': 10000
                })
                
                await exchange.load_markets()
                
                if symbol not in exchange.symbols:
                    print(f"  ⚠️  {symbol} не найден на {exchange_id}")
                    await exchange.close()
                    continue
                
                ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                await exchange.close()
                
                if ohlcv:
                    print(f"  ✅ Получено {len(ohlcv)} свечей с {exchange_id}")
                    return ohlcv
                
            except Exception as e:
                print(f"  ❌ Ошибка с {exchange_id}: {e}")
                try:
                    await exchange.close()
                except:
                    pass
                continue
        
        return None