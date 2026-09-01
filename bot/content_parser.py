# bot/content_parser.py v2.0

import aiohttp
import asyncio
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, unquote
from PIL import Image
import io
from typing import Optional, List, Dict, Tuple
from collections import defaultdict

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
            MAX_ARTICLE_TEXT_LENGTH = 5000
            IMAGE_CHECK_TIMEOUT = 10
            IMAGE_PARTIAL_READ_BYTES = 10240
            MIN_IMAGE_WIDTH = 200
            MIN_IMAGE_HEIGHT = 200
            PARSER_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        
        config = DummyConfig()


class ParserStats:
    
    def __init__(self):
        self.pages_fetched = 0
        self.pages_failed = 0
        self.images_validated = 0
        self.images_rejected = 0
        self.text_extracted = 0
        self.errors_by_type = defaultdict(int)
    
    def record_page_fetch(self, success: bool):
        if success:
            self.pages_fetched += 1
        else:
            self.pages_failed += 1
    
    def record_image_validation(self, valid: bool):
        if valid:
            self.images_validated += 1
        else:
            self.images_rejected += 1
    
    def record_text_extraction(self):
        self.text_extracted += 1
    
    def record_error(self, error_type: str):
        self.errors_by_type[error_type] += 1
    
    def get_summary(self) -> Dict:
        return {
            'pages_fetched': self.pages_fetched,
            'pages_failed': self.pages_failed,
            'success_rate': (self.pages_fetched / (self.pages_fetched + self.pages_failed) * 100) if (self.pages_fetched + self.pages_failed) > 0 else 0.0,
            'images_validated': self.images_validated,
            'images_rejected': self.images_rejected,
            'image_success_rate': (self.images_validated / (self.images_validated + self.images_rejected) * 100) if (self.images_validated + self.images_rejected) > 0 else 0.0,
            'text_extracted': self.text_extracted,
            'errors': dict(self.errors_by_type)
        }
    
    def print_stats(self):
        print("\n📊 [PARSER] Статистика:")
        print(f"  Pages: {self.pages_fetched}/{self.pages_fetched + self.pages_failed} ({self.pages_fetched / (self.pages_fetched + self.pages_failed) * 100:.1f}%)" if (self.pages_fetched + self.pages_failed) > 0 else "  Pages: 0/0")
        print(f"  Images: {self.images_validated}/{self.images_validated + self.images_rejected} ({self.images_validated / (self.images_validated + self.images_rejected) * 100:.1f}%)" if (self.images_validated + self.images_rejected) > 0 else "  Images: 0/0")
        print(f"  Text extracted: {self.text_extracted}")


class URLNormalizer:
    
    @staticmethod
    def normalize(url: str) -> str:
        if not url:
            return url
        
        try:
            parsed = urlparse(url)
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            if normalized.endswith('/') and len(parsed.path) > 1:
                normalized = normalized[:-1]
            
            return normalized
        except Exception:
            return url
    
    @staticmethod
    def is_valid_http_url(url: str) -> bool:
        if not url or len(url) < 10:
            return False
        
        url_lower = url.lower()
        
        invalid_schemes = [
            'data:', 'javascript:', 'mailto:', 'tel:', 'about:', '#',
            'ftp:', 'file:', 'blob:', 'intent:'
        ]
        
        if any(url_lower.startswith(scheme) for scheme in invalid_schemes):
            return False
        
        if not (url_lower.startswith('http://') or url_lower.startswith('https://')):
            return False
        
        parsed = urlparse(url)
        if not parsed.netloc or len(parsed.netloc) < 3:
            return False
        
        if '..' in parsed.path or '//' in parsed.path.replace('//', '', 1):
            return False
        
        return True
    
    @staticmethod
    def clean_url(url: str) -> str:
        if not url:
            return url
        
        try:
            url = url.strip()
            url = url.replace(' ', '%20')
            url = re.sub(r'\s+', '', url)
            
            return url
        except Exception:
            return url


