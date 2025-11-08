# bot/news/http_client.py
"""
HTTP Client for News Fetching
HTTP клиент для получения новостей
"""

import asyncio
import logging
from typing import Optional, Tuple

import aiohttp

logger = logging.getLogger(__name__)


class NewsHttpClient:
    """
    HTTP клиент для получения новостей
    
    Особенности:
    - Настроенные таймауты
    - Правильные заголовки User-Agent
    - Обработка различных типов контента
    """
    
    def __init__(self):
        """Инициализация HTTP клиента"""
        self.timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/131.0.0.0 Safari/537.36'
            ),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    async def fetch(self, url: str, source_name: str = 'Unknown') -> Tuple[Optional[str], str]:
        """
        Получение контента по URL
        
        Args:
            url: URL для получения
            source_name: Название источника (для логирования)
            
        Returns:
            Tuple (content, content_type) или (None, '') при ошибке
        """
        try:
            async with aiohttp.ClientSession(
                timeout=self.timeout,
                headers=self.headers
            ) as session:
                async with session.get(url) as response:
                    # Проверка статуса
                    if response.status != 200:
                        logger.warning(
                            f"[{source_name}] HTTP {response.status} for {url}"
                        )
                        return None, ''
                    
                    # Получение типа контента
                    content_type = response.headers.get('Content-Type', '')
                    
                    # Получение контента
                    content = await response.text()
                    
                    logger.debug(
                        f"[{source_name}] Fetched {len(content)} bytes "
                        f"(type: {content_type})"
                    )
                    
                    return content, content_type
        
        except asyncio.TimeoutError:
            logger.warning(f"[{source_name}] Timeout for {url}")
            return None, ''
        
        except aiohttp.ClientError as e:
            logger.warning(f"[{source_name}] Network error for {url}: {e}")
            return None, ''
        
        except Exception as e:
            logger.error(f"[{source_name}] Unexpected error for {url}: {e}")
            return None, ''


__all__ = ['NewsHttpClient']