# bot/telegram_poster.py v2.0

import asyncio
import re
import aiohttp
import io
from typing import Optional, Dict
from datetime import datetime
from PIL import Image, ImageOps

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError, RetryAfter, TimedOut, NetworkError

try:
    from .config import config
    CONFIG_AVAILABLE = True
except ImportError:
    try:
        from bot.config import config
        CONFIG_AVAILABLE = True
    except ImportError:
        CONFIG_AVAILABLE = False
        
        class DummyConfig:
            TELEGRAM_BOT_TOKEN = ""
            TELEGRAM_CHANNEL_ID = ""
            IMAGE_DOWNLOAD_TIMEOUT = 15
            MAX_IMAGE_SIZE_MB = 10
        
        config = DummyConfig()


class PostingMetrics:
    
    def __init__(self):
        self.total_attempts = 0
        self.successful_posts = 0
        self.failed_posts = 0
        self.posts_with_images = 0
        self.posts_without_images = 0
        self.markdown_errors = 0
        self.network_errors = 0
        self.retry_count = 0
        self.images_downloaded = 0
        self.images_download_failed = 0
        self.total_download_time = 0.0
        self.strategies_used = {
            'markdown_with_image': 0,
            'markdown_without_image': 0,
            'plain_with_image': 0,
            'plain_text': 0
        }
    
    @property
    def success_rate(self) -> float:
        if self.total_attempts == 0:
            return 0.0
        return (self.successful_posts / self.total_attempts) * 100
    
    @property
    def image_download_rate(self) -> float:
        total = self.images_downloaded + self.images_download_failed
        if total == 0:
            return 0.0
        return (self.images_downloaded / total) * 100
    
    @property
    def avg_download_time(self) -> float:
        if self.images_downloaded == 0:
            return 0.0
        return self.total_download_time / self.images_downloaded
    
    def record_strategy(self, strategy_name: str):
        if strategy_name in self.strategies_used:
            self.strategies_used[strategy_name] += 1
    
    def to_dict(self) -> Dict:
        return {
            'total_attempts': self.total_attempts,
            'successful_posts': self.successful_posts,
            'failed_posts': self.failed_posts,
            'success_rate': self.success_rate,
            'posts_with_images': self.posts_with_images,
            'posts_without_images': self.posts_without_images,
            'markdown_errors': self.markdown_errors,
            'network_errors': self.network_errors,
            'retry_count': self.retry_count,
            'images_downloaded': self.images_downloaded,
            'images_download_failed': self.images_download_failed,
            'image_download_rate': self.image_download_rate,
            'avg_download_time': self.avg_download_time,
            'strategies_used': dict(self.strategies_used)
        }
    
    def print_summary(self):
        print("\n📊 [TELEGRAM STATS] Статистика публикаций:")
        print(f"  Всего попыток: {self.total_attempts}")
        print(f"  Успешно: {self.successful_posts} ({self.success_rate:.1f}%)")
        print(f"  Неудачно: {self.failed_posts}")
        print(f"  С изображениями: {self.posts_with_images}")
        print(f"  Без изображений: {self.posts_without_images}")
        print(f"  Изображений скачано: {self.images_downloaded}/{self.images_downloaded + self.images_download_failed} ({self.image_download_rate:.1f}%)")
        if self.images_downloaded > 0:
            print(f"  Среднее время скачивания: {self.avg_download_time:.2f}s")
        print(f"  Ошибок Markdown: {self.markdown_errors}")
        print(f"  Сетевых ошибок: {self.network_errors}")
        print(f"  Повторов (retry): {self.retry_count}")
        
        if any(count > 0 for count in self.strategies_used.values()):
            print("\n  Использованные стратегии:")
            for strategy, count in sorted(self.strategies_used.items(), key=lambda x: x[1], reverse=True):
                if count > 0:
                    print(f"    • {strategy}: {count}")