class ImageURLProcessor:
    
    @staticmethod
    def extract_full_size_url(url: str) -> str:
        if not url:
            return url
        
        original_url = url
        
        try:
            if '/_next/image' in url and 'url=' in url:
                try:
                    parsed = urlparse(url)
                    params = parse_qs(parsed.query)
                    
                    if 'url' in params:
                        extracted_url = unquote(params['url'][0])
                        return extracted_url
                    
                    url = re.sub(r'&w=\d+', '&w=1920', url)
                    url = re.sub(r'&h=\d+', '&h=1080', url)
                    url = re.sub(r'&q=\d+', '&q=90', url)
                    return url
                    
                except Exception:
                    pass
            
            thumbnail_pattern = r'-\d+x\d+(\.[a-z]{3,4})$'
            if re.search(thumbnail_pattern, url):
                url = re.sub(thumbnail_pattern, r'\1', url)
                return url
            
            # Не переписываем CDN URL: query/path могут входить в подпись.
            # Крупный вариант выбирается из srcset, если он доступен.
            return url
            
        except Exception:
            return original_url
    
    @staticmethod
    def is_likely_logo(url: str) -> bool:
        if not url:
            return True
        
        url_lower = url.lower()
        
        logo_keywords = [
            'logo', 'icon', 'favicon', 'brand', 'avatar', 'profile',
            'badge', 'symbol', 'thumbnail', 'thumb', 'placeholder',
            '/icons/', '/logos/', '/favicons/', '/badges/',
            'apple-touch-icon', 'android-chrome', 'mstile',
            'og-image-default', 'default-thumb', 'default-image',
            'social-share', 'share-default', 'no-image',
            'blank.', 'spacer.', 'pixel.', 'transparent.',
            '1x1.', 'tracking.', 'beacon.', 'analytics.',
            'ad-placeholder', 'banner-default'
        ]
        
        if any(keyword in url_lower for keyword in logo_keywords):
            return True
        
        size_patterns = [
            r'/\d{1,3}x\d{1,3}[/\.]',
            r'[-_]\d{1,3}x\d{1,3}[-_\.]',
            r'_small[-_\.]',
            r'_tiny[-_\.]',
            r'_mini[-_\.]'
        ]
        
        for pattern in size_patterns:
            if re.search(pattern, url_lower):
                return True
        
        return False
    
    @staticmethod
    def get_priority_score(url: str, source: str) -> int:
        score = 0
        url_lower = url.lower()
        
        priority_indicators = {
            'featured': 5,
            'hero': 5,
            'main': 4,
            'cover': 4,
            'post': 3,
            'article': 3,
            'content': 2,
            'full': 2,
            'large': 2,
            'hd': 3,
            '1920': 2,
            '1080': 2
        }
        
        for indicator, points in priority_indicators.items():
            if indicator in url_lower:
                score += points
        
        if source == 'og:image':
            score += 10
        elif source == 'twitter:image':
            score += 9
        elif source == 'article-img':
            score += 8
        elif source == 'rss-media':
            score += 7
        
        return score


