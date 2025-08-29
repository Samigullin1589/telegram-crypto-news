# bot/content_parser.py
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from PIL import Image
import io
from . import config

class ContentParser:
    async def get_article_content(self, url, entry, session):
        soup, final_url = await self._fetch_and_parse_page(url, session)
        article_text = self._extract_article_text(soup, entry)
        image_candidates = self._extract_image_candidates(soup, entry, final_url)
        image_url = await self._get_valid_image_url(image_candidates, session)
        return {'text': article_text, 'image_url': image_url, 'final_url': final_url}

    async def _fetch_and_parse_page(self, url, session):
        try:
            async with session.get(url, timeout=15) as response:
                response.raise_for_status()
                final_url = str(response.url)
                html_text = await response.text()
                soup = BeautifulSoup(html_text, 'lxml')
                return soup, final_url
        except Exception as e:
            print(f"🕸️ [WARN] Не удалось скачать страницу {url}: {e}")
            return None, url

    def _extract_article_text(self, soup, entry):
        if not soup: return entry.get('summary', '')
        article_body = soup.find('article') or soup.find('div', class_='post-content') or soup.find('body')
        if article_body:
            for element in (article_body.find_all("script") + article_body.find_all("style")):
                element.decompose()
            parsed_text = ' '.join(article_body.get_text().split())
            if parsed_text: return parsed_text[:12000]
        return entry.get('summary', '')

    def _extract_image_candidates(self, soup, entry, final_url):
        image_candidates = []
        if not soup: return image_candidates
        article_body = soup.find('article') or soup.find('div', class_='post-content') or soup.find('body')
        if article_body:
            for img_tag in article_body.find_all('img', src=True):
                if src := img_tag.get('src'):
                    image_candidates.append(urljoin(final_url, src))
        if 'media_content' in entry and entry.media_content:
            if media_url := entry.media_content[0].get('url'):
                image_candidates.append(urljoin(final_url, media_url))
        elif 'enclosures' in entry and entry.enclosures:
            for enc in entry.enclosures:
                if 'image' in enc.type and enc.href:
                    image_candidates.append(urljoin(final_url, enc.href))
        if og_image := soup.find('meta', property='og:image'):
            if content := og_image.get('content'):
                image_candidates.append(urljoin(final_url, content))
        return image_candidates

    async def _get_valid_image_url(self, image_candidates, session):
        for url in image_candidates:
            if not url or self._is_likely_logo(url): continue
            try:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200: continue
                    image_data = await response.content.read(4096)
                    if not image_data: continue
                    img = Image.open(io.BytesIO(image_data))
                    if img.width >= config.MIN_IMAGE_WIDTH and img.height >= config.MIN_IMAGE_HEIGHT:
                        print(f"🖼️ [IMG] Найдено подходящее изображение: {url} ({img.width}x{img.height})")
                        return url
                    else:
                        print(f"🖼️ [IMG] Изображение отклонено (слишком маленькое): {url} ({img.width}x{img.height})")
            except Exception as e:
                print(f"🖼️ [IMG] Не удалось проверить изображение {url}: {e}")
                continue
        return None

    def _is_likely_logo(self, image_url):
        if not image_url: return True
        return any(keyword in image_url.lower() for keyword in ['logo', 'brand', 'icon'])