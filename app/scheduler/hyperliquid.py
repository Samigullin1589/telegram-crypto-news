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

        # Дедупликация: храним время последней публикации для каждой монеты
        self.last_published = {}  # {coin: timestamp}
        self.publish_cooldown = 300  # 5 минут между публикациями одной монеты

        # DEBUG: Проверяем что publisher загружен
        if self.publisher:
            logger.info(f"🌊 [HYPERLIQUID] Publisher загружен: {type(self.publisher).__name__}")
        else:
            logger.error("🌊 [HYPERLIQUID] ❌ Publisher отсутствует!")

        if not HYPERLIQUID_AVAILABLE or not config.is_feature_enabled('hyperliquid'):
            logger.info("🌊 [HYPERLIQUID] Disabled")
            return

        self.enabled = True
        logger.info("🌊 [HYPERLIQUID] Система активна")

    def _can_publish(self, coin: str) -> bool:
        """
        Проверка: можно ли публиковать монету (дедупликация)

        Args:
            coin: Название монеты

        Returns:
            True если прошло достаточно времени с последней публикации
        """
        now = datetime.now()
        last_time = self.last_published.get(coin)

        if last_time is None:
            return True

        elapsed = (now - last_time).total_seconds()
        return elapsed >= self.publish_cooldown

    def _mark_published(self, coin: str):
        """Отметить монету как опубликованную"""
        self.last_published[coin] = datetime.now()

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
                skipped_cooldown = 0
                if activities and config.hyperliquid.notify_whale_activity:
                    logger.info(f"📊 [HYPERLIQUID] Проверяем {len(activities)} activities для публикации")
                    for activity in activities:
                        logger.info(f"   • {activity.coin}: confidence={activity.confidence:.2f} ({activity.confidence*100:.0f}%)")

                        # Публикуем только высококачественные сигналы (70%+)
                        if activity.confidence >= 0.7:
                            # Проверяем дедупликацию
                            if not self._can_publish(activity.coin):
                                logger.info(f"   ⏭️  Пропускаем {activity.coin}: опубликовано недавно (cooldown 5 мин)")
                                skipped_cooldown += 1
                                continue

                            try:
                                if not self.publisher:
                                    logger.error(f"❌ [HYPERLIQUID] Publisher None, не могу отправить {activity.coin}")
                                    continue

                                message = monitor.format_whale_activity_alert(activity)

                                await self.publisher.bot.send_message(
                                    chat_id=config.telegram.channel_id,
                                    text=message,
                                    parse_mode='HTML'
                                )

                                # Отмечаем как опубликованное
                                self._mark_published(activity.coin)

                                sent += 1
                                logger.info(f"✅ [HYPERLIQUID] Whale activity: {activity.coin}")
                                await asyncio.sleep(2)

                            except Exception as e:
                                logger.error(f"⚠️ [HYPERLIQUID] Send error: {e}")
                                import traceback
                                logger.error(traceback.format_exc())
                        else:
                            logger.info(f"   ⏭️  Пропускаем {activity.coin}: confidence {activity.confidence:.2f} ({activity.confidence*100:.0f}%) < 70%")

                logger.info(f"   Найдено: {len(activities)}, Отправлено: {sent}, Пропущено (cooldown): {skipped_cooldown}")

                return {
                    'success': True,
                    'activities_found': len(activities),
                    'activities_sent': sent,
                    'skipped_cooldown': skipped_cooldown
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
                skipped_cooldown = 0
                if liquidations and config.hyperliquid.notify_liquidations:
                    logger.info(f"📊 [HYPERLIQUID] Проверяем {len(liquidations)} liquidations для публикации")
                    for liq in liquidations:
                        logger.info(f"   • {liq.coin}: confidence={liq.confidence:.2f} ({liq.confidence*100:.0f}%)")

                        # Публикуем только высококачественные сигналы (70%+)
                        if liq.confidence >= 0.7:
                            # Проверяем дедупликацию
                            if not self._can_publish(liq.coin):
                                logger.info(f"   ⏭️  Пропускаем {liq.coin}: опубликовано недавно (cooldown 5 мин)")
                                skipped_cooldown += 1
                                continue

                            try:
                                if not self.publisher:
                                    logger.error(f"❌ [HYPERLIQUID] Publisher None, не могу отправить {liq.coin}")
                                    continue

                                message = monitor.format_liquidation_alert(liq)

                                await self.publisher.bot.send_message(
                                    chat_id=config.telegram.channel_id,
                                    text=message,
                                    parse_mode='HTML'
                                )

                                # Отмечаем как опубликованное
                                self._mark_published(liq.coin)

                                sent += 1
                                logger.info(f"✅ [HYPERLIQUID] Liquidation: {liq.coin}")
                                await asyncio.sleep(2)

                            except Exception as e:
                                logger.error(f"⚠️ [HYPERLIQUID] Send error: {e}")
                                import traceback
                                logger.error(traceback.format_exc())
                        else:
                            logger.info(f"   ⏭️  Пропускаем {liq.coin}: confidence {liq.confidence:.2f} ({liq.confidence*100:.0f}%) < 70%")

                logger.info(f"   Найдено: {len(liquidations)}, Отправлено: {sent}, Пропущено (cooldown): {skipped_cooldown}")

                return {
                    'success': True,
                    'liquidations_found': len(liquidations),
                    'liquidations_sent': sent,
                    'skipped_cooldown': skipped_cooldown
                }
                
        except Exception as e:
            logger.error(f"❌ [HYPERLIQUID] Liquidations error: {e}")
            return {'success': False, 'error': str(e)}