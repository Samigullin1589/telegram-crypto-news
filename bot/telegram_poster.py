# bot/telegram_poster.py
# ИСПРАВЛЕНО: Добавлена поддержка обоих форматов параметров
import asyncio
import re
from typing import Optional, Dict
from datetime import datetime
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError, RetryAfter, TimedOut, NetworkError
from .config import config


class PostingMetrics:
    """Метрики успешности постинга"""
    
    def __init__(self):
        self.total_attempts = 0
        self.successful_posts = 0
        self.failed_posts = 0
        self.posts_with_images = 0
        self.posts_without_images = 0
        self.markdown_errors = 0
        self.network_errors = 0
        self.retry_count = 0
    
    @property
    def success_rate(self) -> float:
        """Процент успешных публикаций"""
        if self.total_attempts == 0:
            return 0.0
        return (self.successful_posts / self.total_attempts) * 100
    
    def print_summary(self):
        """Вывод статистики"""
        print("\n📊 [TELEGRAM STATS] Статистика публикаций:")
        print(f"  Всего попыток: {self.total_attempts}")
        print(f"  Успешно: {self.successful_posts} ({self.success_rate:.1f}%)")
        print(f"  Неудачно: {self.failed_posts}")
        print(f"  С изображениями: {self.posts_with_images}")
        print(f"  Без изображений: {self.posts_without_images}")
        print(f"  Ошибок Markdown: {self.markdown_errors}")
        print(f"  Сетевых ошибок: {self.network_errors}")
        print(f"  Повторов (retry): {self.retry_count}")


class MessageSanitizer:
    """Умная санитизация сообщений для Telegram"""
    
    # Максимальные лимиты Telegram
    MAX_MESSAGE_LENGTH = 4096
    MAX_CAPTION_LENGTH = 1024
    
    @staticmethod
    def sanitize_markdown(text: str) -> str:
        """
        Продвинутая санитизация Markdown для Telegram
        Удаляет/исправляет проблемные конструкции
        """
        if not text:
            return text
        
        # 1. Удаляем HTML теги (если случайно попали)
        text = re.sub(r'<[^>]+>', '', text)
        
        # 2. Исправляем множественные звёздочки (***text*** -> **text**)
        text = re.sub(r'\*{3,}', '**', text)
        
        # 3. Удаляем пустые bold/italic (****, __, etc)
        text = re.sub(r'\*\*\s*\*\*', '', text)
        text = re.sub(r'__\s*__', '', text)
        text = re.sub(r'~~\s*~~', '', text)
        
        # 4. Экранируем одиночные спецсимволы после букв/цифр
        # Проблема: слово* или цифра_ становятся началом форматирования
        text = re.sub(r'(\w)([*_`])([\s.,!?])', r'\1\\\2\3', text)
        
        # 5. Удаляем форматирование внутри URLs (не работает в Telegram)
        text = re.sub(r'\[(.*?)\]\((.*?)\)', lambda m: f"[{m.group(1)}]({m.group(2)})", text)
        
        # 6. Проверяем баланс markdown символов
        for char in ['*', '_', '`']:
            count = text.count(char)
            if count % 2 != 0:
                # Удаляем последний нечётный символ
                pos = text.rfind(char)
                if pos != -1:
                    text = text[:pos] + text[pos + 1:]
        
        return text.strip()
    
    @staticmethod
    def strip_markdown(text: str) -> str:
        """Полное удаление Markdown (для fallback режима)"""
        if not text:
            return text
        
        # Удаляем все markdown символы
        text = re.sub(r'[*_`~\[\]()]', '', text)
        text = re.sub(r'\s+', ' ', text)  # Убираем лишние пробелы
        
        return text.strip()
    
    @staticmethod
    def truncate(text: str, max_length: int, suffix: str = '...') -> str:
        """Умная обрезка текста с сохранением слов"""
        if len(text) <= max_length:
            return text
        
        # Обрезаем с запасом для суффикса
        truncated = text[:max_length - len(suffix)]
        
        # Обрезаем по последнему пробелу чтобы не разрывать слова
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.8:  # Не обрезаем слишком много
            truncated = truncated[:last_space]
        
        return truncated + suffix
    
    @classmethod
    def prepare_message(cls, text: str, is_caption: bool = False) -> str:
        """
        Полная подготовка сообщения к отправке
        
        Args:
            text: Исходный текст
            is_caption: True если это caption для фото (более строгий лимит)
        """
        # Санитизация
        text = cls.sanitize_markdown(text)
        
        # Обрезка если нужно
        max_length = cls.MAX_CAPTION_LENGTH if is_caption else cls.MAX_MESSAGE_LENGTH
        if len(text) > max_length:
            text = cls.truncate(text, max_length)
        
        return text