class MessageSanitizer:
    
    MAX_MESSAGE_LENGTH = 4096
    MAX_CAPTION_LENGTH = 1024
    
    @staticmethod
    def sanitize_markdown(text: str) -> str:
        if not text:
            return text
        
        text = re.sub(r'<[^>]+>', '', text)
        
        text = re.sub(r'\*{4,}', '**', text)
        text = re.sub(r'_{4,}', '__', text)
        text = re.sub(r'`{4,}', '``', text)
        
        text = re.sub(r'\*\*\s*\*\*', '', text)
        text = re.sub(r'__\s*__', '', text)
        text = re.sub(r'~~\s*~~', '', text)
        text = re.sub(r'``\s*``', '', text)
        
        text = re.sub(r'(\w)([*_`])(\s)', r'\1\\\2\3', text)
        text = re.sub(r'(\w)([*_`])([.,!?;:])', r'\1\\\2\3', text)
        
        text = re.sub(r'\[(.*?)\]\((.*?)\)', lambda m: f"[{m.group(1).replace('*', '').replace('_', '')}]({m.group(2)})", text)
        
        for char in ['*', '_', '`']:
            count = text.count(char)
            if count % 2 != 0:
                pos = text.rfind(char)
                if pos != -1:
                    text = text[:pos] + text[pos + 1:]
        
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        return text.strip()
    
    @staticmethod
    def strip_markdown(text: str) -> str:
        if not text:
            return text
        
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'__(.*?)__', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = re.sub(r'_(.*?)_', r'\1', text)
        text = re.sub(r'`(.*?)`', r'\1', text)
        text = re.sub(r'~~(.*?)~~', r'\1', text)
        text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
        
        text = re.sub(r'[*_`~\[\]]', '', text)
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    @staticmethod
    def truncate(text: str, max_length: int, suffix: str = '...') -> str:
        if len(text) <= max_length:
            return text
        
        truncated = text[:max_length - len(suffix)]
        
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.8:
            truncated = truncated[:last_space]
        
        last_newline = truncated.rfind('\n')
        if last_newline > max_length * 0.8:
            truncated = truncated[:last_newline]
        
        return truncated.rstrip() + suffix
    
    @classmethod
    def prepare_message(cls, text: str, is_caption: bool = False) -> str:
        text = cls.sanitize_markdown(text)
        
        max_length = cls.MAX_CAPTION_LENGTH if is_caption else cls.MAX_MESSAGE_LENGTH
        if len(text) > max_length:
            text = cls.truncate(text, max_length)
        
        return text
    
    @staticmethod
    def validate_message(text: str) -> bool:
        if not text or len(text.strip()) < 10:
            return False
        
        if len(text) > MessageSanitizer.MAX_MESSAGE_LENGTH:
            return False
        
        return True


class ImageDownloader:
    
    def __init__(self):
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        self.timeout = getattr(config, 'IMAGE_DOWNLOAD_TIMEOUT', 15)
        self.max_size_mb = getattr(config, 'MAX_IMAGE_SIZE_MB', 10)
        self.max_size_bytes = self.max_size_mb * 1024 * 1024
    
    async def download(
        self,
        image_url: str,
        referer: Optional[str] = None,
    ) -> Optional[bytes]:
        if not image_url:
            return None
        
        try:
            print(f"📥 [TELEGRAM] Скачиваю изображение: {image_url[:70]}")
            
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Referer': referer or image_url,
                'DNT': '1'
            }
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    image_url,
                    headers=headers,
                    timeout=timeout,
                    allow_redirects=True
                ) as response:
                    
                    if response.status != 200:
                        print(f"❌ [TELEGRAM] HTTP {response.status} при скачивании изображения")
                        return None
                    
                    content_type = response.headers.get('Content-Type', '').lower()
                    if not any(img_type in content_type for img_type in ['image/', 'octet-stream']):
                        print(f"⚠️  [TELEGRAM] Неверный Content-Type: {content_type}")
                        return None
                    
                    content_length = response.headers.get('Content-Length')
                    if content_length and int(content_length) > self.max_size_bytes:
                        print(f"⚠️  [TELEGRAM] Изображение слишком большое: {int(content_length) / 1024 / 1024:.1f}MB")
                        return None
                    
                    image_data = await response.read()
                    
                    if not image_data or len(image_data) < 100:
                        print(f"⚠️  [TELEGRAM] Пустое изображение")
                        return None
                    
                    if len(image_data) > self.max_size_bytes:
                        print(f"⚠️  [TELEGRAM] Изображение слишком большое после загрузки: {len(image_data) / 1024 / 1024:.1f}MB")
                        return None
                    
                    try:
                        prepared_data, width, height = self._prepare_for_telegram(
                            image_data
                        )
                        print(
                            f"✅ [TELEGRAM] Изображение подготовлено: "
                            f"{width}x{height}px, {len(prepared_data) // 1024}KB"
                        )
                        return prepared_data
                        
                    except Exception as e:
                        print(f"⚠️  [TELEGRAM] Не удалось открыть изображение: {type(e).__name__}")
                        return None
        
        except asyncio.TimeoutError:
            print(f"⏱️  [TELEGRAM] Timeout при скачивании изображения")
            return None
        except aiohttp.ClientError as e:
            print(f"🕸️  [TELEGRAM] HTTP ошибка: {type(e).__name__}")
            return None
        except Exception as e:
            print(f"❌ [TELEGRAM] Ошибка скачивания: {e}")
            return None

    def _prepare_for_telegram(self, image_data: bytes):
        """Нормализовать изображение под ограничения Telegram sendPhoto."""
        with Image.open(io.BytesIO(image_data)) as source:
            image = ImageOps.exif_transpose(source)
            if image.mode != 'RGB':
                if 'A' in image.getbands():
                    background = Image.new('RGB', image.size, 'white')
                    background.paste(image, mask=image.getchannel('A'))
                    image = background
                else:
                    image = image.convert('RGB')

            max_dimension = 5000
            if image.width + image.height > 10_000:
                max_dimension = 4500
            image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

            quality = 90
            while quality >= 55:
                output = io.BytesIO()
                image.save(output, format='JPEG', quality=quality, optimize=True)
                prepared = output.getvalue()
                if len(prepared) <= self.max_size_bytes:
                    return prepared, image.width, image.height
                quality -= 10

        raise ValueError('Image cannot be reduced to Telegram photo limits')


