# bot/content_parser.py
import aiohttp
import asyncio
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, unquote
from PIL import Image
import io
from typing import Optional, List, Dict, Tuple
from .config import config


class URLNormalizer:
    """Умная нормализация и очистка URL"""
    
    @staticmethod
    def normalize(url: str) -> str:
        """
        Удаляет query параметры и fragments для дедупликации
        https://example.com/article?utm_source=fb#top -> https://example.com/article
        """
        if not url:
            return url
        
        parsed = urlparse(url)
        # Оставляем только scheme, netloc и path
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
        # Убираем trailing slash (кроме корневого URL)
        if normalized.endswith('/') and len(parsed.path) > 1:
            normalized = normalized[:-1]
        
        return normalized
    
    @staticmethod
    def is_valid_http_url(url: str) -> bool:
        """Проверка валидности HTTP(S) URL"""
        if not url or len(url) < 10:
            return False
        
        url_lower = url.lower()
        
        # Блокируем невалидные схемы
        invalid_schemes = [
            'data:', 'javascript:', 'mailto:', 'tel:', 'about:', '#'
        ]
        
        if any(url_lower.startswith(scheme) for scheme in invalid_schemes):
            return False
        
        # Должен начинаться с http:// или https://
        if not (url_lower.startswith('http://') or url_lower.startswith('https://')):
            return False
        
        return True


class ImageURLProcessor:
    """Процессор для извлечения full-size изображений"""
    
    @staticmethod
    def extract_full_size_url(url: str) -> str:
        """
        Извлекает полноразмерное изображение из различных форматов URL
        
        Поддерживает:
        - Next.js Image Optimization
        - WordPress thumbnails
        - Query parameters
        - CDN размеры
        """
        if not url:
            return url
        
        original_url = url
        
        # 1. Next.js Image Optimization (_next/image?url=...&w=32)
        if '/_next/image' in url and 'url=' in url:
            try:
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                
                if 'url' in params:
                    extracted_url = unquote(params['url'][0])
                    return extracted_url
                
                # Fallback: увеличиваем размер
                url = re.sub(r'&w=\d+', '&w=1920', url)
                url = re.sub(r'&h=\d+', '&h=1080', url)
                return url
                
            except Exception:
                pass
        
        # 2. WordPress/CDN thumbnails (image-150x150.jpg -> image.jpg)
        thumbnail_pattern = r'-\d+x\d+(\.[a-z]{3,4})$'
        if re.search(thumbnail_pattern, url):
            url = re.sub(thumbnail_pattern, r'\1', url)
            return url
        
        # 3. Query parameters размера (?w=32&h=32)
        if any(param in url.lower() for param in ['?w=', '&w=', '?width=', '&width=', '?size=', '&size=']):
            url = re.sub(r'[?&]w=\d+', '', url)
            url = re.sub(r'[?&]h=\d+', '', url)
            url = re.sub(r'[?&]width=\d+', '', url)
            url = re.sub(r'[?&]height=\d+', '', url)
            url = re.sub(r'[?&]size=\d+', '', url)
            url = re.sub(r'[?&]quality=\d+', '', url)
            url = re.sub(r'[?&]q=\d+', '', url)
            
            # Чистка
            url = re.sub(r'\?&', '?', url)
            url = re.sub(r'&&+', '&', url)
            url = re.sub(r'[?&]$', '', url)
            
            return url
        
        # 4. CDN сервисы (Cloudflare, Imgix, etc)
        cdn_services = ['imagedelivery.net', 'imgix.net', 'images.unsplash.com', 'cdn-images']
        if any(service in url for service in cdn_services):
            url = re.sub(r'/w=\d+', '/w=1920', url)
            url = re.sub(r'/h=\d+', '/h=1080', url)
            url = re.sub(r',w=\d+', ',w=1920', url)
            url = re.sub(r',h=\d+', ',h=1080', url)
            url = re.sub(r'\bw=\d+', 'w=1920', url)
            url = re.sub(r'\bh=\d+', 'h=1080', url)
            return url
        
        return url
    
    @staticmethod
    def is_likely_logo(url: str) -> bool:
        """Определяет является ли URL логотипом/иконкой"""
        if not url:
            return True
        
        url_lower = url.lower()
        
        logo_keywords = [
            'logo', 'icon', 'favicon', 'brand',
            'avatar', 'profile', 'badge', 'symbol',
            '/icons/', '/logos/', '/favicons/',
            'apple-touch-icon', 'android-chrome',
            'og-image-default', 'default-thumb'
        ]
        
        return any(keyword in url_lower for keyword in logo_keywords)


