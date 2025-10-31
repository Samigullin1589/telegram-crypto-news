"""
WHALE PUBLISHER v3.0
Unified publishing system for whale events and trading signals

ВОЗМОЖНОСТИ:
✅ Whale Event Publishing
✅ Trading Signal Publishing
✅ Alert Publishing
✅ HTML Formatting (более надёжный чем Markdown)
✅ Advanced Error Handling
✅ Rate Limiting Awareness
✅ Rich Formatting with Emojis
✅ Inline Keyboards
✅ Chart Integration
✅ News Integration
✅ Analytics Integration
✅ Multiple Fallback Strategies
"""

import asyncio
from typing import List, Dict, Optional, Union
from datetime import datetime, timezone
from pathlib import Path
import traceback

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError, BadRequest, TimedOut, NetworkError

from app import settings
from app.whales.normalize import WhaleEvent


class PublishingMetrics:
    """Метрики публикации"""
    
    def __init__(self):
        self.total_attempts = 0
        self.successful = 0
        self.failed = 0
        self.markdown_fallbacks = 0
        self.errors_by_type = {}
        self.last_publish_time = None
    
    def record_attempt(self, success: bool, error_type: Optional[str] = None):
        """Регистрация попытки публикации"""
        self.total_attempts += 1
        
        if success:
            self.successful += 1
            self.last_publish_time = datetime.now(timezone.utc)
        else:
            self.failed += 1
            if error_type:
                self.errors_by_type[error_type] = self.errors_by_type.get(error_type, 0) + 1
    
    def get_success_rate(self) -> float:
        """Получение процента успешных публикаций"""
        if self.total_attempts == 0:
            return 0.0
        return (self.successful / self.total_attempts) * 100