class ArticleExtractor:
    
    @staticmethod
    def extract_text(soup: BeautifulSoup, fallback_summary: str = '') -> str:
        if not soup:
            return fallback_summary
        
        content_selectors = [
            ('article', {}),
            ('div', {'class': ['post-content', 'article-content', 'entry-content', 'content', 'article-body', 'post-body']}),
            ('div', {'id': ['article', 'content', 'main-content', 'post-content']}),
            ('main', {}),
            ('div', {'class': ['text', 'description', 'body']}),
        ]
        
        for tag, attrs in content_selectors:
            try:
                if attrs:
                    article_body = soup.find(tag, attrs)
                    if not article_body and 'class' in attrs:
                        for class_name in attrs['class']:
                            article_body = soup.find(tag, class_=lambda x: x and class_name in x)
                            if article_body:
                                break
                else:
                    article_body = soup.find(tag)
                
                if article_body:
                    for unwanted in article_body.find_all(['script', 'style', 'nav', 'aside', 'footer', 'header', 'iframe', 'noscript']):
                        unwanted.decompose()
                    
                    for unwanted_class in ['advertisement', 'social-share', 'comments', 'related-posts', 'sidebar']:
                        for elem in article_body.find_all(class_=lambda x: x and unwanted_class in str(x).lower()):
                            elem.decompose()
                    
                    paragraphs = article_body.find_all('p')
                    if paragraphs:
                        text_parts = []
                        for p in paragraphs:
                            p_text = p.get_text(separator=' ', strip=True)
                            if len(p_text) > 30:
                                text_parts.append(p_text)
                        
                        if text_parts:
                            text = ' '.join(text_parts)
                        else:
                            text = article_body.get_text(separator=' ', strip=True)
                    else:
                        text = article_body.get_text(separator=' ', strip=True)
                    
                    text = re.sub(r'\s+', ' ', text)
                    text = re.sub(r'\n+', '\n', text)
                    text = text.strip()
                    
                    if len(text) > 200:
                        return text[:config.MAX_ARTICLE_TEXT_LENGTH]
                        
            except Exception:
                continue
        
        try:
            all_paragraphs = soup.find_all('p')
            if all_paragraphs and len(all_paragraphs) >= 3:
                text_parts = []
                for p in all_paragraphs[:20]:
                    p_text = p.get_text(separator=' ', strip=True)
                    if len(p_text) > 50:
                        text_parts.append(p_text)
                
                if text_parts:
                    text = ' '.join(text_parts)
                    text = re.sub(r'\s+', ' ', text)
                    if len(text) > 200:
                        return text[:config.MAX_ARTICLE_TEXT_LENGTH]
        except Exception:
            pass
        
        return fallback_summary
    
    @staticmethod
    def extract_metadata(soup: BeautifulSoup) -> Dict[str, str]:
        metadata = {
            'title': '',
            'description': '',
            'author': '',
            'published_date': '',
            'og_title': '',
            'og_description': '',
            'twitter_title': '',
            'twitter_description': ''
        }
        
        if not soup:
            return metadata
        
        try:
            title_tag = soup.find('title')
            if title_tag:
                metadata['title'] = title_tag.get_text().strip()
            
            description_tag = soup.find('meta', attrs={'name': 'description'})
            if description_tag and description_tag.get('content'):
                metadata['description'] = description_tag['content'].strip()
            
            author_tag = soup.find('meta', attrs={'name': 'author'})
            if author_tag and author_tag.get('content'):
                metadata['author'] = author_tag['content'].strip()
            
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                metadata['og_title'] = og_title['content'].strip()
            
            og_desc = soup.find('meta', property='og:description')
            if og_desc and og_desc.get('content'):
                metadata['og_description'] = og_desc['content'].strip()
            
            twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
            if twitter_title and twitter_title.get('content'):
                metadata['twitter_title'] = twitter_title['content'].strip()
            
            twitter_desc = soup.find('meta', attrs={'name': 'twitter:description'})
            if twitter_desc and twitter_desc.get('content'):
                metadata['twitter_description'] = twitter_desc['content'].strip()
                
        except Exception:
            pass
        
        return metadata