class ArticleExtractor:
    """Умный экстрактор текста статьи"""
    
    @staticmethod
    def extract_text(soup: BeautifulSoup, fallback_summary: str = '') -> str:
        """
        Извлекает основной текст статьи с приоритезацией
        """
        if not soup:
            return fallback_summary
        
        # Приоритеты для поиска контента
        content_selectors = [
            ('article', {}),
            ('div', {'class': ['post-content', 'article-content', 'entry-content', 'content']}),
            ('div', {'id': ['article', 'content', 'main-content']}),
            ('main', {}),
        ]
        
        for tag, attrs in content_selectors:
            if attrs:
                article_body = soup.find(tag, attrs)
            else:
                article_body = soup.find(tag)
            
            if article_body:
                # Удаляем ненужные элементы
                for unwanted in article_body.find_all(['script', 'style', 'nav', 'aside', 'footer', 'header']):
                    unwanted.decompose()
                
                # Извлекаем текст
                text = article_body.get_text(separator=' ', strip=True)
                
                # Очистка лишних пробелов
                text = re.sub(r'\s+', ' ', text)
                
                if len(text) > 200:  # Минимальная длина статьи
                    return text[:config.MAX_ARTICLE_TEXT_LENGTH]
        
        # Fallback на summary из RSS
        return fallback_summary


class ImageExtractor:
    """Умный экстрактор изображений с приоритезацией"""
    
    def __init__(self):
        self.url_processor = ImageURLProcessor()
        self.url_normalizer = URLNormalizer()
    
    def extract_candidates(
        self,
        soup: BeautifulSoup,
        entry: Dict,
        base_url: str
    ) -> List[str]:
        """
        Извлекает кандидатов на изображение с умной приоритезацией
        
        Приоритет:
        1. og:image (лучшее качество)
        2. twitter:image
        3. Первое изображение в article
        4. RSS media:content
        5. RSS enclosures
        """
        candidates = []
        
        if not soup:
            return self._extract_from_rss(entry, base_url)
        
        # 1. Open Graph image (высший приоритет)
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            url = self._process_url(og_image['content'], base_url)
            if url:
                candidates.append(('og:image', url, 10))  # priority 10
        
        # 2. Twitter card image
        twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
        if twitter_image and twitter_image.get('content'):
            url = self._process_url(twitter_image['content'], base_url)
            if url:
                candidates.append(('twitter:image', url, 9))
        
        # 3. Первое изображение в article
        article_body = soup.find('article') or soup.find('div', class_='post-content')
        if article_body:
            images = article_body.find_all('img', src=True, limit=5)
            for idx, img in enumerate(images):
                url = self._process_url(img['src'], base_url)
                if url:
                    priority = 8 - idx  # Первое изображение важнее
                    candidates.append((f'article-img-{idx}', url, priority))
        
        # 4. RSS media:content
        if hasattr(entry, 'media_content') and entry.media_content:
            for media in entry.media_content[:3]:
                if url := media.get('url'):
                    url = self._process_url(url, base_url)
                    if url:
                        candidates.append(('rss-media', url, 6))
        
        # 5. RSS enclosures
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enc in entry.enclosures[:3]:
                if 'image' in enc.get('type', '') and enc.get('href'):
                    url = self._process_url(enc['href'], base_url)
                    if url:
                        candidates.append(('rss-enclosure', url, 5))
        
        # Сортируем по приоритету (высший первым)
        candidates.sort(key=lambda x: x[2], reverse=True)
        
        # Возвращаем только URLs без дубликатов
        seen = set()
        unique_urls = []
        for source, url, priority in candidates:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        return unique_urls
    
    def _extract_from_rss(self, entry: Dict, base_url: str) -> List[str]:
        """Fallback: извлечение только из RSS когда нет soup"""
        candidates = []
        
        if hasattr(entry, 'media_content') and entry.media_content:
            for media in entry.media_content[:3]:
                if url := media.get('url'):
                    url = self._process_url(url, base_url)
                    if url:
                        candidates.append(url)
        
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enc in entry.enclosures[:3]:
                if 'image' in enc.get('type', '') and enc.get('href'):
                    url = self._process_url(enc['href'], base_url)
                    if url:
                        candidates.append(url)
        
        return candidates
    
    def _process_url(self, url: str, base_url: str) -> Optional[str]:
        """Обработка и валидация URL изображения"""
        # Преобразуем относительный URL в абсолютный
        full_url = urljoin(base_url, url)
        
        # Валидация
        if not self.url_normalizer.is_valid_http_url(full_url):
            return None
        
        # Проверка на логотип
        if self.url_processor.is_likely_logo(full_url):
            return None
        
        # Извлечение full-size версии
        return self.url_processor.extract_full_size_url(full_url)


