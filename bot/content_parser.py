# bot/content_parser.py (ФИНАЛЬНАЯ ВЕРСИЯ - 24 октября 2025)
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, unquote
from PIL import Image
import io
import re
from . import config

class ContentParser:
    async def get_article_content(self, url, entry, session):
        soup, final_url = await self._fetch_and_parse_page(url, session)
        article_text = self._extract_article_text(soup, entry)
        image_candidates = self._extract_image_candidates(soup, entry, final_url)
        image_url = await self._get_valid_image_url(image_candidates, session)
        return {'text': article_text, 'image_url': image_url, 'final_url': final_url}

    async def _fetch_and_parse_page(self, url, session):
        """УЛУЧШЕНО: Надежные headers для обхода блокировок"""
        try:
            # Максимально реалистичные headers (как у браузера)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            }
            
            async with session.get(url, timeout=15, headers=headers) as response:
                response.raise_for_status()
                final_url = str(response.url)
                html_text = await response.text()
                soup = BeautifulSoup(html_text, 'lxml')
                return soup, final_url
        except Exception as e:
            print(f"🕸️ [WARN] Не удалось скачать страницу {url}: {e}")
            return None, url

    def _extract_article_text(self, soup, entry):
        """Извлекает текст статьи"""
        if not soup:
            return entry.get('summary', '')
        
        article_body = soup.find('article') or soup.find('div', class_='post-content') or soup.find('body')
        if article_body:
            # Удаляем скрипты и стили
            for element in (article_body.find_all("script") + article_body.find_all("style")):
                element.decompose()
            
            parsed_text = ' '.join(article_body.get_text().split())
            if parsed_text:
                return parsed_text[:12000]
        
        return entry.get('summary', '')

    def _extract_image_candidates(self, soup, entry, final_url):
        """УЛУЧШЕНО: Извлекает кандидатов на изображение с умной обработкой"""
        image_candidates = []
        if not soup:
            return image_candidates
        
        # 1. Приоритет: og:image (обычно лучшего качества)
        if og_image := soup.find('meta', property='og:image'):
            if content := og_image.get('content'):
                full_url = urljoin(final_url, content)
                fixed_url = self._extract_full_size_image_url(full_url)
                image_candidates.append(fixed_url)
                print(f"🖼️ [IMG] Найден og:image: {fixed_url[:80]}...")
        
        # 2. Изображения из article body
        article_body = soup.find('article') or soup.find('div', class_='post-content') or soup.find('body')
        if article_body:
            for img_tag in article_body.find_all('img', src=True):
                if src := img_tag.get('src'):
                    full_url = urljoin(final_url, src)
                    fixed_url = self._extract_full_size_image_url(full_url)
                    image_candidates.append(fixed_url)
        
        # 3. RSS media:content
        if 'media_content' in entry and entry.media_content:
            if media_url := entry.media_content[0].get('url'):
                full_url = urljoin(final_url, media_url)
                fixed_url = self._extract_full_size_image_url(full_url)
                image_candidates.append(fixed_url)
        
        # 4. RSS enclosures
        elif 'enclosures' in entry and entry.enclosures:
            for enc in entry.enclosures:
                if 'image' in enc.type and enc.href:
                    full_url = urljoin(final_url, enc.href)
                    fixed_url = self._extract_full_size_image_url(full_url)
                    image_candidates.append(fixed_url)
        
        print(f"🖼️ [IMG] Найдено {len(image_candidates)} кандидатов")
        return image_candidates

    def _extract_full_size_image_url(self, url):
        """
        КРИТИЧНО: Извлекает полноразмерное изображение из различных форматов URL
        
        Обрабатывает:
        1. Next.js Image Optimization: /_next/image?url=...&w=32
        2. WordPress thumbnails: image-150x150.jpg
        3. Query parameters: ?w=32&h=32
        4. CDN размеры: /w=32,h=32
        """
        if not url:
            return url
        
        original_url = url
        
        # ========================================================================
        # 1. Next.js Image Optimization (CoinDesk и многие современные сайты)
        # ========================================================================
        # URL вида: https://site.com/_next/image?url=https%3A%2F%2Freal-image.png&w=32&q=75
        if '/_next/image' in url and 'url=' in url:
            try:
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                
                # Извлекаем оригинальный URL из параметра 'url'
                if 'url' in params:
                    extracted_url = unquote(params['url'][0])
                    print(f"🔧 [IMG] Next.js → оригинал: {extracted_url[:80]}...")
                    return extracted_url
                
                # Если не получилось - меняем размер на максимальный
                url = re.sub(r'&w=\d+', '&w=1920', url)
                url = re.sub(r'&h=\d+', '&h=1080', url)
                print(f"🔧 [IMG] Next.js → увеличен до 1920x1080")
                return url
                
            except Exception as e:
                print(f"⚠️  [IMG] Ошибка обработки Next.js URL: {e}")
        
        # ========================================================================
        # 2. WordPress/CDN thumbnails
        # ========================================================================
        # image-150x150.jpg → image.jpg
        # image-300x200.jpg → image.jpg
        thumbnail_pattern = r'-\d+x\d+(\.[a-z]{3,4})$'
        if re.search(thumbnail_pattern, url):
            url = re.sub(thumbnail_pattern, r'\1', url)
            print(f"🔧 [IMG] WordPress thumbnail удалён")
            return url
        
        # ========================================================================
        # 3. Query parameters размера (общий случай)
        # ========================================================================
        # ?w=32&h=32 или &width=100&height=100
        if any(param in url.lower() for param in ['?w=', '&w=', '?width=', '&width=', '?size=', '&size=']):
            # Удаляем все параметры размера
            url = re.sub(r'[?&]w=\d+', '', url)
            url = re.sub(r'[?&]h=\d+', '', url)
            url = re.sub(r'[?&]width=\d+', '', url)
            url = re.sub(r'[?&]height=\d+', '', url)
            url = re.sub(r'[?&]size=\d+', '', url)
            url = re.sub(r'[?&]quality=\d+', '', url)
            url = re.sub(r'[?&]q=\d+', '', url)
            
            # Чистим лишние символы
            url = re.sub(r'\?&', '?', url)  # ?& → ?
            url = re.sub(r'&&', '&', url)   # && → &
            url = re.sub(r'[?&]$', '', url) # Убираем ? или & в конце
            
            print(f"🔧 [IMG] Query params удалены")
            return url
        
        # ========================================================================
        # 4. Cloudflare Images / Imgix / CDN
        # ========================================================================
        # https://imagedelivery.net/.../w=32,h=32
        if any(service in url for service in ['imagedelivery.net', 'imgix.net', 'images.unsplash.com', 'cdn-images']):
            # Заменяем маленькие размеры на большие
            url = re.sub(r'/w=\d+', '/w=1920', url)
            url = re.sub(r'/h=\d+', '/h=1080', url)
            url = re.sub(r',w=\d+', ',w=1920', url)
            url = re.sub(r',h=\d+', ',h=1080', url)
            url = re.sub(r'w=\d+', 'w=1920', url)
            url = re.sub(r'h=\d+', 'h=1080', url)
            print(f"🔧 [IMG] CDN размер увеличен")
            return url
        
        # ========================================================================
        # 5. Возвращаем как есть если ничего не подошло
        # ========================================================================
        if url != original_url:
            print(f"🔧 [IMG] URL обработан")
        
        return url

    async def _get_valid_image_url(self, image_candidates, session):
        """УЛУЧШЕНО: Проверяет и возвращает первое валидное изображение"""
        
        # Сортируем кандидатов по приоритету (og:image в начало)
        prioritized = []
        regular = []
        
        for url in image_candidates:
            if not url or self._is_likely_logo(url):
                continue
            
            # og:image обычно лучшего качества - проверяем первым
            if len(prioritized) == 0:
                prioritized.append(url)
            else:
                regular.append(url)
        
        # Проверяем сначала приоритетные, потом обычные
        all_candidates = prioritized + regular
        
        for url in all_candidates:
            try:
                # Проверяем размер изображения
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        print(f"🖼️ [IMG] Пропущено (HTTP {response.status}): {url[:60]}...")
                        continue
                    
                    # Читаем первые 8KB чтобы определить размер (было 4KB)
                    image_data = await response.content.read(8192)
                    if not image_data:
                        continue
                    
                    try:
                        img = Image.open(io.BytesIO(image_data))
                        width, height = img.size
                    except Exception as e:
                        print(f"⚠️  [IMG] Не удалось открыть изображение: {e}")
                        continue
                    
                    # Проверяем минимальный размер
                    if width >= config.MIN_IMAGE_WIDTH and height >= config.MIN_IMAGE_HEIGHT:
                        print(f"✅ [IMG] НАЙДЕНО: {url[:80]} ({width}x{height})")
                        return url
                    else:
                        print(f"🖼️ [IMG] Отклонено (маленькое): {url[:60]} ({width}x{height})")
                
            except asyncio.TimeoutError:
                print(f"⏱️  [IMG] Timeout: {url[:60]}")
                continue
            except Exception as e:
                print(f"⚠️  [IMG] Ошибка проверки {url[:50]}: {e}")
                continue
        
        print(f"⚠️  [IMG] Подходящее изображение не найдено среди {len(all_candidates)} кандидатов")
        return None

    def _is_likely_logo(self, image_url):
        """Определяет является ли URL логотипом/иконкой"""
        if not image_url:
            return True
        
        url_lower = image_url.lower()
        
        # Явные признаки логотипа
        logo_keywords = [
            'logo', 'icon', 'favicon', 'brand', 
            'avatar', 'profile', 'badge',
            '/icons/', '/logos/', '/favicons/',
            'apple-touch-icon', 'android-chrome'
        ]
        
        return any(keyword in url_lower for keyword in logo_keywords)