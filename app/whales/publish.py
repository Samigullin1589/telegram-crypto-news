# app/whales/publish.py
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict, Optional
from app import settings
from app.whales.normalize import WhaleEvent

class WhalePublisher:
    """Публикация событий китов в Telegram"""
    
    def __init__(self):
        self.bot = telegram.Bot(token=settings.TELEGRAM_TOKEN)
        self.chat_id = settings.CHAT_ID
    
    async def publish_whale_event(
        self,
        event: WhaleEvent,
        verdict: str,
        confidence: int,
        news: List[Dict],
        chart_path: Optional[str] = None
    ) -> bool:
        """Публикует событие кита в канал"""
        
        try:
            message = self._format_message(event, verdict, confidence, news)
            keyboard = self._create_keyboard(event, news)
            
            if chart_path and settings.ENABLE_IMAGES:
                with open(chart_path, 'rb') as photo:
                    await self.bot.send_photo(
                        chat_id=self.chat_id,
                        photo=photo,
                        caption=message,
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
            else:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode='Markdown',
                    disable_web_page_preview=True,
                    reply_markup=keyboard
                )
            
            print(f"✅ [PUBLISH] Опубликовано: {event.asset} {event.amount_usd:,.0f}$")
            return True
            
        except telegram.error.BadRequest as e:
            print(f"⚠️  [PUBLISH] Ошибка Markdown: {e}")
            
            try:
                message_plain = self._strip_markdown(message)
                
                if chart_path and settings.ENABLE_IMAGES:
                    with open(chart_path, 'rb') as photo:
                        await self.bot.send_photo(
                            chat_id=self.chat_id,
                            photo=photo,
                            caption=message_plain,
                            reply_markup=keyboard
                        )
                else:
                    await self.bot.send_message(
                        chat_id=self.chat_id,
                        text=message_plain,
                        disable_web_page_preview=True,
                        reply_markup=keyboard
                    )
                
                print("✅ [PUBLISH] Опубликовано без Markdown")
                return True
                
            except Exception as e_plain:
                print(f"❌ [PUBLISH] Повторная отправка не удалась: {e_plain}")
                return False
        
        except Exception as e:
            print(f"❌ [PUBLISH] Ошибка: {e}")
            return False
    
    def _format_message(self, event: WhaleEvent, verdict: str, confidence: int, news: List[Dict]) -> str:
        """Форматирует текст сообщения"""
        
        verdict_emoji = {
            "bullish": "🟢",
            "bearish": "🔴",
            "neutral": "🟡"
        }[verdict]
        
        lines = [
            f"{verdict_emoji} *Крупный перевод по {event.asset}*",
            "",
            f"*Факт:* {event.amount_native:,.2f} {event.asset} ≈ {event.amount_usd:,.0f}$ → {self._format_direction(event)}",
            f"*Фаза:* {self._format_phase(event)}",
            f"*Контекст:* {self._format_context(event)}",
        ]
        
        if event.history_hint and event.history_hint.d1h is not None:
            lines.append(f"*В прошлый раз:* {self._format_history(event.history_hint)}")
        
        lines.append(f"*Торговый план:* {self._generate_trade_plan(event, verdict)}")
        
        verdict_ru = {"bullish": "бычий", "bearish": "медвежий", "neutral": "нейтральный"}[verdict]
        lines.append(f"*Вердикт:* {verdict_ru}, уверенность {confidence}/100, горизонт 4–8 ч")
        
        if news:
            lines.append("")
            lines.append("*Новости:*")
            for n in news:
                lines.append(f"• {n['title'][:80]}...")
        
        lines.append("")
        lines.append("_Дисклеймер: не финсовет. Риск: возможна внутренняя консолидация/bridge._")
        
        return "\n".join(lines)
    
    def _format_direction(self, event: WhaleEvent) -> str:
        """Форматирует направление"""
        direction_map = {
            "inflow_to_exchange": "приток на биржу",
            "outflow_to_cold": "отток в холодное хранилище",
            "bridge": "мост между биржами",
            "internal": "внутренний перевод",
            "unknown": "неизвестное направление"
        }
        
        desc = direction_map.get(event.direction, "перемещение")
        
        to_labels = event.labels.get("to", [])
        if to_labels:
            best_label = max(to_labels, key=lambda l: l.confidence)
            if best_label.confidence >= 70 and best_label.details:
                desc += f" ({best_label.details})"
        
        return desc
    
    def _format_phase(self, event: WhaleEvent) -> str:
        """Форматирует фазу"""
        phase_map = {
            "activation": "активация (первое движение)",
            "transfer_cluster": "кластер переводов",
            "deposit_confirmed": "подтверждённый депозит",
            "execution": "исполнение на рынке"
        }
        return phase_map.get(event.phase, event.phase)
    
    def _format_context(self, event: WhaleEvent) -> str:
        """Форматирует контекст"""
        parts = []
        
        if event.cluster:
            parts.append(f"кластер {event.cluster.tx_in_window} tx за {event.cluster.window_minutes} мин")
        
        if event.market.volume_24h_usd:
            size_rel = (event.amount_usd / event.market.volume_24h_usd) * 100
            parts.append(f"доля от 24h объёма {size_rel:.2f}%")
        
        return "; ".join(parts) if parts else "единичный перевод"
    
    def _format_history(self, hint) -> str:
        """Форматирует 'в прошлый раз'"""
        parts = []
        
        if hint.d1h is not None:
            parts.append(f"{hint.d1h:+.1f}% (1ч)")
        if hint.d4h is not None:
            parts.append(f"{hint.d4h:+.1f}% (4ч)")
        if hint.d24h is not None:
            parts.append(f"{hint.d24h:+.1f}% (24ч)")
        
        result = " / ".join(parts)
        
        if hint.comparable_ts:
            result += f" (событие от {hint.comparable_ts[:10]})"
        
        return result
    
    def _generate_trade_plan(self, event: WhaleEvent, verdict: str) -> str:
        """Генерирует торговый план"""
        
        if verdict == "bearish":
            trigger = "Продажа при пробое поддержки (M5-M15)"
            invalidation = "Инвалидация: возврат выше VWAP(M5)"
        elif verdict == "bullish":
            trigger = "Покупка при удержании уровня (M5-M15)"
            invalidation = "Инвалидация: пробой локального минимума"
        else:
            trigger = "Наблюдение, дожидаемся подтверждения"
            invalidation = "Инвалидация: отсутствие движения 2-4ч"
        
        return f"{trigger}; {invalidation}"
    
    def _create_keyboard(self, event: WhaleEvent, news: List[Dict]) -> InlineKeyboardMarkup:
        """Создаёт inline-кнопки"""
        
        buttons = []
        
        row1 = []
        if event.links.get("tx"):
            row1.append(InlineKeyboardButton("🔗 TX", url=event.links["tx"]))
        if event.links.get("from"):
            row1.append(InlineKeyboardButton("📤 FROM", url=event.links["from"]))
        if event.links.get("to"):
            row1.append(InlineKeyboardButton("📥 TO", url=event.links["to"]))
        
        if row1:
            buttons.append(row1)
        
        if news:
            row2 = []
            for i, n in enumerate(news[:2], 1):
                row2.append(InlineKeyboardButton(f"📰 Новость {i}", url=n["url"]))
            buttons.append(row2)
        
        tv_symbol = self._get_tradingview_symbol(event.asset)
        buttons.append([
            InlineKeyboardButton("📊 График на TradingView", url=f"https://www.tradingview.com/chart/?symbol={tv_symbol}")
        ])
        
        return InlineKeyboardMarkup(buttons)
    
    def _get_tradingview_symbol(self, asset: str) -> str:
        """Получает символ для TradingView"""
        return f"BINANCE:{asset}USDT"
    
    def _strip_markdown(self, text: str) -> str:
        """Удаляет Markdown"""
        return text.replace("*", "").replace("_", "").replace("`", "")