class ContentParser:
    """
    Главный класс для парсинга контента статей
    Объединяет все компоненты для умного извлечения текста и изображений
    """
    
    def __init__(self):
        self.url_normalizer = URLNormalizer()
        self.article_extractor = ArticleExtractor()
        self.image_extractor = ImageExtractor()
    
    async def get_article_content(
        self,
        url: str,
        entry: Dict,
        session: aiohttp.ClientSession
    ) -> Dict[str, Optional[str]]:
        """
        Основной метод для получения контента статьи
        
        Returns:
            {
                'text': str,
                'image_url': Optional[str],
                'final_url': str
            }
        """
        # Загружаем и парсим страницу
        soup, final_url = await self._fetch_and_parse_page(url, session)
        
        # Извлекаем текст
        fallback_summary = entry.get('summary', '')
        article_text = self.article_extractor.extract_text(soup, fallback_summary)
        
        # Извлекаем изображения
        image_candidates = self.image_extractor.extract_candidates(soup, entry, final_url)
        image_url = await self._validate_image(image_candidates, session)
        
        return {
            'text': article_text,
            'image_url': image_url,
            'final_url': final_url
        }
    
    async def parse_article(
        self,
        link: str,
        session: aiohttp.ClientSession
    ) -> str:
        """
        Извлекает текст статьи из URL
        
        Этот метод был добавлен для совместимости с bot/processor.py,
        который вызывает self.parser.parse_article(link, session)
        
        Args:
            link: URL статьи
            session: aiohttp ClientSession для запросов
            
        Returns:
            Извлеченный текст статьи
        """
        try:
            # Загружаем и парсим страницу
            soup, final_url = await self._fetch_and_parse_page(link, session)
            
            if not soup:
                print(f"⚠️  [PARSER] Не удалось загрузить страницу: {link[:60]}")
                return ""
            
            # Извлекаем текст статьи
            article_text = self.article_extractor.extract_text(soup, fallback_summary='')
            
            if article_text and len(article_text) > 100:
                print(f"✅ [PARSER] Извлечено {len(article_text)} символов из {link[:60]}")
                return article_text
            else:
                print(f"⚠️  [PARSER] Текст статьи слишком короткий: {len(article_text)} символов")
                return ""
        
        except Exception as e:
            print(f"❌ [PARSER] Ошибка parse_article для {link[:60]}: {e}")
            return ""
    
    async def _fetch_and_parse_page(
        self,
        url: str,
        session: aiohttp.ClientSession
    ) -> Tuple[Optional[BeautifulSoup], str]:
        """Загрузка и парсинг HTML страницы"""
        try:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=15),
                allow_redirects=True
            ) as response:
                response.raise_for_status()
                final_url = str(response.url)
                
                # Проверка content-type
                content_type = response.headers.get('Content-Type', '').lower()
                if 'text/html' not in content_type:
                    print(f"⚠️  [PARSER] Не HTML контент: {content_type}")
                    return None, url
                
                html_text = await response.text()
                soup = BeautifulSoup(html_text, 'lxml')
                
                return soup, final_url
                
        except asyncio.TimeoutError:
            print(f"⏱️  [PARSER] Timeout загрузки: {url[:60]}")
        except aiohttp.ClientError as e:
            print(f"🕸️  [PARSER] HTTP ошибка {url[:50]}: {type(e).__name__}")
        except Exception as e:
            print(f"❌ [PARSER] Ошибка парсинга {url[:50]}: {e}")
        
        return None, url
    
    async def _validate_image(
        self,
        candidates: List[str],
        session: aiohttp.ClientSession
    ) -> Optional[str]:
        """
        Проверка и валидация изображений
        Возвращает первое валидное изображение подходящего размера
        """
        if not candidates:
            return None
        
        print(f"🖼️  [IMG] Проверяю {len(candidates)} кандидатов...")
        
        for idx, url in enumerate(candidates):
            try:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=config.IMAGE_CHECK_TIMEOUT)
                ) as response:
                    
                    if response.status != 200:
                        continue
                    
                    # Читаем первые байты для определения размера
                    image_data = await response.content.read(config.IMAGE_PARTIAL_READ_BYTES)
                    if not image_data:
                        continue
                    
                    try:
                        img = Image.open(io.BytesIO(image_data))
                        width, height = img.size
                        
                        # Проверка минимального размера
                        if width >= config.MIN_IMAGE_WIDTH and height >= config.MIN_IMAGE_HEIGHT:
                            print(f"✅ [IMG] ВАЛИДНОЕ #{idx + 1}: {url[:70]} ({width}x{height})")
                            return url
                        else:
                            print(f"📏 [IMG] Маленькое #{idx + 1}: {width}x{height}px")
                    
                    except Exception as e:
                        print(f"⚠️  [IMG] Не удалось открыть #{idx + 1}: {type(e).__name__}")
                        continue
                    
            except asyncio.TimeoutError:
                print(f"⏱️  [IMG] Timeout #{idx + 1}")
                continue
            except aiohttp.ClientError:
                continue
            except Exception as e:
                print(f"⚠️  [IMG] Ошибка #{idx + 1}: {type(e).__name__}")
                continue
        
        print(f"⚠️  [IMG] Подходящее изображение не найдено")
        return None