class WhalePublisher:
    """
    Универсальный издатель для всех типов контента
    
    Поддерживает:
    - Whale events (крупные перемещения)
    - Trading signals (торговые сигналы)
    - Alerts (системные уведомления)
    - Analytics reports (аналитические отчёты)
    """
    
    def __init__(self):
        """Инициализация publisher"""
        
        # Telegram bot
        self.bot = telegram.Bot(token=settings.TELEGRAM_TOKEN)
        self.chat_id = settings.CHAT_ID
        
        # Metrics
        self.metrics = PublishingMetrics()
        
        # Rate limiting awareness
        self.last_publish = None
        self.min_interval = 2.0  # Минимум 2 секунды между публикациями
        
        # Retry settings
        self.max_retries = 3
        self.retry_delay = 5
        
        print("📢 [PUBLISHER] Инициализирован")
    
    # ========================================================================
    # WHALE EVENT PUBLISHING
    # ========================================================================
    
    async def publish_whale_event(
        self,
        event: WhaleEvent,
        verdict: str,
        confidence: int,
        news: List[Dict],
        chart_path: Optional[str] = None
    ) -> bool:
        """
        Публикация события кита в канал
        
        Args:
            event: Событие перемещения
            verdict: Вердикт (bullish/bearish/neutral)
            confidence: Уверенность 0-100
            news: Список релевантных новостей
            chart_path: Путь к графику (опционально)
        
        Returns:
            bool: True если успешно опубликовано
        """
        
        try:
            # Rate limiting
            await self._respect_rate_limit()
            
            # Форматируем сообщение
            message = self._format_whale_message(event, verdict, confidence, news)
            
            # Создаём клавиатуру
            keyboard = self._create_whale_keyboard(event, news)
            
            # Публикуем
            success = await self._publish_with_retry(
                message=message,
                keyboard=keyboard,
                chart_path=chart_path,
                parse_mode='HTML'
            )
            
            if success:
                print(f"✅ [PUBLISH] Whale Event: {event.asset} ${event.amount_usd:,.0f}")
            else:
                print(f"❌ [PUBLISH] Failed: {event.asset}")
            
            return success
        
        except Exception as e:
            print(f"❌ [PUBLISH] Критическая ошибка: {e}")
            traceback.print_exc()
            self.metrics.record_attempt(False, "critical_error")
            return False
    
    def _format_whale_message(
        self,
        event: WhaleEvent,
        verdict: str,
        confidence: int,
        news: List[Dict]
    ) -> str:
        """
        Форматирует сообщение о whale событии в HTML
        
        HTML более надёжен чем Markdown и поддерживает больше возможностей
        """
        
        # Эмодзи для вердикта
        verdict_emoji = {
            "bullish": "🟢",
            "bearish": "🔴",
            "neutral": "🟡"
        }
        
        emoji = verdict_emoji.get(verdict, "⚪")
        
        # Заголовок
        lines = [
            f"{emoji} <b>КРУПНЫЙ ПЕРЕВОД: {event.asset}</b>",
            ""
        ]
        
        # Основная информация
        lines.append("<b>💰 ФАКТ:</b>")
        lines.append(
            f"• Сумма: <code>{event.amount_native:,.2f} {event.asset}</code> "
            f"≈ <b>${event.amount_usd:,.0f}</b>"
        )
        lines.append(f"• Направление: {self._format_direction(event)}")
        lines.append(f"• Время: {event.tx_time_utc.strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append("")
        
        # Контекст рынка
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
        
        # Фаза и кластер
        lines.append("<b>🔍 АНАЛИЗ:</b>")
        lines.append(f"• Фаза: {self._format_phase(event)}")
        
        if event.cluster:
            lines.append(
                f"• Кластер: {event.cluster.tx_in_window} транзакций "
                f"за {event.cluster.window_minutes} минут"
            )
            if event.cluster.total_amount_native:
                lines.append(
                    f"• Общая сумма кластера: "
                    f"{event.cluster.total_amount_native:,.2f} {event.asset}"
                )
        
        lines.append("")
        
        # Историческая справка
        if event.history_hint and event.history_hint.d1h is not None:
            lines.append("<b>📜 ИСТОРИЯ:</b>")
            lines.append(f"• В прошлый раз: {self._format_history(event.history_hint)}")
            lines.append("")
        
        # Analytics (если доступны)
        if hasattr(event, 'analytics') and event.analytics:
            lines.append("<b>🧠 ANALYTICS:</b>")
            
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
        
        # Торговый план
        lines.append("<b>📈 ТОРГОВЫЙ ПЛАН:</b>")
        trade_plan = self._generate_trade_plan(event, verdict)
        for plan_line in trade_plan:
            lines.append(f"• {plan_line}")
        lines.append("")
        
        # Вердикт
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
        
        # Новости
        if news:
            lines.append("<b>📰 РЕЛЕВАНТНЫЕ НОВОСТИ:</b>")
            for i, n in enumerate(news[:3], 1):
                title = n.get('title', 'Без заголовка')[:100]
                lines.append(f"{i}. {title}...")
            lines.append("")
        
        # Дисклеймер
        lines.append("─" * 40)
        lines.append("")
        lines.append("<b>⚠️ ДИСКЛЕЙМЕР:</b>")
        lines.append(
            "<i>Это НЕ финансовая рекомендация. Информация предоставляется "
            "исключительно в образовательных целях. Возможна внутренняя "
            "консолидация, bridge-перевод или реорганизация. Всегда проводите "
            "собственное исследование (DYOR) и консультируйтесь с финансовым "
            "советником перед принятием инвестиционных решений.</i>"
        )
        
        return "\n".join(lines)
    
    def _format_direction(self, event: WhaleEvent) -> str:
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
        
        # Добавляем детали из labels
        to_labels = event.labels.get("to", [])
        if to_labels:
            best_label = max(to_labels, key=lambda l: l.confidence)
            if best_label.confidence >= 70 and best_label.details:
                base_direction += f" ({best_label.details})"
        
        return base_direction
    
    def _format_phase(self, event: WhaleEvent) -> str:
        """Форматирует фазу движения"""
        
        phase_map = {
            "activation": "🔥 Активация (первое движение)",
            "transfer_cluster": "📊 Кластер переводов",
            "deposit_confirmed": "✅ Подтверждённый депозит",
            "execution": "⚡ Исполнение на рынке",
            "accumulation": "📈 Аккумуляция",
            "distribution": "📉 Распределение"
        }
        
        return phase_map.get(event.phase, event.phase.title())
    
    def _format_history(self, hint) -> str:
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
    
    def _generate_trade_plan(self, event: WhaleEvent, verdict: str) -> List[str]:
        """Генерирует торговый план"""
        
        plan = []
        
        if verdict == "bearish":
            plan.extend([
                "<b>Вход:</b> Продажа при пробое поддержки (M5-M15)",
                "<b>Stop-Loss:</b> Выше локального максимума + спред",
                "<b>Take-Profit:</b> Следующий уровень поддержки",
                "<b>Инвалидация:</b> Возврат выше VWAP(M5)"
            ])
        
        elif verdict == "bullish":
            plan.extend([
                "<b>Вход:</b> Покупка при удержании уровня (M5-M15)",
                "<b>Stop-Loss:</b> Ниже локального минимума + спред",
                "<b>Take-Profit:</b> Следующий уровень сопротивления",
                "<b>Инвалидация:</b> Пробой локального минимума"
            ])
        
        else:
            plan.extend([
                "<b>Стратегия:</b> Наблюдение, дожидаемся подтверждения",
                "<b>Условие входа:</b> Подтверждение направления на объёме",
                "<b>Инвалидация:</b> Отсутствие движения 2-4 часа"
            ])
        
        return plan
    
    def _create_whale_keyboard(
        self,
        event: WhaleEvent,
        news: List[Dict]
    ) -> InlineKeyboardMarkup:
        """Создаёт inline-клавиатуру для whale события"""
        
        buttons = []
        
        # Первый ряд: ссылки на транзакцию и адреса
        row1 = []
        
        if event.links.get("tx"):
            row1.append(InlineKeyboardButton("🔗 TX", url=event.links["tx"]))
        
        if event.links.get("from"):
            row1.append(InlineKeyboardButton("📤 FROM", url=event.links["from"]))
        
        if event.links.get("to"):
            row1.append(InlineKeyboardButton("📥 TO", url=event.links["to"]))
        
        if row1:
            buttons.append(row1)
        
        # Второй ряд: новости
        if news:
            row2 = []
            for i, n in enumerate(news[:2], 1):
                title = f"📰 Новость {i}"
                row2.append(InlineKeyboardButton(title, url=n["url"]))
            buttons.append(row2)
        
        # Третий ряд: график TradingView
        tv_symbol = self._get_tradingview_symbol(event.asset, event.chain)
        buttons.append([
            InlineKeyboardButton(
                "📊 График на TradingView",
                url=f"https://www.tradingview.com/chart/?symbol={tv_symbol}"
            )
        ])
        
        # Четвёртый ряд: дополнительные ссылки
        row4 = []
        
        # CoinGecko
        coingecko_id = self._get_coingecko_id(event.asset)
        if coingecko_id:
            row4.append(InlineKeyboardButton(
                "📈 CoinGecko",
                url=f"https://www.coingecko.com/en/coins/{coingecko_id}"
            ))
        
        # CoinMarketCap
        row4.append(InlineKeyboardButton(
            "💹 CMC",
            url=f"https://coinmarketcap.com/currencies/{event.asset.lower()}/"
        ))
        
        if row4:
            buttons.append(row4)
        
        return InlineKeyboardMarkup(buttons)
    
    # ========================================================================
    # TRADING SIGNAL PUBLISHING
    # ========================================================================
    
    async def publish_trading_signal(
        self,
        message: str,
        parse_mode: str = 'HTML'
    ) -> bool:
        """
        Публикация торгового сигнала
        
        Args:
            message: Отформатированное сообщение (уже содержит все детали)
            parse_mode: Режим парсинга ('HTML' или 'Markdown')
        
        Returns:
            bool: True если успешно опубликовано
        """
        
        try:
            # Rate limiting
            await self._respect_rate_limit()
            
            # Публикуем
            success = await self._publish_with_retry(
                message=message,
                keyboard=None,
                chart_path=None,
                parse_mode=parse_mode
            )
            
            if success:
                print(f"✅ [PUBLISH] Trading Signal")
            else:
                print(f"❌ [PUBLISH] Failed: Trading Signal")
            
            return success
        
        except Exception as e:
            print(f"❌ [PUBLISH] Ошибка публикации trading signal: {e}")
            traceback.print_exc()
            self.metrics.record_attempt(False, "trading_signal_error")
            return False
    
    # ========================================================================
    # GENERIC PUBLISHING
    # ========================================================================
    
    async def publish_message(
        self,
        message: str,
        parse_mode: str = 'HTML',
        keyboard: Optional[InlineKeyboardMarkup] = None,
        disable_preview: bool = True
    ) -> bool:
        """
        Универсальная публикация сообщения
        
        Args:
            message: Текст сообщения
            parse_mode: Режим парсинга
            keyboard: Inline клавиатура (опционально)
            disable_preview: Отключить превью ссылок
        
        Returns:
            bool: True если успешно
        """
        
        try:
            await self._respect_rate_limit()
            
            return await self._publish_with_retry(
                message=message,
                keyboard=keyboard,
                chart_path=None,
                parse_mode=parse_mode,
                disable_preview=disable_preview
            )
        
        except Exception as e:
            print(f"❌ [PUBLISH] Ошибка: {e}")
            self.metrics.record_attempt(False, "generic_error")
            return False
    
    # ========================================================================
    # INTERNAL HELPERS
    # ========================================================================
    
    async def _publish_with_retry(
        self,
        message: str,
        keyboard: Optional[InlineKeyboardMarkup],
        chart_path: Optional[str],
        parse_mode: str = 'HTML',
        disable_preview: bool = True
    ) -> bool:
        """
        Публикация с retry логикой и fallback стратегиями
        
        Стратегии fallback:
        1. Попытка с заданным parse_mode
        2. Попытка без parse_mode (plain text)
        3. Попытка без клавиатуры
        4. Сокращённое сообщение
        """
        
        for attempt in range(self.max_retries):
            try:
                # Попытка публикации
                if chart_path and Path(chart_path).exists():
                    # С изображением
                    with open(chart_path, 'rb') as photo:
                        await self.bot.send_photo(
                            chat_id=self.chat_id,
                            photo=photo,
                            caption=message,
                            parse_mode=parse_mode,
                            reply_markup=keyboard
                        )
                else:
                    # Только текст
                    await self.bot.send_message(
                        chat_id=self.chat_id,
                        text=message,
                        parse_mode=parse_mode,
                        disable_web_page_preview=disable_preview,
                        reply_markup=keyboard
                    )
                
                # Успех
                self.metrics.record_attempt(True)
                return True
            
            except BadRequest as e:
                error_msg = str(e).lower()
                
                # Проблема с форматированием
                if 'parse' in error_msg or 'entities' in error_msg:
                    print(f"⚠️ [PUBLISH] Ошибка форматирования, попытка без parse_mode...")
                    
                    # Убираем HTML теги
                    message_plain = self._strip_html(message)
                    
                    try:
                        if chart_path and Path(chart_path).exists():
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
                                disable_web_page_preview=disable_preview,
                                reply_markup=keyboard
                            )
                        
                        self.metrics.record_attempt(True)
                        self.metrics.markdown_fallbacks += 1
                        print("✅ [PUBLISH] Опубликовано без форматирования")
                        return True
                    
                    except Exception as e2:
                        print(f"⚠️ [PUBLISH] Plain text также не удался: {e2}")
                
                # Слишком длинное сообщение
                elif 'too long' in error_msg or 'message is too long' in error_msg:
                    print(f"⚠️ [PUBLISH] Сообщение слишком длинное, сокращаем...")
                    message = self._truncate_message(message, 4000)
                    continue
                
                else:
                    print(f"❌ [PUBLISH] BadRequest: {e}")
                    self.metrics.record_attempt(False, "bad_request")
                    return False
            
            except TimedOut:
                print(f"⚠️ [PUBLISH] Timeout, попытка {attempt + 1}/{self.max_retries}...")
                await asyncio.sleep(self.retry_delay * (attempt + 1))
                continue
            
            except NetworkError as e:
                print(f"⚠️ [PUBLISH] Network error: {e}, попытка {attempt + 1}/{self.max_retries}...")
                await asyncio.sleep(self.retry_delay * (attempt + 1))
                continue
            
            except TelegramError as e:
                print(f"❌ [PUBLISH] Telegram error: {e}")
                self.metrics.record_attempt(False, "telegram_error")
                return False
            
            except Exception as e:
                print(f"❌ [PUBLISH] Неожиданная ошибка: {e}")
                traceback.print_exc()
                self.metrics.record_attempt(False, "unexpected_error")
                return False
        
        # Все попытки исчерпаны
        print(f"❌ [PUBLISH] Не удалось опубликовать после {self.max_retries} попыток")
        self.metrics.record_attempt(False, "max_retries_exceeded")
        return False
    
    async def _respect_rate_limit(self):
        """Соблюдение rate limit между публикациями"""
        
        if self.last_publish:
            elapsed = (datetime.now(timezone.utc) - self.last_publish).total_seconds()
            
            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                await asyncio.sleep(wait_time)
        
        self.last_publish = datetime.now(timezone.utc)
    
    def _strip_html(self, text: str) -> str:
        """Удаляет HTML теги"""
        
        import re
        
        # Удаляем HTML теги
        text = re.sub(r'<[^>]+>', '', text)
        
        # Декодируем HTML entities
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        
        return text
    
    def _truncate_message(self, message: str, max_length: int) -> str:
        """Сокращает сообщение до заданной длины"""
        
        if len(message) <= max_length:
            return message
        
        # Обрезаем с запасом для "..."
        truncated = message[:max_length - 50]
        
        # Находим последний перевод строки
        last_newline = truncated.rfind('\n')
        if last_newline > 0:
            truncated = truncated[:last_newline]
        
        truncated += "\n\n<i>... (сообщение сокращено)</i>"
        
        return truncated
    
    def _get_tradingview_symbol(self, asset: str, chain: str) -> str:
        """Получает символ для TradingView"""
        
        # Для большинства активов используем Binance
        if chain in ['ethereum', 'bsc', 'polygon']:
            return f"BINANCE:{asset}USDT"
        elif chain == 'solana':
            return f"RAYDIUM:{asset}USDT"
        else:
            return f"BINANCE:{asset}USDT"
    
    def _get_coingecko_id(self, asset: str) -> Optional[str]:
        """Получает CoinGecko ID для актива"""
        
        # Маппинг популярных активов
        mapping = {
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
        
        return mapping.get(asset, asset.lower())
    
    # ========================================================================
    # METRICS & STATS
    # ========================================================================
    
    def get_stats(self) -> Dict:
        """Получение статистики публикаций"""
        
        return {
            "total_attempts": self.metrics.total_attempts,
            "successful": self.metrics.successful,
            "failed": self.metrics.failed,
            "success_rate": self.metrics.get_success_rate(),
            "markdown_fallbacks": self.metrics.markdown_fallbacks,
            "errors_by_type": dict(self.metrics.errors_by_type),
            "last_publish_time": self.metrics.last_publish_time.isoformat() if self.metrics.last_publish_time else None
        }
    
    def print_stats(self):
        """Вывод статистики"""
        
        stats = self.get_stats()
        
        print("\n" + "="*80)
        print("📊 PUBLISHER STATISTICS")
        print("="*80)
        print(f"Total Attempts: {stats['total_attempts']}")
        print(f"Successful: {stats['successful']}")
        print(f"Failed: {stats['failed']}")
        print(f"Success Rate: {stats['success_rate']:.1f}%")
        print(f"Markdown Fallbacks: {stats['markdown_fallbacks']}")
        
        if stats['errors_by_type']:
            print("\nErrors by Type:")
            for error_type, count in stats['errors_by_type'].items():
                print(f"  • {error_type}: {count}")
        
        print("="*80 + "\n")