class TelegramPoster:
    
    def __init__(self):
        if not CONFIG_AVAILABLE or not config.TELEGRAM_BOT_TOKEN:
            print("❌ [TELEGRAM] Не настроен TELEGRAM_BOT_TOKEN")
            self._initialized = False
            return
        
        if not config.TELEGRAM_CHANNEL_ID:
            print("❌ [TELEGRAM] Не настроен TELEGRAM_CHANNEL_ID")
            self._initialized = False
            return
        
        self.bot = telegram.Bot(token=config.TELEGRAM_BOT_TOKEN)
        self.channel_id = config.TELEGRAM_CHANNEL_ID
        self.metrics = PostingMetrics()
        self.sanitizer = MessageSanitizer()
        self.image_downloader = ImageDownloader()
        
        self._last_post_time = 0
        self._min_post_interval = 3.0
        
        self.max_retries = 3
        self.retry_delays = [5, 10, 20]
        
        self._initialized = True
        
        print(f"📱 [TELEGRAM] Poster v2.0 инициализирован")
        print(f"   • Канал: {self.channel_id}")
        print(f"   • Rate limit: {self._min_post_interval}s")
        print(f"   • Max retries: {self.max_retries}")
        print(f"   • Image download: ✅ Enabled")
    
    @property
    def is_initialized(self) -> bool:
        return getattr(self, '_initialized', False)
    
    async def post(
        self,
        message: Optional[str] = None,
        link: Optional[str] = None,
        image_url: Optional[str] = None,
        text: Optional[str] = None,
        image_data: Optional[bytes] = None,
        **kwargs
    ) -> bool:
        
        if not self.is_initialized:
            print("❌ [TELEGRAM] Poster не инициализирован")
            return False
        
        final_message = message or text
        final_link = link
        final_image_data = image_data
        
        if not final_message:
            print("❌ [POST] Отсутствует текст сообщения")
            return False
        
        if not final_link:
            print("❌ [POST] Отсутствует ссылка")
            return False
        
        if not self.sanitizer.validate_message(final_message):
            print("❌ [POST] Невалидное сообщение")
            return False
        
        self.metrics.total_attempts += 1
        
        await self._rate_limit()
        
        if image_url and not final_image_data:
            start_time = datetime.now()
            final_image_data = await self.image_downloader.download(
                image_url,
                referer=final_link,
            )
            download_time = (datetime.now() - start_time).total_seconds()
            
            if final_image_data:
                self.metrics.images_downloaded += 1
                self.metrics.total_download_time += download_time
                print(f"✅ [TELEGRAM] Изображение скачано за {download_time:.2f}s")
            else:
                self.metrics.images_download_failed += 1
                print(f"⚠️  [TELEGRAM] Не удалось скачать изображение, публикую без него")
        
        keyboard = [[InlineKeyboardButton("🔗 Читать первоисточник", url=final_link)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        is_caption = bool(final_image_data)
        prepared_message = self.sanitizer.prepare_message(final_message, is_caption=is_caption)
        
        if final_image_data:
            strategies = [
                ('markdown_with_image', self._post_with_markdown_and_image),
                ('plain_with_image', self._post_plain_with_image),
                ('markdown_without_image', self._post_with_markdown_text_only),
                ('plain_text', self._post_plain_text_only),
            ]
        else:
            strategies = [
                ('markdown_without_image', self._post_with_markdown_text_only),
                ('plain_text', self._post_plain_text_only),
            ]
        
        for strategy_name, strategy_func in strategies:
            success = await strategy_func(
                prepared_message,
                final_image_data,
                reply_markup
            )
            
            if success:
                self.metrics.successful_posts += 1
                self.metrics.record_strategy(strategy_name)
                
                if strategy_name.endswith('with_image'):
                    self.metrics.posts_with_images += 1
                else:
                    self.metrics.posts_without_images += 1
                
                print(f"✅ [POST] Успешно ({strategy_name}): {final_link[:60]}")
                return True
            
            if strategy_name != strategies[-1][0]:
                print(f"🔄 [POST] Пробую следующую стратегию...")
                await asyncio.sleep(2)
        
        self.metrics.failed_posts += 1
        print(f"❌ [POST] ВСЕ СТРАТЕГИИ ПРОВАЛИЛИСЬ: {final_link[:60]}")
        return False
    
    async def _post_with_markdown_and_image(
        self,
        message: str,
        image_data: Optional[bytes],
        reply_markup: InlineKeyboardMarkup
    ) -> bool:
        if not image_data:
            return False
        
        try:
            await self._send_with_retry(
                lambda: self.bot.send_photo(
                    chat_id=self.channel_id,
                    photo=image_data,
                    caption=message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            )
            return True
            
        except telegram.error.BadRequest as e:
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ['parse', 'markdown', 'entities', 'can\'t parse']):
                self.metrics.markdown_errors += 1
                print(f"⚠️  [POST] Markdown ошибка: {e}")
            else:
                print(f"⚠️  [POST] BadRequest: {e}")
            return False
        except Exception as e:
            print(f"⚠️  [POST] Ошибка (markdown+image): {type(e).__name__}")
            return False
    
    async def _post_with_markdown_text_only(
        self,
        message: str,
        image_data: Optional[bytes],
        reply_markup: InlineKeyboardMarkup
    ) -> bool:
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
            if any(keyword in error_str for keyword in ['parse', 'markdown', 'entities', 'can\'t parse']):
                self.metrics.markdown_errors += 1
                print(f"⚠️  [POST] Markdown ошибка (text): {e}")
            else:
                print(f"⚠️  [POST] BadRequest (text): {e}")
            return False
        except Exception as e:
            print(f"⚠️  [POST] Ошибка (markdown text): {type(e).__name__}")
            return False
    
    async def _post_plain_with_image(
        self,
        message: str,
        image_data: Optional[bytes],
        reply_markup: InlineKeyboardMarkup
    ) -> bool:
        if not image_data:
            return False
        
        try:
            plain_message = self.sanitizer.strip_markdown(message)
            
            if len(plain_message) > MessageSanitizer.MAX_CAPTION_LENGTH:
                plain_message = self.sanitizer.truncate(plain_message, MessageSanitizer.MAX_CAPTION_LENGTH)
            
            await self._send_with_retry(
                lambda: self.bot.send_photo(
                    chat_id=self.channel_id,
                    photo=image_data,
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
        image_data: Optional[bytes],
        reply_markup: InlineKeyboardMarkup
    ) -> bool:
        try:
            plain_message = self.sanitizer.strip_markdown(message)
            
            if len(plain_message) > MessageSanitizer.MAX_MESSAGE_LENGTH:
                plain_message = self.sanitizer.truncate(plain_message, MessageSanitizer.MAX_MESSAGE_LENGTH)
            
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
        for attempt in range(self.max_retries):
            try:
                result = await send_func()
                return result
                
            except RetryAfter as e:
                wait_time = e.retry_after + 1
                print(f"⏱️  [TELEGRAM] Rate limit. Жду {wait_time}s...")
                self.metrics.retry_count += 1
                await asyncio.sleep(wait_time)
                continue
                
            except (TimedOut, NetworkError) as e:
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
                error_str = str(e).lower()
                if 'flood' in error_str or 'too many' in error_str:
                    if attempt < self.max_retries - 1:
                        delay = self.retry_delays[attempt] * 2
                        print(f"⏱️  [TELEGRAM] Flood control. Жду {delay}s...")
                        self.metrics.retry_count += 1
                        await asyncio.sleep(delay)
                        continue
                raise
                
            except Exception as e:
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    print(f"⚠️  [TELEGRAM] Неизвестная ошибка: {type(e).__name__}. Retry через {delay}s")
                    self.metrics.retry_count += 1
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise
        
        raise Exception(f"Превышен лимит retry ({self.max_retries})")
    
    async def _rate_limit(self):
        import time
        elapsed = time.time() - self._last_post_time
        
        if elapsed < self._min_post_interval:
            wait_time = self._min_post_interval - elapsed
            await asyncio.sleep(wait_time)
        
        self._last_post_time = time.time()
    
    def get_stats(self) -> Dict:
        stats = self.metrics.to_dict()
        
        stats['total_posts'] = self.metrics.total_attempts
        stats['successful_posts'] = self.metrics.successful_posts
        stats['failed_posts'] = self.metrics.failed_posts
        
        return stats
    
    def print_stats(self):
        self.metrics.print_summary()


__all__ = ['TelegramPoster', 'PostingMetrics', 'MessageSanitizer', 'ImageDownloader']
