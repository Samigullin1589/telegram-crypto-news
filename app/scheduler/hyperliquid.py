# app/scheduler/hyperliquid.py
"""
Hyperliquid DEX Monitoring
Whale activity, liquidations, funding rates, volume spikes
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict

from app.config import config

logger = logging.getLogger(__name__)

try:
    from app.exchanges import HyperliquidMonitor, HYPERLIQUID_AVAILABLE
except ImportError:
    HYPERLIQUID_AVAILABLE = False
    HyperliquidMonitor = None
    logger.warning("⚠️ Hyperliquid module not available")


class HyperliquidSystem:
    """Система мониторинга Hyperliquid DEX"""
    
    def __init__(self, components: Dict):
        self.enabled = False
        self.publisher = components.get('publisher')
        
        if not HYPERLIQUID_AVAILABLE or not config.is_feature_enabled('hyperliquid'):
            logger.info("🌊 [HYPERLIQUID] Disabled")
            return
        
        self.enabled = True
        logger.info("🌊 [HYPERLIQUID] Система активна")
    
    async def check_whale_activity(self) -> Dict:
        """Проверка whale activity"""
        if not self.enabled:
            return {'success': False, 'reason': 'disabled'}
        
        try:
            logger.info(f"\n🌊 [HYPERLIQUID] Проверка Whale Activity")
            
            async with HyperliquidMonitor() as monitor:
                activities = await monitor.detect_whale_activity(
                    min_activity_usd=config.hyperliquid.min_whale_activity_usd,
                    lookback_minutes=10
                )
                
                sent = 0
                if activities and config.hyperliquid.notify_whale_activity:
                    for activity in activities:
                        if activity.confidence >= 70:
                            try:
                                message = monitor.format_whale_activity_alert(activity)
                                
                                await self.publisher.bot.send_message(
                                    chat_id=config.telegram.channel_id,
                                    text=message,
                                    parse_mode='HTML'
                                )
                                
                                sent += 1
                                logger.info(f"✅ [HYPERLIQUID] Whale activity: {activity.asset}")
                                await asyncio.sleep(2)
                                
                            except Exception as e:
                                logger.error(f"⚠️ [HYPERLIQUID] Send error: {e}")
                
                logger.info(f"   Найдено: {len(activities)}, Отправлено: {sent}")
                
                return {
                    'success': True,
                    'activities_found': len(activities),
                    'activities_sent': sent
                }
                
        except Exception as e:
            logger.error(f"❌ [HYPERLIQUID] Whale activity error: {e}")
            return {'success': False, 'error': str(e)}
    
    async def check_liquidations(self) -> Dict:
        """Проверка ликвидаций"""
        if not self.enabled:
            return {'success': False, 'reason': 'disabled'}
        
        try:
            logger.info(f"\n💥 [HYPERLIQUID] Проверка Liquidations")
            
            async with HyperliquidMonitor() as monitor:
                liquidations = await monitor.detect_liquidations(
                    lookback_minutes=10,
                    min_liquidation_usd=config.hyperliquid.min_liquidation_usd
                )
                
                sent = 0
                if liquidations and config.hyperliquid.notify_liquidations:
                    for liq in liquidations:
                        if liq.confidence >= 70:
                            try:
                                message = monitor.format_liquidation_alert(liq)
                                
                                await self.publisher.bot.send_message(
                                    chat_id=config.telegram.channel_id,
                                    text=message,
                                    parse_mode='HTML'
                                )
                                
                                sent += 1
                                logger.info(f"✅ [HYPERLIQUID] Liquidation: {liq.asset}")
                                await asyncio.sleep(2)
                                
                            except Exception as e:
                                logger.error(f"⚠️ [HYPERLIQUID] Send error: {e}")
                
                logger.info(f"   Найдено: {len(liquidations)}, Отправлено: {sent}")
                
                return {
                    'success': True,
                    'liquidations_found': len(liquidations),
                    'liquidations_sent': sent
                }
                
        except Exception as e:
            logger.error(f"❌ [HYPERLIQUID] Liquidations error: {e}")
            return {'success': False, 'error': str(e)}