class ImageExtractor:
    
    def __init__(self):
        self.url_processor = ImageURLProcessor()
        self.url_normalizer = URLNormalizer()
    
    def extract_candidates(
        self,
        soup: BeautifulSoup,
        entry: Dict,
        base_url: str
    ) -> List[Tuple[str, str, int]]:
        candidates = []
        
        if not soup:
            urls = self._extract_from_rss(entry, base_url)
            return [(url, 'rss', 7) for url in urls]
        
        try:
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                url = self._process_url(og_image['content'], base_url)
                if url:
                    score = self.url_processor.get_priority_score(url, 'og:image')
                    candidates.append((url, 'og:image', score))
        except Exception:
            pass
        
        try:
            twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
            if twitter_image and twitter_image.get('content'):
                url = self._process_url(twitter_image['content'], base_url)
                if url:
                    score = self.url_processor.get_priority_score(url, 'twitter:image')
                    candidates.append((url, 'twitter:image', score))
        except Exception:
            pass
        
        try:
            article_tag = soup.find('article')
            if article_tag:
                first_img = article_tag.find('img')
                if first_img:
                    img_src = self._best_img_source(first_img)
                    if img_src:
                        url = self._process_url(img_src, base_url)
                        if url:
                            score = self.url_processor.get_priority_score(url, 'article-img')
                            candidates.append((url, 'article-img', score))
        except Exception:
            pass
        
        try:
            main_img = soup.find('img', class_=lambda x: x and ('featured' in str(x).lower() or 'hero' in str(x).lower()))
            if main_img:
                img_src = self._best_img_source(main_img)
                if img_src:
                    url = self._process_url(img_src, base_url)
                    if url:
                        score = self.url_processor.get_priority_score(url, 'featured-img')
                        candidates.append((url, 'featured-img', score + 5))
        except Exception:
            pass
        
        try:
            media_content = self._entry_value(entry, 'media_content', [])
            if media_content:
                for idx, media in enumerate(media_content[:5]):
                    if url := media.get('url'):
                        url = self._process_url(url, base_url)
                        if url:
                            score = 7 - idx
                            candidates.append((url, 'rss-media', score))
        except Exception:
            pass
        
        try:
            enclosures = self._entry_value(entry, 'enclosures', [])
            if enclosures:
                for idx, enc in enumerate(enclosures[:3]):
                    if 'image' in enc.get('type', '') and enc.get('href'):
                        url = self._process_url(enc['href'], base_url)
                        if url:
                            score = 5 - idx
                            candidates.append((url, 'rss-enclosure', score))
        except Exception:
            pass
        
        try:
            all_images = soup.find_all('img', limit=10)
            for img in all_images:
                img_src = self._best_img_source(img)
                if img_src:
                    url = self._process_url(img_src, base_url)
                    if url and not any(url == c[0] for c in candidates):
                        score = self.url_processor.get_priority_score(url, 'page-img')
                        candidates.append((url, 'page-img', score))
        except Exception:
            pass
        
        candidates.sort(key=lambda x: x[2], reverse=True)
        
        seen = set()
        unique_candidates = []
        for url, source, priority in candidates:
            if url not in seen:
                seen.add(url)
                unique_candidates.append((url, source, priority))
        
        return unique_candidates
    
    def _extract_from_rss(self, entry: Dict, base_url: str) -> List[str]:
        candidates = []
        
        try:
            media_content = self._entry_value(entry, 'media_content', [])
            if media_content:
                for media in media_content[:5]:
                    if url := media.get('url'):
                        url = self._process_url(url, base_url)
                        if url:
                            candidates.append(url)
        except Exception:
            pass
        
        try:
            enclosures = self._entry_value(entry, 'enclosures', [])
            if enclosures:
                for enc in enclosures[:3]:
                    if 'image' in enc.get('type', '') and enc.get('href'):
                        url = self._process_url(enc['href'], base_url)
                        if url:
                            candidates.append(url)
        except Exception:
            pass
        
        direct_image = self._entry_value(entry, 'image_url') or self._entry_value(entry, 'image')
        if isinstance(direct_image, dict):
            direct_image = direct_image.get('href') or direct_image.get('url')
        if direct_image:
            processed = self._process_url(str(direct_image), base_url)
            if processed:
                candidates.insert(0, processed)

        return list(dict.fromkeys(candidates))

    @staticmethod
    def _entry_value(entry, key: str, default=None):
        if isinstance(entry, dict):
            return entry.get(key, default)
        return getattr(entry, key, default)

    @staticmethod
    def _best_img_source(img) -> Optional[str]:
        """Выбрать крупнейший вариант из lazy/srcset либо обычный src."""
        srcset = img.get('srcset') or img.get('data-srcset')
        if srcset:
            variants = []
            for item in srcset.split(','):
                parts = item.strip().split()
                if not parts:
                    continue
                width = 0
                if len(parts) > 1 and parts[-1].lower().endswith('w'):
                    try:
                        width = int(parts[-1][:-1])
                    except ValueError:
                        pass
                variants.append((width, parts[0]))
            if variants:
                return max(variants, key=lambda variant: variant[0])[1]
        return (
            img.get('data-src')
            or img.get('data-lazy-src')
            or img.get('data-original')
            or img.get('src')
        )
    
    def _process_url(self, url: str, base_url: str) -> Optional[str]:
        try:
            full_url = urljoin(base_url, url)
            
            full_url = self.url_normalizer.clean_url(full_url)
            
            if not self.url_normalizer.is_valid_http_url(full_url):
                return None
            
            if self.url_processor.is_likely_logo(full_url):
                return None
            
            return self.url_processor.extract_full_size_url(full_url)
            
        except Exception:
            return None