class TelegramPoster:
    """
    Умный Telegram poster с retry механизмом и детальной статистикой
    
    ИСПРАВЛЕНО: Поддержка обоих форматов параметров:
    - post(message, link, image_url) - новый формат
    - post(text=..., link=..., image_data=...) - старый формат из processor.py
    """
    
    def __init__(self):
        self.bot = telegram.Bot(token=config.TELEGRAM_BOT_TOKEN)
        self.channel_id = config.TELEGRAM_CHANNEL_ID
        self.metrics = PostingMetrics()
        self.sanitizer = MessageSanitizer()
        
        # Rate limiting
        self._last_post_time = 0
        self._min_post_interval = 3.0  # Минимум 3 секунды между постами
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delays = [5, 10, 20]  # Задержки между retry
        
        print(f"📱 [TELEGRAM] Poster инициализирован. Канал: {self.channel_id}")
    
    async def post(
        self,
        message: Optional[str] = None,
        link: Optional[str] = None,
        image_url: Optional[str] = None,
        # ИСПРАВЛЕНО: Добавлена поддержка старых параметров из processor.py
        text: Optional[str] = None,
        image_data: Optional[bytes] = None
    ) -> bool:
        """
        Основной метод публикации с умным retry и fallback
        
        ИСПРАВЛЕНО: Поддержка обоих форматов параметров!
        
        Args:
            message: Текст сообщения (новый формат)
            link: Ссылка на первоисточник
            image_url: URL изображения (новый формат) - НЕ ИСПОЛЬЗУЕТСЯ, оставлен для совместимости
            text: Текст сообщения (старый формат из processor.py)
            image_data: Байты изображения (старый формат из processor.py)
        
        Returns:
            True если успешно опубликовано
        """
        # ИСПРАВЛЕНО: Маппинг параметров
        # Если используется старый формат (text=..., image_data=...), конвертируем в новый
        final_message = message or text
        final_link = link
        
        # ВАЖНО: image_data это bytes, а image_url это str
        # Если передан image_data (bytes) - используем его
        # Если передан image_url (str) - игнорируем (API Telegram требует либо bytes либо URL отдельно)
        final_image_data = image_data  # bytes или None
        
        if not final_message or not final_link:
            print("❌ [POST] Отсутствуют обязательные параметры (message/text и link)")
            return False
        
        self.metrics.total_attempts += 1
        
        # Rate limiting
        await self._rate_limit()
        
        # Создаём кнопку
        keyboard = [[InlineKeyboardButton("🔗 Читать первоисточник", url=final_link)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Подготовка сообщения
        is_caption = bool(final_image_data)
        prepared_message = self.sanitizer.prepare_message(final_message, is_caption=is_caption)
        
        # Стратегия публикации
        strategies = [
            ('markdown_with_image', self._post_with_markdown_and_image),
            ('markdown_without_image', self._post_with_markdown_text_only),
            ('plain_with_image', self._post_plain_with_image),
            ('plain_text', self._post_plain_text_only),
        ]
        
        for strategy_name, strategy_func in strategies:
            success = await strategy_func(
                prepared_message,
                final_image_data,  # ИСПРАВЛЕНО: передаем bytes вместо URL
                reply_markup
            )
            
            if success:
                self.metrics.successful_posts += 1
                if final_image_data:
                    self.metrics.posts_with_images += 1
                else:
                    self.metrics.posts_without_images += 1
                
                print(f"✅ [POST] Успешно ({strategy_name}): {final_link[:60]}")
                return True
            
            # Если это не последняя стратегия - пробуем следующую
            if strategy_name != strategies[-1][0]:
                print(f"🔄 [POST] Пробую следующую стратегию...")
                await asyncio.sleep(2)
        
        # Все стратегии провалились
        self.metrics.failed_posts += 1
        print(f"❌ [POST] ВСЕ СТРАТЕГИИ ПРОВАЛИЛИСЬ: {final_link[:60]}")
        return False
    
    async def _post_with_markdown_and_image(
        self,
        message: str,
        image_data: Optional[bytes],  # ИСПРАВЛЕНО: bytes вместо str
        reply_markup: InlineKeyboardMarkup
    ) -> bool:
        """Стратегия 1: Markdown + изображение"""
        if not image_data:
            return False
        
        try:
            # ИСПРАВЛЕНО: передаем bytes напрямую
            await self._send_with_retry(
                lambda: self.bot.send_photo(
                    chat_id=self.channel_id,
                    photo=image_data,  # bytes
                    caption=message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            )
            return True
            
        except telegram.error.BadRequest as e:
            error_str = str(e).lower()
            if 'parse' in error_str or 'markdown' in error_str or 'entities' in error_str:
                self.metrics.markdown_errors += 1
                print(f"⚠️  [POST] Markdown ошибка: {e}")
            return False
        except Exception as e:
            print(f"⚠️  [POST] Ошибка (markdown+image): {type(e).__name__}")
            return False
    
    async def _post_with_markdown_text_only(
        self,
        message: str,
        image_data: Optional[bytes],  # ИСПРАВЛЕНО: bytes
        reply_markup: InlineKeyboardMarkup
    ) -> bool:
        """Стратегия 2: Markdown без изображения"""
        try:
            await self._send_with_retry(
                lambda: self.bot.send_message(
                    chat_id=self.channel_id,
                    text=message,
                    parse_mode='Markdown',
                    disable_web_page_preview=True,
                    reply_markup=reply_markup
                )
            )
            return True
            
        except telegram.error.BadRequest as e:
            error_str = str(e).lower()
            if 'parse' in error_str or 'markdown' in error_str:
                self.metrics.markdown_errors += 1
                print(f"⚠️  [POST] Markdown ошибка (text): {e}")
            return False
        except Exception as e:
            print(f"⚠️  [POST] Ошибка (markdown text): {type(e).__name__}")
            return False
    
    async def _post_plain_with_image(
        self,
        message: str,
        image_data: Optional[bytes],  # ИСПРАВЛЕНО: bytes
        reply_markup: InlineKeyboardMarkup
    ) -> bool:
        """Стратегия 3: Plain text + изображение (без Markdown)"""
        if not image_data:
            return False
        
        try:
            # Удаляем Markdown форматирование
            plain_message = self.sanitizer.strip_markdown(message)
            
            await self._send_with_retry(
                lambda: self.bot.send_photo(
                    chat_id=self.channel_id,
                    photo=image_data,  # bytes
                    caption=plain_message,
                    reply_markup=reply_markup
                )
            )
            print("⚠️  [POST] Отправлено без Markdown (с изображением)")
            return True
            
        except Exception as e:
            print(f"⚠️  [POST] Ошибка (plain+image): {type(e).__name__}")
            return False
    
    async def _post_plain_text_only(
        self,
        message: str,
        image_data: Optional[bytes],  # ИСПРАВЛЕНО: bytes
        reply_markup: InlineKeyboardMarkup
    ) -> bool:
        """Стратегия 4: Plain text без изображения (последний шанс)"""
        try:
            # Удаляем Markdown форматирование
            plain_message = self.sanitizer.strip_markdown(message)
            
            await self._send_with_retry(
                lambda: self.bot.send_message(
                    chat_id=self.channel_id,
                    text=plain_message,
                    disable_web_page_preview=True,
                    reply_markup=reply_markup
                )
            )
            print("⚠️  [POST] Отправлено в безопасном режиме (plain text)")
            return True
            
        except Exception as e:
            print(f"❌ [POST] КРИТИЧЕСКАЯ ОШИБКА (plain text): {e}")
            return False
    
    async def _send_with_retry(self, send_func):
        """
        Универсальная функция отправки с retry для сетевых ошибок
        """
        for attempt in range(self.max_retries):
            try:
                result = await send_func()
                return result
                
            except RetryAfter as e:
                # Telegram просит подождать
                wait_time = e.retry_after + 1
                print(f"⏱️  [TELEGRAM] Rate limit. Жду {wait_time}s...")
                self.metrics.retry_count += 1
                await asyncio.sleep(wait_time)
                continue
                
            except (TimedOut, NetworkError) as e:
                # Сетевые ошибки - retry
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    print(f"🔄 [TELEGRAM] Сетевая ошибка. Retry {attempt + 1}/{self.max_retries} через {delay}s")
                    self.metrics.network_errors += 1
                    self.metrics.retry_count += 1
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise
                    
            except TelegramError as e:
                # Другие Telegram ошибки - не retry
                raise
                
            except Exception as e:
                # Неизвестные ошибки
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    print(f"⚠️  [TELEGRAM] Неизвестная ошибка: {type(e).__name__}. Retry через {delay}s")
                    self.metrics.retry_count += 1
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise
        
        # Все retry израсходованы
        raise Exception(f"Превышен лимит retry ({self.max_retries})")
    
    async def _rate_limit(self):
        """Rate limiting между постами"""
        import time
        elapsed = time.time() - self._last_post_time
        
        if elapsed < self._min_post_interval:
            wait_time = self._min_post_interval - elapsed
            await asyncio.sleep(wait_time)
        
        self._last_post_time = time.time()
    
    def get_stats(self) -> Dict:
        """Получить статистику в виде словаря"""
        return {
            'total_attempts': self.metrics.total_attempts,
            'successful': self.metrics.successful_posts,
            'failed': self.metrics.failed_posts,
            'success_rate': f"{self.metrics.success_rate:.1f}%",
            'with_images': self.metrics.posts_with_images,
            'without_images': self.metrics.posts_without_images,
            'markdown_errors': self.metrics.markdown_errors,
            'network_errors': self.metrics.network_errors,
            'retries': self.metrics.retry_count
        }
    
    def print_stats(self):
        """Вывод статистики в консоль"""
        self.metrics.print_summary()
