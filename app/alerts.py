# app/alerts.py
"""
Система уведомлений администратора о критических ошибках
"""
import telegram
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from app import settings

class AlertManager:
    """Отправляет уведомления администратору"""
    
    def __init__(self, admin_chat_id: Optional[str] = None):
        self.bot = telegram.Bot(token=settings.TELEGRAM_TOKEN)
        self.admin_chat_id = admin_chat_id or settings.CHAT_ID  # По умолчанию тот же канал
        self.last_alert_time = {}
        self.alert_cooldown = 300  # 5 минут между повторами одной и той же ошибки
    
    async def send_critical_alert(self, error_type: str, message: str, details: Optional[str] = None):
        """Отправляет критическое уведомление"""
        
        # Проверяем cooldown
        now = datetime.utcnow()
        if error_type in self.last_alert_time:
            time_since_last = (now - self.last_alert_time[error_type]).seconds
            if time_since_last < self.alert_cooldown:
                return  # Пропускаем, чтобы не спамить
        
        self.last_alert_time[error_type] = now
        
        alert_text = f"🚨 *КРИТИЧЕСКАЯ ОШИБКА*\n\n"
        alert_text += f"*Тип:* {error_type}\n"
        alert_text += f"*Сообщение:* {message}\n"
        alert_text += f"*Время:* {now.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        
        if details:
            alert_text += f"\n*Детали:*\n```\n{details[:500]}\n```"
        
        try:
            await self.bot.send_message(
                chat_id=self.admin_chat_id,
                text=alert_text,
                parse_mode='Markdown'
            )
            print(f"📨 [ALERT] Отправлено уведомление: {error_type}")
        except Exception as e:
            print(f"❌ [ALERT] Не удалось отправить уведомление: {e}")
    
    async def send_warning(self, message: str):
        """Отправляет предупреждение (не критическое)"""
        
        warning_text = f"⚠️ *Предупреждение*\n\n{message}"
        
        try:
            await self.bot.send_message(
                chat_id=self.admin_chat_id,
                text=warning_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"❌ [ALERT] Не удалось отправить предупреждение: {e}")
    
    async def send_startup_notification(self):
        """Отправляет уведомление о запуске системы"""
        
        startup_text = (
            "✅ *Система запущена*\n\n"
            f"*Режим:* {'DISCOVERY' if settings.ASSETS == '*' else 'ALLOWLIST'}\n"
            f"*Порог:* ${settings.MIN_USD_FLOOR:,.0f}\n"
            f"*Время:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        
        try:
            await self.bot.send_message(
                chat_id=self.admin_chat_id,
                text=startup_text,
                parse_mode='Markdown'
            )
            print(f"✅ [ALERT] Уведомление о запуске отправлено")
        except Exception as e:
            print(f"⚠️  [ALERT] Не удалось отправить уведомление о запуске: {e}")
    
    async def send_daily_stats(self, stats: dict):
        """Отправляет ежедневную статистику"""
        
        stats_text = (
            "📊 *Статистика за 24 часа*\n\n"
            f"*События собрано:* {stats.get('events_collected', 0)}\n"
            f"*Прошло фильтры:* {stats.get('events_qualified', 0)}\n"
            f"*Опубликовано:* {stats.get('events_published', 0)}\n"
            f"*Ошибки:* {stats.get('errors', 0)}\n"
        )
        
        try:
            await self.bot.send_message(
                chat_id=self.admin_chat_id,
                text=stats_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"❌ [ALERT] Не удалось отправить статистику: {e}")


# =========================================================================
# Глобальный экземпляр (singleton)
# =========================================================================

_alert_manager_instance = None

def get_alert_manager(admin_chat_id: Optional[str] = None) -> AlertManager:
    """Получает глобальный экземпляр AlertManager"""
    global _alert_manager_instance
    
    if _alert_manager_instance is None:
        _alert_manager_instance = AlertManager(admin_chat_id)
    
    return _alert_manager_instance