class ContentParser:
    
    def __init__(self):
        print("📖 [PARSER] Content Parser v2.0 инициализирован")
        
        self.url_normalizer = URLNormalizer()
        self.article_extractor = ArticleExtractor()
        self.image_extractor = ImageExtractor()
        self.stats = ParserStats()
        
        self.user_agent = getattr(config, 'PARSER_USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        print("✅ [PARSER] Ready")
    
    async def get_article_content(
        self,
        url: str,
        entry: Dict,
        session: aiohttp.ClientSession
    ) -> Dict[str, Optional[str]]:
        soup, final_url = await self._fetch_and_parse_page(url, session)
        
        fallback_summary = entry.get('summary', '') or entry.get('description', '')
        article_text = self.article_extractor.extract_text(soup, fallback_summary)
        
        if article_text and len(article_text) > 200:
            self.stats.record_text_extraction()
        
        candidates = self.image_extractor.extract_candidates(soup, entry, final_url)
        image_url = await self._validate_image_candidates(
            candidates,
            session,
            referer=final_url,
        )
        
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
        try:
            soup, final_url = await self._fetch_and_parse_page(link, session)
            
            if not soup:
                print(f"⚠️  [PARSER] Не удалось загрузить страницу: {link[:60]}")
                return ""
            
            article_text = self.article_extractor.extract_text(soup, fallback_summary='')
            
            if article_text and len(article_text) > 100:
                self.stats.record_text_extraction()
                print(f"✅ [PARSER] Извлечено {len(article_text)} символов из {link[:60]}")
                return article_text
            else:
                print(f"⚠️  [PARSER] Текст статьи слишком короткий: {len(article_text)} символов")
                return ""
        
        except Exception as e:
            self.stats.record_error('parse_article')
            print(f"❌ [PARSER] Ошибка parse_article для {link[:60]}: {e}")
            return ""
    
    def find_best_image(self, entry: Dict) -> Optional[str]:
        try:
            base_url = entry.get('link', '')
            
            candidates = self.image_extractor._extract_from_rss(entry, base_url)
            
            if candidates:
                print(f"🖼️  [PARSER] Найдено изображение: {candidates[0][:70]}")
                return candidates[0]
            else:
                return None
                
        except Exception as e:
            self.stats.record_error('find_best_image')
            print(f"❌ [PARSER] Ошибка find_best_image: {e}")
            return None
    
    async def download_image(
        self,
        image_url: str,
        session: aiohttp.ClientSession
    ) -> Optional[bytes]:
        if not image_url:
            return None
        
        try:
            print(f"📥 [PARSER] Скачиваю изображение: {image_url[:70]}")
            
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Referer': image_url,
                'DNT': '1'
            }
            
            async with session.get(
                image_url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=config.IMAGE_CHECK_TIMEOUT)
            ) as response:
                
                if response.status != 200:
                    print(f"❌ [PARSER] HTTP {response.status} при загрузке изображения")
                    self.stats.record_image_validation(False)
                    return None
                
                content_type = response.headers.get('Content-Type', '').lower()
                if not any(img_type in content_type for img_type in ['image/', 'octet-stream']):
                    print(f"⚠️  [PARSER] Неверный Content-Type: {content_type}")
                    self.stats.record_image_validation(False)
                    return None
                
                image_data = await response.read()
                
                if not image_data or len(image_data) < 100:
                    print(f"⚠️  [PARSER] Пустое или слишком маленькое изображение")
                    self.stats.record_image_validation(False)
                    return None
                
                try:
                    img = Image.open(io.BytesIO(image_data))
                    width, height = img.size
                    
                    if width >= config.MIN_IMAGE_WIDTH and height >= config.MIN_IMAGE_HEIGHT:
                        print(f"✅ [PARSER] Изображение валидно: {width}x{height}px, {len(image_data) // 1024}KB")
                        self.stats.record_image_validation(True)
                        return image_data
                    else:
                        print(f"📏 [PARSER] Изображение слишком маленькое: {width}x{height}px")
                        self.stats.record_image_validation(False)
                        return None
                
                except Exception as e:
                    print(f"⚠️  [PARSER] Не удалось открыть изображение: {type(e).__name__}")
                    self.stats.record_image_validation(False)
                    return None
                
        except asyncio.TimeoutError:
            print(f"⏱️  [PARSER] Timeout при загрузке изображения")
            self.stats.record_error('download_timeout')
            self.stats.record_image_validation(False)
            return None
        except aiohttp.ClientError as e:
            print(f"🕸️  [PARSER] HTTP ошибка при загрузке: {type(e).__name__}")
            self.stats.record_error('download_client_error')
            self.stats.record_image_validation(False)
            return None
        except Exception as e:
            print(f"❌ [PARSER] Ошибка download_image: {e}")
            self.stats.record_error('download_unknown')
            self.stats.record_image_validation(False)
            return None
    
    async def _fetch_and_parse_page(
        self,
        url: str,
        session: aiohttp.ClientSession
    ) -> Tuple[Optional[BeautifulSoup], str]:
        try:
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
                allow_redirects=True
            ) as response:
                
                if response.status != 200:
                    print(f"⚠️  [PARSER] HTTP {response.status}: {url[:60]}")
                    self.stats.record_page_fetch(False)
                    return None, url
                
                final_url = str(response.url)
                
                content_type = response.headers.get('Content-Type', '').lower()
                if 'text/html' not in content_type and 'application/xhtml' not in content_type:
                    print(f"⚠️  [PARSER] Не HTML контент: {content_type}")
                    self.stats.record_page_fetch(False)
                    return None, url
                
                try:
                    html_text = await response.text()
                except UnicodeDecodeError:
                    html_bytes = await response.read()
                    for encoding in ['utf-8', 'windows-1251', 'iso-8859-1', 'cp1252']:
                        try:
                            html_text = html_bytes.decode(encoding)
                            break
                        except:
                            continue
                    else:
                        html_text = html_bytes.decode('utf-8', errors='ignore')
                
                if len(html_text) < 100:
                    print(f"⚠️  [PARSER] HTML слишком короткий: {len(html_text)} байт")
                    self.stats.record_page_fetch(False)
                    return None, url
                
                try:
                    soup = BeautifulSoup(html_text, 'lxml')
                except Exception:
                    try:
                        soup = BeautifulSoup(html_text, 'html.parser')
                    except Exception as e:
                        print(f"⚠️  [PARSER] Ошибка парсинга BeautifulSoup: {e}")
                        self.stats.record_page_fetch(False)
                        return None, url
                
                self.stats.record_page_fetch(True)
                return soup, final_url
                
        except asyncio.TimeoutError:
            print(f"⏱️  [PARSER] Timeout загрузки: {url[:60]}")
            self.stats.record_error('fetch_timeout')
            self.stats.record_page_fetch(False)
        except aiohttp.ClientError as e:
            print(f"🕸️  [PARSER] HTTP ошибка {url[:50]}: {type(e).__name__}")
            self.stats.record_error('fetch_client_error')
            self.stats.record_page_fetch(False)
        except Exception as e:
            print(f"❌ [PARSER] Ошибка парсинга {url[:50]}: {e}")
            self.stats.record_error('fetch_unknown')
            self.stats.record_page_fetch(False)
        
        return None, url
    
    async def _validate_image_candidates(
        self,
        candidates: List[Tuple[str, str, int]],
        session: aiohttp.ClientSession,
        referer: Optional[str] = None,
    ) -> Optional[str]:
        if not candidates:
            return None
        
        print(f"🖼️  [IMG] Проверяю {len(candidates)} кандидатов...")
        
        for idx, (url, source, priority) in enumerate(candidates[:5]):
            try:
                headers = {
                    'User-Agent': self.user_agent,
                    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                    'Referer': referer or url
                }
                
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=config.IMAGE_CHECK_TIMEOUT)
                ) as response:
                    
                    if response.status != 200:
                        continue
                    
                    content_type = response.headers.get('Content-Type', '').lower()
                    if not any(img_type in content_type for img_type in ['image/', 'octet-stream']):
                        continue

                    max_validation_bytes = int(
                        getattr(config, 'MAX_IMAGE_SIZE_MB', 10)
                    ) * 1024 * 1024
                    declared_length = response.headers.get('Content-Length')
                    if (
                        declared_length
                        and declared_length.isdigit()
                        and int(declared_length) > max_validation_bytes
                    ):
                        continue

                    image_data = await self._read_limited_response(
                        response,
                        max_validation_bytes,
                    )
                    if not image_data or len(image_data) < 100:
                        continue
                    
                    try:
                        img = Image.open(io.BytesIO(image_data))
                        img.load()
                        width, height = img.size
                        
                        if width >= config.MIN_IMAGE_WIDTH and height >= config.MIN_IMAGE_HEIGHT:
                            print(f"✅ [IMG] ВАЛИДНОЕ #{idx + 1} ({source}, priority={priority}): {url[:70]} ({width}x{height})")
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

    @staticmethod
    async def _read_limited_response(response, max_bytes: int) -> Optional[bytes]:
        """Прочитать все сетевые chunks до EOF, не превышая лимит."""
        chunks = []
        total = 0
        async for chunk in response.content.iter_chunked(64 * 1024):
            total += len(chunk)
            if total > max_bytes:
                return None
            chunks.append(chunk)
        return b''.join(chunks)
    
    def get_stats(self) -> Dict:
        return self.stats.get_summary()
    
    def print_stats(self):
        self.stats.print_stats()


__all__ = ['ContentParser', 'URLNormalizer', 'ImageExtractor', 'ArticleExtractor']