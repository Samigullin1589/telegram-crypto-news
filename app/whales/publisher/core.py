# app/whales/publisher/core.py
"""
Whale Publisher - Core Implementation
"""

import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timezone
from pathlib import Path
import traceback

import telegram
from telegram import InlineKeyboardMarkup
from telegram.error import TelegramError, BadRequest, TimedOut, NetworkError

from app.config import config
from app.whales.normalize import WhaleEvent
from app.whales.publisher.metrics import PublishingMetrics
from app.whales.publisher.formatters import MessageFormatter
from app.whales.publisher.keyboards import KeyboardBuilder
from app.whales.publisher.utils import PublisherUtils


class WhalePublisher:
    """Универсальный издатель для всех типов контента"""
    
    def __init__(self):
        """Инициализация publisher"""
        
        self.bot = telegram.Bot(token=config.telegram.bot_token)
        self.chat_id = config.telegram.channel_id
        
        self.metrics = PublishingMetrics()
        
        self.last_publish = None
        self.min_interval = 2.0
        
        self.max_retries = 3
        self.retry_delay = 5
        
        print("📢 [PUBLISHER] Инициализирован")
    
    async def publish_whale_event(
        self,
        event: WhaleEvent,
        verdict: str,
        confidence: int,
        news: List[Dict],
        chart_path: Optional[str] = None
    ) -> bool:
        """Публикация события кита"""
        
        try:
            await self._respect_rate_limit()
            
            message = MessageFormatter.format_whale_event(event, verdict, confidence, news)
            keyboard = KeyboardBuilder.create_whale_keyboard(event, news)
            
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
    
    async def publish_trading_signal(
        self,
        message: str,
        parse_mode: str = 'HTML'
    ) -> bool:
        """Публикация торгового сигнала"""
        
        try:
            await self._respect_rate_limit()
            
            success = await self._publish_with_retry(
                message=message,
                keyboard=None,
                chart_path=None,
                parse_mode=parse_mode
            )
            
            if success:
                print(f"✅ [PUBLISH] Trading Signal")
            
            return success
        
        except Exception as e:
            print(f"❌ [PUBLISH] Ошибка: {e}")
            traceback.print_exc()
            self.metrics.record_attempt(False, "trading_signal_error")
            return False
    
    async def publish_message(
        self,
        message: str,
        parse_mode: str = 'HTML',
        keyboard: Optional[InlineKeyboardMarkup] = None,
        disable_preview: bool = True
    ) -> bool:
        """Универсальная публикация сообщения"""
        
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
    
    async def _publish_with_retry(
        self,
        message: str,
        keyboard: Optional[InlineKeyboardMarkup],
        chart_path: Optional[str],
        parse_mode: str = 'HTML',
        disable_preview: bool = True
    ) -> bool:
        """Публикация с retry логикой"""
        
        for attempt in range(self.max_retries):
            try:
                if chart_path and Path(chart_path).exists():
                    with open(chart_path, 'rb') as photo:
                        await self.bot.send_photo(
                            chat_id=self.chat_id,
                            photo=photo,
                            caption=message,
                            parse_mode=parse_mode,
                            reply_markup=keyboard
                        )
                else:
                    await self.bot.send_message(
                        chat_id=self.chat_id,
                        text=message,
                        parse_mode=parse_mode,
                        disable_web_page_preview=disable_preview,
                        reply_markup=keyboard
                    )
                
                self.metrics.record_attempt(True)
                return True
            
            except BadRequest as e:
                error_msg = str(e).lower()
                
                if 'parse' in error_msg or 'entities' in error_msg:
                    print(f"⚠️  [PUBLISH] Ошибка форматирования, без parse_mode...")
                    
                    message_plain = PublisherUtils.strip_html(message)
                    
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
                        print(f"⚠️  [PUBLISH] Plain text не удался: {e2}")
                
                elif 'too long' in error_msg:
                    print(f"⚠️  [PUBLISH] Сообщение слишком длинное, сокращаем...")
                    message = PublisherUtils.truncate_message(message, 4000)
                    continue
                
                else:
                    print(f"❌ [PUBLISH] BadRequest: {e}")
                    self.metrics.record_attempt(False, "bad_request")
                    return False
            
            except TimedOut:
                print(f"⚠️  [PUBLISH] Timeout, попытка {attempt + 1}/{self.max_retries}...")
                await asyncio.sleep(self.retry_delay * (attempt + 1))
                continue
            
            except NetworkError as e:
                print(f"⚠️  [PUBLISH] Network error, попытка {attempt + 1}/{self.max_retries}...")
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
        
        print(f"❌ [PUBLISH] Не удалось после {self.max_retries} попыток")
        self.metrics.record_attempt(False, "max_retries_exceeded")
        return False
    
    async def _respect_rate_limit(self):
        """Соблюдение rate limit"""
        
        if self.last_publish:
            elapsed = (datetime.now(timezone.utc) - self.last_publish).total_seconds()
            
            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                await asyncio.sleep(wait_time)