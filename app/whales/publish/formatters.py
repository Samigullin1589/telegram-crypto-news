# app/whales/publish/formatters.py
"""
Message Formatters for Whale Events
Handles HTML formatting, trade plans, keyboards
"""

import re
from typing import List, Dict, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.whales.normalize import WhaleEvent


class WhaleMessageFormatter:
    """Форматирование сообщений о whale событиях"""
    
    VERDICT_EMOJIS = {
        "bullish": "🟢",
        "bearish": "🔴",
        "neutral": "🟡"
    }
    
    DIRECTION_MAP = {
        "inflow_to_exchange": "📥 Приток на биржу",
        "outflow_to_cold": "🧊 Отток в холодное хранилище",
        "outflow_from_exchange": "📤 Отток с биржи",
        "bridge": "🌉 Мост между биржами",
        "internal": "🔄 Внутренний перевод",
        "unknown": "❓ Неизвестное направление"
    }
    
    PHASE_MAP = {
        "activation": "🔥 Активация",
        "transfer_cluster": "📊 Кластер переводов",
        "deposit_confirmed": "✅ Подтверждённый депозит",
        "execution": "⚡ Исполнение",
        "accumulation": "📈 Аккумуляция",
        "distribution": "📉 Распределение"
    }
    
    VERDICT_TEXT = {
        "bullish": "🐂 Бычий",
        "bearish": "🐻 Медвежий",
        "neutral": "🦀 Нейтральный"
    }
    
    @staticmethod
    def format_whale_message(
        event: WhaleEvent,
        verdict: str,
        confidence: int,
        news: List[Dict]
    ) -> str:
        """Форматирует полное сообщение о whale событии"""
        
        emoji = WhaleMessageFormatter.VERDICT_EMOJIS.get(verdict, "⚪")
        
        lines = [
            f"{emoji} <b>КРУПНЫЙ ПЕРЕВОД: {event.asset}</b>",
            ""
        ]
        
        lines.extend(WhaleMessageFormatter._format_fact_section(event))
        lines.extend(WhaleMessageFormatter._format_market_context(event))
        lines.extend(WhaleMessageFormatter._format_analysis(event))
        
        if event.history_hint and event.history_hint.d1h is not None:
            lines.extend(WhaleMessageFormatter._format_history(event))
        
        if hasattr(event, 'analytics') and event.analytics:
            lines.extend(WhaleMessageFormatter._format_analytics(event))
        
        lines.extend(WhaleMessageFormatter._format_trade_plan_section(event, verdict))
        lines.extend(WhaleMessageFormatter._format_verdict_section(verdict, confidence))
        
        if news:
            lines.extend(WhaleMessageFormatter._format_news_section(news))
        
        lines.extend(WhaleMessageFormatter._format_disclaimer())
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_fact_section(event: WhaleEvent) -> List[str]:
        """Форматирует секцию фактов"""
        lines = ["<b>💰 ФАКТ:</b>"]
        
        lines.append(
            f"• Сумма: <code>{event.amount_native:,.2f} {event.asset}</code> "
            f"≈ <b>${event.amount_usd:,.0f}</b>"
        )
        
        direction = WhaleMessageFormatter._format_direction(event)
        lines.append(f"• Направление: {direction}")
        
        lines.append(f"• Время: {event.tx_time_utc.strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append("")
        
        return lines
    
    @staticmethod
    def _format_direction(event: WhaleEvent) -> str:
        """Форматирует направление перевода"""
        base_direction = WhaleMessageFormatter.DIRECTION_MAP.get(
            event.direction, 
            "Перемещение"
        )
        
        to_labels = event.labels.get("to", [])
        if to_labels:
            best_label = max(to_labels, key=lambda l: l.confidence)
            if best_label.confidence >= 70 and best_label.details:
                base_direction += f" ({best_label.details})"
        
        return base_direction
    
    @staticmethod
    def _format_market_context(event: WhaleEvent) -> List[str]:
        """Форматирует контекст рынка"""
        lines = ["<b>📊 КОНТЕКСТ РЫНКА:</b>"]
        
        if not event.market:
            lines.append("• Данные недоступны")
            lines.append("")
            return lines
        
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
        return lines
    
    @staticmethod
    def _format_analysis(event: WhaleEvent) -> List[str]:
        """Форматирует секцию анализа"""
        lines = ["<b>🔍 АНАЛИЗ:</b>"]
        
        phase = WhaleMessageFormatter.PHASE_MAP.get(event.phase, event.phase.title())
        lines.append(f"• Фаза: {phase}")
        
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
        return lines
    
    @staticmethod
    def _format_history(event: WhaleEvent) -> List[str]:
        """Форматирует историческую справку"""
        lines = ["<b>📜 ИСТОРИЯ:</b>"]
        
        hint = event.history_hint
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
        lines.append(f"• В прошлый раз: {result}")
        
        if hint.comparable_ts:
            lines.append(f"  <i>(событие от {hint.comparable_ts[:10]})</i>")
        
        lines.append("")
        return lines
    
    @staticmethod
    def _format_analytics(event: WhaleEvent) -> List[str]:
        """Форматирует аналитику"""
        lines = ["<b>🧠 ANALYTICS:</b>"]
        
        sentiment = event.analytics.get('sentiment', {})
        if sentiment:
            lines.append(
                f"• Sentiment: {sentiment.get('label', 'Unknown')} "
                f"(score: {sentiment.get('score', 0):.2f})"
            )
        
        risk = event.analytics.get('risk', {})
        if risk:
            risk_score = risk.get('risk_score', 50)
            risk_emoji = "🟢" if risk_score < 40 else "🟡" if risk_score < 70 else "🔴"
            lines.append(f"• Risk Score: {risk_emoji} {risk_score}/100")
        
        lines.append("")
        return lines
    
    @staticmethod
    def _format_trade_plan_section(event: WhaleEvent, verdict: str) -> List[str]:
        """Форматирует торговый план"""
        lines = ["<b>📈 ТОРГОВЫЙ ПЛАН:</b>"]
        
        if verdict == "bearish":
            lines.extend([
                "• <b>Вход:</b> Продажа при пробое поддержки",
                "• <b>Stop-Loss:</b> Выше локального максимума",
                "• <b>Take-Profit:</b> Следующий уровень поддержки",
                "• <b>Инвалидация:</b> Возврат выше VWAP"
            ])
        elif verdict == "bullish":
            lines.extend([
                "• <b>Вход:</b> Покупка при удержании уровня",
                "• <b>Stop-Loss:</b> Ниже локального минимума",
                "• <b>Take-Profit:</b> Следующий уровень сопротивления",
                "• <b>Инвалидация:</b> Пробой локального минимума"
            ])
        else:
            lines.extend([
                "• <b>Стратегия:</b> Наблюдение",
                "• <b>Условие входа:</b> Подтверждение направления",
                "• <b>Инвалидация:</b> Отсутствие движения 2-4 часа"
            ])
        
        lines.append("")
        return lines
    
    @staticmethod
    def _format_verdict_section(verdict: str, confidence: int) -> List[str]:
        """Форматирует секцию вердикта"""
        verdict_text = WhaleMessageFormatter.VERDICT_TEXT.get(verdict, "⚪ Неопределённый")
        
        return [
            f"<b>🎯 ВЕРДИКТ:</b> {verdict_text}",
            f"<b>Уверенность:</b> {confidence}/100",
            f"<b>Горизонт:</b> 4-8 часов",
            ""
        ]
    
    @staticmethod
    def _format_news_section(news: List[Dict]) -> List[str]:
        """Форматирует секцию новостей"""
        lines = ["<b>📰 РЕЛЕВАНТНЫЕ НОВОСТИ:</b>"]
        
        for i, n in enumerate(news[:3], 1):
            title = n.get('title', 'Без заголовка')[:100]
            lines.append(f"{i}. {title}...")
        
        lines.append("")
        return lines
    
    @staticmethod
    def _format_disclaimer() -> List[str]:
        """Форматирует дисклеймер"""
        return [
            "─" * 40,
            "",
            "<b>⚠️ ДИСКЛЕЙМЕР:</b>",
            "<i>Это НЕ финансовая рекомендация. Информация предоставляется "
            "исключительно в образовательных целях. Возможна внутренняя "
            "консолидация, bridge-перевод или реорганизация. Всегда проводите "
            "собственное исследование (DYOR).</i>"
        ]
    
    @staticmethod
    def strip_html(text: str) -> str:
        """Удаляет HTML теги"""
        text = re.sub(r'<[^>]+>', '', text)
        
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        
        return text
    
    @staticmethod
    def truncate_message(message: str, max_length: int) -> str:
        """Сокращает сообщение до указанной длины"""
        if len(message) <= max_length:
            return message
        
        truncated = message[:max_length - 50]
        
        last_newline = truncated.rfind('\n')
        if last_newline > 0:
            truncated = truncated[:last_newline]
        
        truncated += "\n\n<i>... (сообщение сокращено)</i>"
        
        return truncated


class KeyboardBuilder:
    """Построение inline-клавиатур для whale событий"""
    
    COINGECKO_IDS = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "BNB": "binancecoin",
        "SOL": "solana",
        "MATIC": "matic-network",
        "AVAX": "avalanche-2",
        "DOT": "polkadot",
        "ADA": "cardano",
        "XRP": "ripple",
        "DOGE": "dogecoin",
        "SHIB": "shiba-inu",
        "LINK": "chainlink",
        "UNI": "uniswap",
        "AAVE": "aave",
        "ARB": "arbitrum",
        "OP": "optimism"
    }
    
    @staticmethod
    def create_whale_keyboard(
        event: WhaleEvent,
        news: List[Dict]
    ) -> InlineKeyboardMarkup:
        """Создаёт inline-клавиатуру для whale события"""
        buttons = []
        
        row1 = KeyboardBuilder._create_explorer_buttons(event)
        if row1:
            buttons.append(row1)
        
        if news:
            row2 = KeyboardBuilder._create_news_buttons(news)
            if row2:
                buttons.append(row2)
        
        buttons.append(KeyboardBuilder._create_chart_button(event))
        
        row4 = KeyboardBuilder._create_market_data_buttons(event)
        if row4:
            buttons.append(row4)
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def _create_explorer_buttons(event: WhaleEvent) -> List[InlineKeyboardButton]:
        """Создаёт кнопки для explorer ссылок"""
        buttons = []
        
        if event.links.get("tx"):
            buttons.append(InlineKeyboardButton("🔗 TX", url=event.links["tx"]))
        
        if event.links.get("from"):
            buttons.append(InlineKeyboardButton("📤 FROM", url=event.links["from"]))
        
        if event.links.get("to"):
            buttons.append(InlineKeyboardButton("📥 TO", url=event.links["to"]))
        
        return buttons
    
    @staticmethod
    def _create_news_buttons(news: List[Dict]) -> List[InlineKeyboardButton]:
        """Создаёт кнопки для новостей"""
        buttons = []
        
        for i, n in enumerate(news[:2], 1):
            title = f"📰 Новость {i}"
            buttons.append(InlineKeyboardButton(title, url=n["url"]))
        
        return buttons
    
    @staticmethod
    def _create_chart_button(event: WhaleEvent) -> List[InlineKeyboardButton]:
        """Создаёт кнопку графика TradingView"""
        tv_symbol = KeyboardBuilder._get_tradingview_symbol(event.asset, event.chain)
        
        return [
            InlineKeyboardButton(
                "📊 График TradingView",
                url=f"https://www.tradingview.com/chart/?symbol={tv_symbol}"
            )
        ]
    
    @staticmethod
    def _create_market_data_buttons(event: WhaleEvent) -> List[InlineKeyboardButton]:
        """Создаёт кнопки для market data"""
        buttons = []
        
        coingecko_id = KeyboardBuilder.COINGECKO_IDS.get(event.asset, event.asset.lower())
        buttons.append(InlineKeyboardButton(
            "📈 CoinGecko",
            url=f"https://www.coingecko.com/en/coins/{coingecko_id}"
        ))
        
        buttons.append(InlineKeyboardButton(
            "💹 CMC",
            url=f"https://coinmarketcap.com/currencies/{event.asset.lower()}/"
        ))
        
        return buttons
    
    @staticmethod
    def _get_tradingview_symbol(asset: str, chain: str) -> str:
        """Получает символ для TradingView"""
        if chain in ['ethereum', 'bsc', 'polygon']:
            return f"BINANCE:{asset}USDT"
        elif chain == 'solana':
            return f"RAYDIUM:{asset}USDT"
        else:
            return f"BINANCE:{asset}USDT"