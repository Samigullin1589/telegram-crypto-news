# app/bot/commands/settings.py
"""
Configuration and settings commands
"""

import traceback
import aiohttp
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from app.bot.utils import is_admin, send_long_message
from app.config import config


async def cmd_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /config"""
    
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора")
        return
    
    try:
        from app.scheduler import scheduler
        
        text = "<b>⚙️  КОНФИГУРАЦИЯ СИСТЕМЫ</b>\n\n"

        # ИСПРАВЛЕНО: Безопасный доступ к config.features.whale.*
        _features = getattr(config, 'features', None)
        _whale = getattr(_features, 'whale', None) if _features else None
        posts_per_hour_cap = getattr(_whale, 'posts_per_hour_cap', 3) if _whale else 3
        poll_seconds = getattr(_whale, 'poll_seconds', 300) if _whale else 300

        text += "<b>🔧 GENERAL</b>\n"
        text += f"Posts per Hour: {posts_per_hour_cap}\n"
        text += f"Poll Interval: {poll_seconds}s\n\n"
        
        text += "<b>🐋 WHALE MONITORING</b>\n"
        text += f"Smart Discovery: {'✅' if config.smart_discovery.enabled else '❌'}\n"
        text += f"Adaptive Thresholds: {'✅' if config.adaptive_thresholds.enabled else '❌'}\n"
        text += f"Validation: {'✅' if config.validation.enabled else '❌'}\n\n"
        
        if scheduler.trading_enabled:
            text += "<b>📈 TRADING SYSTEM</b>\n"
            text += "Status: ✅ Enabled\n"
        else:
            text += "<b>📈 TRADING SYSTEM</b>\n"
            text += "Status: ❌ Disabled\n"
        
        if scheduler.chains_enabled:
            text += "\n<b>🌐 MULTI-CHAIN</b>\n"
            text += f"Chains: {', '.join(scheduler.supported_chains)}\n"
        
        await send_long_message(update, text)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def cmd_thresholds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /thresholds"""
    
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора")
        return
    
    try:
        from app.scheduler import scheduler
        
        if not scheduler.adaptive_thresholds:
            await update.message.reply_text("❌ Adaptive thresholds не инициализированы")
            return
        
        stats = scheduler.adaptive_thresholds.get_stats()
        thresholds = stats['current_thresholds']
        
        text = "<b>⚙️  АДАПТИВНЫЕ ПОРОГИ</b>\n\n"
        
        text += f"<b>Режим:</b> {stats['regime'].upper()}\n"
        text += f"<b>Сигналов:</b> {stats['signals_tracked']}\n"
        if stats['signals_tracked'] > 0:
            text += f"<b>Точность:</b> {stats['accuracy']:.1%}\n"
        text += "\n"
        
        text += "<b>Пороги:</b>\n"
        text += f"• Min Confidence: ≥{thresholds['min_confidence']}\n"
        text += f"• Min Size Rel: ≥{thresholds['min_size_rel']:.2%}\n"
        text += f"• Min Volume 24h: ≥${thresholds['min_volume_24h']:,}\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def cmd_regime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /regime"""
    
    try:
        from app.scheduler import scheduler
        
        if not scheduler.adaptive_thresholds:
            await update.message.reply_text("❌ Adaptive system не инициализирована")
            return
        
        async with aiohttp.ClientSession() as session:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": "bitcoin",
                "vs_currencies": "usd",
                "include_24h_change": "true",
                "include_7d_change": "true"
            }
            
            try:
                async with session.get(url, params=params, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        btc_24h = data["bitcoin"].get("usd_24h_change", 0)
                        btc_7d = data["bitcoin"].get("usd_7d_change", 0)
                    else:
                        await update.message.reply_text("❌ Не удалось получить данные")
                        return
            except Exception:
                await update.message.reply_text("❌ Ошибка API")
                return
        
        regime = scheduler.adaptive_thresholds.market_regime
        
        regime_emoji = {
            "bull": "🐂",
            "bear": "🐻",
            "sideways": "🦀"
        }
        
        text = f"<b>📊 РЕЖИМ РЫНКА</b>\n\n"
        text += f"{regime_emoji.get(regime, '📊')} <b>{regime.upper()}</b>\n\n"
        text += f"<b>Bitcoin (7d):</b> {btc_7d:+.2f}%\n"
        text += f"<b>Bitcoin (24h):</b> {btc_24h:+.2f}%\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        traceback.print_exc()


__all__ = ['cmd_config', 'cmd_thresholds', 'cmd_regime']