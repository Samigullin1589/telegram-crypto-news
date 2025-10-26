# app/alerts.py
"""
Advanced Alert System with Rate Limiting and Priority Management
"""

import asyncio
import telegram
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from enum import Enum
from collections import defaultdict, deque
from dataclasses import dataclass
from app import settings


class AlertPriority(Enum):
    """Приоритет алертов"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Alert:
    """Структура алерта"""
    alert_type: str
    message: str
    priority: AlertPriority
    details: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class AlertRateLimiter:
    """Умный rate limiter для предотвращения спама"""
    
    def __init__(self, cooldown_seconds: int = 300):
        self.cooldown = cooldown_seconds
        self.last_alert_times: Dict[str, datetime] = {}
        self.alert_counts: Dict[str, int] = defaultdict(int)
        self.suppressed_count: Dict[str, int] = defaultdict(int)
    
    def should_send(self, alert_type: str, priority: AlertPriority) -> bool:
        """
        Определяет нужно ли отправлять алерт
        
        Логика:
        - CRITICAL: всегда отправляем
        - HIGH: отправляем если прошло >2 минуты с последнего
        - MEDIUM/LOW: отправляем если прошло >5 минут
        """
        now = datetime.utcnow()
        
        # CRITICAL всегда отправляем
        if priority == AlertPriority.CRITICAL:
            return True
        
        # Проверяем cooldown
        if alert_type in self.last_alert_times:
            elapsed = (now - self.last_alert_times[alert_type]).seconds
            
            if priority == AlertPriority.HIGH:
                min_interval = 120  # 2 минуты
            else:
                min_interval = self.cooldown  # 5 минут
            
            if elapsed < min_interval:
                self.suppressed_count[alert_type] += 1
                return False
        
        return True
    
    def record_sent(self, alert_type: str):
        """Записывает отправку алерта"""
        self.last_alert_times[alert_type] = datetime.utcnow()
        self.alert_counts[alert_type] += 1
        
        # Сбрасываем счётчик подавленных
        if alert_type in self.suppressed_count:
            del self.suppressed_count[alert_type]
    
    def get_suppressed_count(self, alert_type: str) -> int:
        """Возвращает количество подавленных алертов"""
        return self.suppressed_count.get(alert_type, 0)
    
    def get_stats(self) -> Dict:
        """Статистика работы rate limiter"""
        return {
            'total_types': len(self.alert_counts),
            'total_sent': sum(self.alert_counts.values()),
            'total_suppressed': sum(self.suppressed_count.values()),
            'by_type': dict(self.alert_counts)
        }


class AlertQueue:
    """Очередь алертов с приоритизацией"""
    
    def __init__(self, max_size: int = 100):
        self.queue: deque[Alert] = deque(maxlen=max_size)
        self._lock = asyncio.Lock()
    
    async def add(self, alert: Alert):
        """Добавляет алерт в очередь"""
        async with self._lock:
            self.queue.append(alert)
            # Сортируем по приоритету (высший первым)
            self.queue = deque(
                sorted(self.queue, key=lambda x: x.priority.value, reverse=True),
                maxlen=self.queue.maxlen
            )
    
    async def get_next(self) -> Optional[Alert]:
        """Извлекает следующий алерт"""
        async with self._lock:
            if self.queue:
                return self.queue.popleft()
            return None
    
    def size(self) -> int:
        """Размер очереди"""
        return len(self.queue)


class AlertFormatter:
    """Форматирование алертов для Telegram"""
    
    @staticmethod
    def format_critical(alert: Alert) -> str:
        """Форматирование критического алерта"""
        text = f"🚨 *КРИТИЧЕСКАЯ ОШИБКА*\n\n"
        text += f"*Тип:* `{alert.alert_type}`\n"
        text += f"*Сообщение:* {alert.message}\n"
        text += f"*Время:* {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        
        if alert.details:
            # Обрезаем детали до 500 символов
            details = alert.details[:500]
            text += f"\n*Детали:*\n```\n{details}\n```"
        
        return text
    
    @staticmethod
    def format_warning(alert: Alert) -> str:
        """Форматирование предупреждения"""
        text = f"⚠️  *Предупреждение*\n\n"
        text += f"*Тип:* `{alert.alert_type}`\n"
        text += f"{alert.message}"
        
        if alert.details:
            text += f"\n\n_{alert.details}_"
        
        return text
    
    @staticmethod
    def format_info(alert: Alert) -> str:
        """Форматирование информационного сообщения"""
        emoji_map = {
            'startup': '✅',
            'shutdown': '🛑',
            'stats': '📊',
            'discovery': '🔍',
            'validation': '🧹',
            'performance': '📈'
        }
        
        emoji = emoji_map.get(alert.alert_type.lower(), 'ℹ️')
        
        text = f"{emoji} *{alert.alert_type.replace('_', ' ').title()}*\n\n"
        text += alert.message
        
        return text
    
    @staticmethod
    def format_stats(stats: Dict) -> str:
        """Форматирование статистики"""
        text = "📊 *Ежедневная статистика*\n\n"
        
        # News System
        if 'news' in stats:
            news = stats['news']
            text += "*📰 Новостной бот:*\n"
            text += f"  • Обработано: {news.get('processed', 0)}\n"
            text += f"  • Опубликовано: {news.get('published', 0)}\n"
            if news.get('processed', 0) > 0:
                rate = (news.get('published', 0) / news['processed']) * 100
                text += f"  • Success rate: {rate:.1f}%\n"
            text += "\n"
        
        # Whale System
        if 'whale' in stats:
            whale = stats['whale']
            text += "*🐋 Whale Monitor:*\n"
            text += f"  • События собрано: {whale.get('events_collected', 0)}\n"
            text += f"  • Прошло фильтры: {whale.get('events_qualified', 0)}\n"
            text += f"  • Опубликовано: {whale.get('events_published', 0)}\n"
            
            if 'events_successful' in whale and 'events_failed' in whale:
                total = whale['events_successful'] + whale['events_failed']
                if total > 0:
                    accuracy = (whale['events_successful'] / total) * 100
                    text += f"  • Точность: {accuracy:.1f}%\n"
            
            text += "\n"
        
        # Adaptive System
        if 'adaptive' in stats:
            adaptive = stats['adaptive']
            text += "*🧠 Адаптивная система:*\n"
            text += f"  • Режим рынка: {adaptive.get('regime', 'unknown')}\n"
            text += f"  • Отслежено сигналов: {adaptive.get('signals_tracked', 0)}\n"
            if 'accuracy' in adaptive:
                text += f"  • Точность: {adaptive['accuracy'] * 100:.1f}%\n"
            text += "\n"
        
        # Wallet DB
        if 'wallet_db' in stats:
            wdb = stats['wallet_db']
            text += "*💾 База кошельков:*\n"
            text += f"  • Всего: {wdb.get('total', 0)}\n"
            text += f"  • Активных: {wdb.get('active', 0)}\n"
            text += "\n"
        
        # Общее
        if 'errors' in stats:
            text += f"*❌ Ошибок за период:* {stats['errors']}\n"
        
        return text


class AlertManager:
    """
    Продвинутый менеджер алертов с очередью, rate limiting и приоритизацией
    """
    
    def __init__(self, admin_chat_id: Optional[str] = None):
        self.bot = telegram.Bot(token=settings.TELEGRAM_TOKEN)
        self.admin_chat_id = admin_chat_id or settings.ADMIN_CHAT_ID
        
        # Компоненты
        self.rate_limiter = AlertRateLimiter(settings.ALERT_COOLDOWN_SECONDS)
        self.queue = AlertQueue(max_size=100)
        self.formatter = AlertFormatter()
        
        # Статистика
        self.stats = {
            'sent': 0,
            'failed': 0,
            'suppressed': 0,
            'by_priority': defaultdict(int)
        }
        
        # Фоновая задача отправки
        self._sender_task: Optional[asyncio.Task] = None
        self._running = False
        
        print(f"📨 [ALERTS] Инициализирован. Admin: {self.admin_chat_id[:4]}...{self.admin_chat_id[-4:]}")
    
    async def start(self):
        """Запускает фоновую отправку алертов"""
        if self._running:
            return
        
        self._running = True
        self._sender_task = asyncio.create_task(self._alert_sender_loop())
        print("✅ [ALERTS] Фоновая отправка запущена")
    
    async def stop(self):
        """Останавливает фоновую отправку"""
        self._running = False
        
        if self._sender_task:
            self._sender_task.cancel()
            try:
                await self._sender_task
            except asyncio.CancelledError:
                pass
        
        print("🛑 [ALERTS] Фоновая отправка остановлена")
    
    async def _alert_sender_loop(self):
        """Фоновый цикл отправки алертов из очереди"""
        while self._running:
            try:
                alert = await self.queue.get_next()
                
                if alert:
                    await self._send_alert(alert)
                    await asyncio.sleep(2)  # Небольшая задержка между алертами
                else:
                    await asyncio.sleep(10)  # Ждём новые алерты
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ [ALERTS] Ошибка в sender loop: {e}")
                await asyncio.sleep(30)
    
    async def send_critical_alert(
        self,
        error_type: str,
        message: str,
        details: Optional[str] = None
    ):
        """Отправляет критический алерт (высший приоритет)"""
        alert = Alert(
            alert_type=error_type,
            message=message,
            priority=AlertPriority.CRITICAL,
            details=details
        )
        
        # Критические алерты отправляем немедленно, минуя очередь
        await self._send_alert(alert)
    
    async def send_warning(self, message: str, alert_type: str = "warning"):
        """Отправляет предупреждение"""
        alert = Alert(
            alert_type=alert_type,
            message=message,
            priority=AlertPriority.HIGH
        )
        
        await self.queue.add(alert)
    
    async def send_info(self, message: str, alert_type: str = "info"):
        """Отправляет информационное сообщение"""
        alert = Alert(
            alert_type=alert_type,
            message=message,
            priority=AlertPriority.LOW
        )
        
        await self.queue.add(alert)
    
    async def send_notification(self, message: str, alert_type: str = "notification"):
        """Отправляет обычное уведомление"""
        alert = Alert(
            alert_type=alert_type,
            message=message,
            priority=AlertPriority.MEDIUM
        )
        
        await self.queue.add(alert)
    
    async def send_startup_notification(self):
        """Отправляет уведомление о запуске системы"""
        if not settings.SEND_STARTUP_NOTIFICATION:
            return
        
        mode = 'DISCOVERY' if settings.ASSETS == '*' else 'ALLOWLIST'
        
        startup_text = (
            f"✅ *Система запущена*\n\n"
            f"*Режим:* {mode}\n"
            f"*Порог whale:* ${settings.MIN_USD_FLOOR:,.0f}\n"
            f"*Время:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        )
        
        # Добавляем инфо о системах самообучения
        if settings.SMART_DISCOVERY_ENABLED:
            startup_text += f"*Smart Discovery:* ✅ каждые {settings.SMART_DISCOVERY_INTERVAL_HOURS}ч\n"
        if settings.ADAPTIVE_THRESHOLDS_ENABLED:
            startup_text += f"*Adaptive Thresholds:* ✅\n"
        if settings.PERFORMANCE_TRACKING_ENABLED:
            startup_text += f"*Performance Tracking:* ✅\n"
        
        alert = Alert(
            alert_type="startup",
            message=startup_text,
            priority=AlertPriority.MEDIUM
        )
        
        await self._send_alert(alert)
    
    async def send_daily_stats(self, stats: Dict):
        """Отправляет ежедневную статистику"""
        if not settings.SEND_DAILY_STATS:
            return
        
        stats_text = self.formatter.format_stats(stats)
        
        alert = Alert(
            alert_type="stats",
            message=stats_text,
            priority=AlertPriority.LOW
        )
        
        await self._send_alert(alert)
    
    async def _send_alert(self, alert: Alert):
        """Внутренний метод отправки алерта"""
        
        # Проверяем rate limiting
        if not self.rate_limiter.should_send(alert.alert_type, alert.priority):
            self.stats['suppressed'] += 1
            return
        
        # Форматируем сообщение
        if alert.priority == AlertPriority.CRITICAL:
            text = self.formatter.format_critical(alert)
        elif alert.priority in (AlertPriority.HIGH, AlertPriority.MEDIUM):
            text = self.formatter.format_warning(alert)
        else:
            text = self.formatter.format_info(alert)
        
        # Добавляем информацию о подавленных алертах
        suppressed = self.rate_limiter.get_suppressed_count(alert.alert_type)
        if suppressed > 0:
            text += f"\n\n_({suppressed} похожих алертов подавлено)_"
        
        # Отправляем
        try:
            await self.bot.send_message(
                chat_id=self.admin_chat_id,
                text=text,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
            # Обновляем статистику
            self.rate_limiter.record_sent(alert.alert_type)
            self.stats['sent'] += 1
            self.stats['by_priority'][alert.priority.name] += 1
            
            print(f"📨 [ALERT] Отправлен: {alert.alert_type} ({alert.priority.name})")
            
        except telegram.error.BadRequest as e:
            # Пробуем без Markdown
            try:
                plain_text = text.replace('*', '').replace('_', '').replace('`', '')
                await self.bot.send_message(
                    chat_id=self.admin_chat_id,
                    text=plain_text,
                    disable_web_page_preview=True
                )
                
                self.rate_limiter.record_sent(alert.alert_type)
                self.stats['sent'] += 1
                print(f"📨 [ALERT] Отправлен (plain): {alert.alert_type}")
                
            except Exception as e2:
                print(f"❌ [ALERT] Не удалось отправить: {e2}")
                self.stats['failed'] += 1
        
        except Exception as e:
            print(f"❌ [ALERT] Ошибка отправки: {e}")
            self.stats['failed'] += 1
    
    def get_stats(self) -> Dict:
        """Получить статистику работы"""
        return {
            **self.stats,
            'queue_size': self.queue.size(),
            'rate_limiter': self.rate_limiter.get_stats()
        }
    
    def print_stats(self):
        """Вывод статистики в консоль"""
        stats = self.get_stats()
        
        print("\n📊 ALERT MANAGER STATS:")
        print(f"  Отправлено: {stats['sent']}")
        print(f"  Провалено: {stats['failed']}")
        print(f"  Подавлено: {stats['suppressed']}")
        print(f"  В очереди: {stats['queue_size']}")
        
        if stats['by_priority']:
            print(f"  По приоритетам:")
            for priority, count in stats['by_priority'].items():
                print(f"    {priority}: {count}")


# =========================================================================
# Глобальный singleton экземпляр
# =========================================================================

_alert_manager_instance: Optional[AlertManager] = None
_instance_lock = asyncio.Lock()


async def get_alert_manager(admin_chat_id: Optional[str] = None) -> AlertManager:
    """
    Получает глобальный экземпляр AlertManager (async singleton)
    """
    global _alert_manager_instance
    
    async with _instance_lock:
        if _alert_manager_instance is None:
            _alert_manager_instance = AlertManager(admin_chat_id)
            await _alert_manager_instance.start()
        
        return _alert_manager_instance


def get_alert_manager_sync(admin_chat_id: Optional[str] = None) -> AlertManager:
    """
    Синхронная версия для обратной совместимости
    НЕ запускает фоновую отправку!
    """
    global _alert_manager_instance
    
    if _alert_manager_instance is None:
        _alert_manager_instance = AlertManager(admin_chat_id)
    
    return _alert_manager_instance