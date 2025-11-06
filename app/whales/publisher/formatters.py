# app/whales/publisher/formatters.py
"""
Message Formatters
"""

from typing import List, Dict, Optional
from app.whales.normalize import WhaleEvent


class MessageFormatter:
    """Форматирование сообщений"""
    
    @staticmethod
    def format_whale_event(
        event: WhaleEvent,
        verdict: str,
        confidence: int,
        news: List[Dict]
    ) -> str:
        """Форматирует сообщение о whale событии в HTML"""
        
        verdict_emoji = {
            "bullish": "🟢",
            "bearish": "🔴",
            "neutral": "🟡"
        }
        
        emoji = verdict_emoji.get(verdict, "⚪")
        
        lines = [
            f"{emoji} <b>КРУПНЫЙ ПЕРЕВОД: {event.asset}</b>",
            ""
        ]
        
        lines.append("<b>💰 ФАКТ:</b>")
        lines.append(
            f"• Сумма: <code>{event.amount_native:,.2f} {event.asset}</code> "
            f"≈ <b>${event.amount_usd:,.0f}</b>"
        )
        lines.append(f"• Направление: {MessageFormatter._format_direction(event)}")
        lines.append(f"• Время: {event.tx_time_utc.strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append("")
        
        lines.append("<b>📊 КОНТЕКСТ РЫНКА:</b>")
        
        if event.market:
            if event.market.price_usd:
                lines.append(f"• Цена: ${event.market.price_usd:,.2f}")
            
            if event.market.volume_24h_usd:
                size_rel = (event.amount_usd / event.market.volume_24h_usd) * 100
                lines.append(
                    f"• 24h Volume: ${event.market.volume_24h_usd/1e6:.1f}M "
                    f"(перевод {size_rel:.2f}%)"
                )
            
            if event.market.price_change_24h_pct is not None:
                change_emoji = "📈" if event.market.price_change_24h_pct > 0 else "📉"
                lines.append(
                    f"• 24h Change: {change_emoji} "
                    f"{event.market.price_change_24h_pct:+.2f}%"
                )
        
        lines.append("")
        
        lines.append("<b>🔍 АНАЛИЗ:</b>")
        lines.append(f"• Фаза: {MessageFormatter._format_phase(event)}")
        
        if event.cluster:
            lines.append(
                f"• Кластер: {event.cluster.tx_in_window} транзакций "
                f"за {event.cluster.window_minutes} минут"
            )
            if event.cluster.total_amount_native:
                lines.append(
                    f"• Общая сумма: "
                    f"{event.cluster.total_amount_native:,.2f} {event.asset}"
                )
        
        lines.append("")
        
        if event.history_hint and event.history_hint.d1h is not None:
            lines.append("<b>📜 ИСТОРИЯ:</b>")
            lines.append(f"• В прошлый раз: {MessageFormatter._format_history(event.history_hint)}")
            lines.append("")
        
        lines.append("<b>📈 ТОРГОВЫЙ ПЛАН:</b>")
        trade_plan = MessageFormatter._generate_trade_plan(event, verdict)
        for plan_line in trade_plan:
            lines.append(f"• {plan_line}")
        lines.append("")
        
        verdict_map = {
            "bullish": "🐂 Бычий",
            "bearish": "🐻 Медвежий",
            "neutral": "🦀 Нейтральный"
        }
        
        verdict_text = verdict_map.get(verdict, "⚪ Неопределённый")
        
        lines.append(f"<b>🎯 ВЕРДИКТ:</b> {verdict_text}")
        lines.append(f"<b>Уверенность:</b> {confidence}/100")
        lines.append(f"<b>Горизонт:</b> 4-8 часов")
        lines.append("")
        
        if news:
            lines.append("<b>📰 РЕЛЕВАНТНЫЕ НОВОСТИ:</b>")
            for i, n in enumerate(news[:3], 1):
                title = n.get('title', 'Без заголовка')[:100]
                lines.append(f"{i}. {title}...")
            lines.append("")
        
        lines.append("─" * 40)
        lines.append("")
        lines.append("<b>⚠️  ДИСКЛЕЙМЕР:</b>")
        lines.append(
            "<i>Это НЕ финансовая рекомендация. Информация предоставляется "
            "исключительно в образовательных целях. Возможна внутренняя "
            "консолидация, bridge-перевод или реорганизация. Всегда проводите "
            "собственное исследование (DYOR).</i>"
        )
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_direction(event: WhaleEvent) -> str:
        """Форматирует направление перевода"""
        
        direction_map = {
            "inflow_to_exchange": "📥 Приток на биржу",
            "outflow_to_cold": "🧊 Отток в холодное хранилище",
            "outflow_from_exchange": "📤 Отток с биржи",
            "bridge": "🌉 Мост между биржами",
            "internal": "🔄 Внутренний перевод",
            "unknown": "❓ Неизвестное направление"
        }
        
        base_direction = direction_map.get(event.direction, "Перемещение")
        
        to_labels = event.labels.get("to", [])
        if to_labels:
            best_label = max(to_labels, key=lambda l: l.confidence)
            if best_label.confidence >= 70 and best_label.details:
                base_direction += f" ({best_label.details})"
        
        return base_direction
    
    @staticmethod
    def _format_phase(event: WhaleEvent) -> str:
        """Форматирует фазу движения"""
        
        phase_map = {
            "activation": "🔥 Активация",
            "transfer_cluster": "📊 Кластер переводов",
            "deposit_confirmed": "✅ Подтверждённый депозит",
            "execution": "⚡ Исполнение",
            "accumulation": "📈 Аккумуляция",
            "distribution": "📉 Распределение"
        }
        
        return phase_map.get(event.phase, event.phase.title())
    
    @staticmethod
    def _format_history(hint) -> str:
        """Форматирует историческую справку"""
        
        parts = []
        
        if hint.d1h is not None:
            emoji = "🟢" if hint.d1h > 0 else "🔴" if hint.d1h < 0 else "⚪"
            parts.append(f"{emoji} {hint.d1h:+.1f}% (1ч)")
        
        if hint.d4h is not None:
            emoji = "🟢" if hint.d4h > 0 else "🔴" if hint.d4h < 0 else "⚪"
            parts.append(f"{emoji} {hint.d4h:+.1f}% (4ч)")
        
        if hint.d24h is not None:
            emoji = "🟢" if hint.d24h > 0 else "🔴" if hint.d24h < 0 else "⚪"
            parts.append(f"{emoji} {hint.d24h:+.1f}% (24ч)")
        
        result = " → ".join(parts)
        
        if hint.comparable_ts:
            result += f"\n  <i>(событие от {hint.comparable_ts[:10]})</i>"
        
        return result
    
    @staticmethod
    def _generate_trade_plan(event: WhaleEvent, verdict: str) -> List[str]:
        """Генерирует торговый план"""
        
        plan = []
        
        if verdict == "bearish":
            plan.extend([
                "<b>Вход:</b> Продажа при пробое поддержки",
                "<b>Stop-Loss:</b> Выше локального максимума",
                "<b>Take-Profit:</b> Следующий уровень поддержки",
                "<b>Инвалидация:</b> Возврат выше VWAP"
            ])
        
        elif verdict == "bullish":
            plan.extend([
                "<b>Вход:</b> Покупка при удержании уровня",
                "<b>Stop-Loss:</b> Ниже локального минимума",
                "<b>Take-Profit:</b> Следующий уровень сопротивления",
                "<b>Инвалидация:</b> Пробой локального минимума"
            ])
        
        else:
            plan.extend([
                "<b>Стратегия:</b> Наблюдение",
                "<b>Условие входа:</b> Подтверждение направления",
                "<b>Инвалидация:</b> Отсутствие движения 2-4 часа"
            ])
        
        return plan


__all__ = ['MessageFormatter']