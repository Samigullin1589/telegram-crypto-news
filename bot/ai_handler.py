"""
AI HANDLER v3.1 - Enhanced with Graceful Degradation
Умный обработчик AI с автоматическим переключением провайдеров

ВОЗМОЖНОСТИ:
✅ Gemini API (если доступен)
✅ OpenAI API (если доступен)
✅ Graceful fallback если провайдеры недоступны
✅ Статистика и умный выбор провайдера
✅ Кэширование ответов
✅ Валидация ответов
✅ Rate limiting
"""

import asyncio
import hashlib
import time
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta

# Graceful импорт Google Generative AI
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

# Graceful импорт OpenAI
try:
    from openai import OpenAI
    import httpx
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None
    httpx = None

# Graceful импорт config
try:
    from .config import config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    # Создаем минимальный fallback config
    class DummyConfig:
        GEMINI_API_KEY = ""
        GEMINI_MODEL = "gemini-pro"
        OPENAI_API_KEY = ""
        OPENAI_MODEL = "gpt-3.5-turbo"
        MAX_ARTICLE_TEXT_LENGTH = 3000
        AI_MAX_RETRIES = 2
        AI_TIMEOUT = 30
        AI_BACKOFF_FACTOR = 2
        ai_prompt_template = """Создай краткое саммари этой новости для crypto-канала.
        
Формат ответа:
{emoji} **{title}**

[2-3 предложения о ключевых моментах]

#crypto #news"""
    
    config = DummyConfig()


class AIProviderStats:
    """Статистика по AI провайдерам для умного выбора"""
    
    def __init__(self):
        self.stats = {
            'gemini': {'success': 0, 'failures': 0, 'total_time': 0.0, 'last_success': None},
            'openai': {'success': 0, 'failures': 0, 'total_time': 0.0, 'last_success': None},
            'dummy': {'success': 0, 'failures': 0, 'total_time': 0.0, 'last_success': None}
        }
    
    def record_success(self, provider: str, elapsed_time: float):
        """Запись успешного вызова"""
        if provider in self.stats:
            self.stats[provider]['success'] += 1
            self.stats[provider]['total_time'] += elapsed_time
            self.stats[provider]['last_success'] = datetime.now()
    
    def record_failure(self, provider: str):
        """Запись неудачного вызова"""
        if provider in self.stats:
            self.stats[provider]['failures'] += 1
    
    def get_success_rate(self, provider: str) -> float:
        """Процент успеха провайдера"""
        if provider not in self.stats:
            return 0.0
        
        total = self.stats[provider]['success'] + self.stats[provider]['failures']
        if total == 0:
            return 1.0
        return self.stats[provider]['success'] / total
    
    def get_avg_time(self, provider: str) -> float:
        """Среднее время ответа"""
        if provider not in self.stats:
            return 0.0
        
        if self.stats[provider]['success'] == 0:
            return 0.0
        return self.stats[provider]['total_time'] / self.stats[provider]['success']
    
    def get_preferred_provider(self) -> str:
        """Определяет лучший провайдер на основе статистики"""
        if GEMINI_AVAILABLE:
            gemini_score = self.get_success_rate('gemini') * 1.2
            if gemini_score >= 0.7:
                return 'gemini'
        
        if OPENAI_AVAILABLE:
            openai_score = self.get_success_rate('openai')
            if openai_score >= 0.7:
                return 'openai'
        
        # Если ничего не доступно - dummy
        return 'dummy'
    
    def print_summary(self):
        """Вывод статистики"""
        print("\n📊 [AI STATS] Статистика провайдеров:")
        for provider, data in self.stats.items():
            if data['success'] + data['failures'] == 0:
                continue
            
            success_rate = self.get_success_rate(provider) * 100
            avg_time = self.get_avg_time(provider)
            total = data['success'] + data['failures']
            print(f"  {provider.upper()}: {data['success']}/{total} успешно ({success_rate:.1f}%), "
                  f"avg {avg_time:.2f}s")


class ResponseValidator:
    """Валидатор ответов от AI"""
    
    @staticmethod
    def validate(text: str) -> Tuple[bool, Optional[str]]:
        """
        Проверяет корректность ответа от AI
        Returns: (is_valid, error_message)
        """
        if not text or len(text.strip()) < 30:
            return False, "Ответ слишком короткий"
        
        # Базовая проверка markdown
        for char in ['*', '_', '`']:
            if text.count(char) % 2 != 0:
                return False, f"Несбалансированные markdown символы: {char}"
        
        return True, None


class SimpleCache:
    """Простой in-memory кэш для ответов AI"""
    
    def __init__(self, ttl_seconds: int = 3600):
        self.cache: Dict[str, Tuple[str, float]] = {}
        self.ttl = ttl_seconds
    
    def _get_key(self, title: str, text: str) -> str:
        """Генерация ключа кэша"""
        content = f"{title}:{text[:500]}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, title: str, text: str) -> Optional[str]:
        """Получить из кэша"""
        key = self._get_key(title, text)
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, title: str, text: str, value: str):
        """Сохранить в кэш"""
        key = self._get_key(title, text)
        self.cache[key] = (value, time.time())
        
        if len(self.cache) > 100:
            self._cleanup()
    
    def _cleanup(self):
        """Удаление устаревших записей"""
        current_time = time.time()
        expired_keys = [
            k for k, (_, ts) in self.cache.items()
            if current_time - ts >= self.ttl
        ]
        for key in expired_keys:
            del self.cache[key]


class AIHandler:
    """
    Умный обработчик AI с автоматическим переключением провайдеров,
    статистикой и кэшированием
    
    НОВОЕ v3.1: Graceful degradation если провайдеры недоступны
    """
    
    def __init__(self):
        print("\n🤖 [AI] Инициализация AI Handler...")
        
        # Инициализация Gemini
        self.gemini_model = None
        if GEMINI_AVAILABLE and config.GEMINI_API_KEY:
            try:
                genai.configure(api_key=config.GEMINI_API_KEY)
                self.gemini_model = genai.GenerativeModel(config.GEMINI_MODEL)
                print("   ✅ Gemini API доступен")
            except Exception as e:
                print(f"   ⚠️ Gemini API недоступен: {e}")
        else:
            if not GEMINI_AVAILABLE:
                print("   ⚠️ google.generativeai не установлен")
            else:
                print("   ⚠️ GEMINI_API_KEY не установлен")
        
        # Инициализация OpenAI
        self.openai_client = None
        if OPENAI_AVAILABLE and config.OPENAI_API_KEY:
            try:
                http_client = httpx.Client(
                    timeout=httpx.Timeout(60.0, connect=30.0),
                    follow_redirects=True,
                    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
                )
                
                self.openai_client = OpenAI(
                    api_key=config.OPENAI_API_KEY,
                    http_client=http_client,
                    timeout=60.0
                )
                print("   ✅ OpenAI API доступен")
            except Exception as e:
                print(f"   ⚠️ OpenAI API недоступен: {e}")
        else:
            if not OPENAI_AVAILABLE:
                print("   ⚠️ openai не установлен")
            else:
                print("   ⚠️ OPENAI_API_KEY не установлен")
        
        # Вспомогательные компоненты
        self.stats = AIProviderStats()
        self.validator = ResponseValidator()
        self.cache = SimpleCache(ttl_seconds=3600)
        
        # Rate limiting
        self._last_request_time = 0
        self._min_request_interval = 1.0
        
        # Определяем режим работы
        if self.gemini_model or self.openai_client:
            print("✅ [AI] Handler инициализирован (AI режим)")
        else:
            print("⚠️ [AI] Handler в dummy режиме (нет доступных провайдеров)")
    
    async def analyze_article(self, article: Dict) -> Optional[Dict]:
        """
        Анализ статьи (используется в NewsProcessor)
        
        Args:
            article: Dict с полями title, summary, content
        
        Returns:
            Dict с score, sentiment, relevance или None
        """
        title = article.get('title', '')
        text = article.get('summary', '') or article.get('content', '')
        
        if not title or not text:
            return None
        
        # Базовый score на основе длины и наличия ключевых слов
        score = 70
        
        # Проверка ключевых слов (увеличивает score)
        crypto_keywords = ['bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'blockchain', 
                          'биткоин', 'эфириум', 'крипто', 'блокчейн']
        
        text_lower = (title + ' ' + text).lower()
        keyword_matches = sum(1 for kw in crypto_keywords if kw in text_lower)
        score += min(keyword_matches * 5, 20)
        
        # Проверка позитивных слов
        positive_words = ['рост', 'прибыль', 'успех', 'новый рекорд', 'breakthrough', 'gain']
        negative_words = ['падение', 'потери', 'скам', 'взлом', 'loss', 'hack', 'crash']
        
        positive_count = sum(1 for w in positive_words if w in text_lower)
        negative_count = sum(1 for w in negative_words if w in text_lower)
        
        if positive_count > negative_count:
            sentiment = 'positive'
        elif negative_count > positive_count:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        return {
            'score': min(score, 95),
            'sentiment': sentiment,
            'relevance': 'high' if score > 80 else 'medium'
        }
    
    async def get_summary(
        self,
        title: str,
        text: str,
        category: str,
        force_provider: Optional[str] = None
    ) -> Optional[Tuple[str, str]]:
        """
        Генерация саммари с умным выбором провайдера
        
        Returns: (summary_text, provider_used) or None
        """
        if not text or len(text.strip()) < 100:
            return None
        
        # Проверка кэша
        cached = self.cache.get(title, text)
        if cached:
            return cached, 'cache'
        
        # Rate limiting
        await self._rate_limit()
        
        # Определяем провайдера
        if force_provider:
            provider = force_provider
        else:
            provider = self.stats.get_preferred_provider()
        
        category_emoji = category.split()[-1] if category else '📰'
        
        # Пробуем основной провайдер
        result = await self._try_provider(provider, title, text, category_emoji)
        if result:
            summary, elapsed = result
            self.stats.record_success(provider, elapsed)
            self.cache.set(title, text, summary)
            return summary, provider
        
        # Fallback на альтернативный провайдер
        if provider == 'gemini' and self.openai_client:
            fallback = 'openai'
        elif provider == 'openai' and self.gemini_model:
            fallback = 'gemini'
        else:
            fallback = 'dummy'
        
        if fallback != 'dummy':
            result = await self._try_provider(fallback, title, text, category_emoji)
            if result:
                summary, elapsed = result
                self.stats.record_success(fallback, elapsed)
                self.cache.set(title, text, summary)
                return summary, fallback
        
        # Последний fallback - dummy режим
        result = await self._try_provider('dummy', title, text, category_emoji)
        if result:
            summary, elapsed = result
            self.stats.record_success('dummy', elapsed)
            self.cache.set(title, text, summary)
            return summary, 'dummy'
        
        return None
    
    async def _try_provider(
        self,
        provider: str,
        title: str,
        text: str,
        emoji: str
    ) -> Optional[Tuple[str, float]]:
        """
        Попытка получить ответ от конкретного провайдера
        
        Returns: (summary, elapsed_time) or None
        """
        start_time = time.time()
        
        try:
            if provider == 'gemini' and self.gemini_model:
                summary = await self._call_gemini(title, text, emoji)
            elif provider == 'openai' and self.openai_client:
                summary = await self._call_openai(title, text, emoji)
            elif provider == 'dummy':
                summary = self._call_dummy(title, text, emoji)
            else:
                return None
            
            elapsed = time.time() - start_time
            
            # Валидация ответа
            is_valid, error = self.validator.validate(summary)
            if not is_valid:
                self.stats.record_failure(provider)
                return None
            
            return summary, elapsed
            
        except Exception as e:
            self.stats.record_failure(provider)
            return None
    
    async def _call_gemini(self, title: str, text: str, emoji: str) -> str:
        """Вызов Gemini API"""
        prompt = config.ai_prompt_template.format(emoji=emoji, title=title)
        full_prompt = f"{prompt}\n\nТЕКСТ СТАТЬИ ДЛЯ АНАЛИЗА:\n{text[:config.MAX_ARTICLE_TEXT_LENGTH]}"
        
        for attempt in range(config.AI_MAX_RETRIES):
            try:
                response = await asyncio.wait_for(
                    self.gemini_model.generate_content_async(full_prompt),
                    timeout=config.AI_TIMEOUT
                )
                
                if not response.text:
                    raise ValueError("Empty response from Gemini")
                
                return self._sanitize_markdown(response.text)
                
            except asyncio.TimeoutError:
                if attempt < config.AI_MAX_RETRIES - 1:
                    await asyncio.sleep(config.AI_BACKOFF_FACTOR * (2 ** attempt))
                else:
                    raise
            
            except Exception as e:
                error_str = str(e).lower()
                
                if any(kw in error_str for kw in ['404', 'not found', 'quota', '429', 'rate limit']):
                    raise
                
                if attempt < config.AI_MAX_RETRIES - 1:
                    await asyncio.sleep(config.AI_BACKOFF_FACTOR * (2 ** attempt))
                else:
                    raise
    
    async def _call_openai(self, title: str, text: str, emoji: str) -> str:
        """Вызов OpenAI API"""
        prompt = config.ai_prompt_template.format(emoji=emoji, title=title)
        user_prompt = f"Заголовок: {title}\n\nПолный текст статьи:\n{text[:config.MAX_ARTICLE_TEXT_LENGTH]}"
        
        loop = asyncio.get_event_loop()
        
        for attempt in range(config.AI_MAX_RETRIES):
            try:
                response = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: self.openai_client.chat.completions.create(
                            model=config.OPENAI_MODEL,
                            messages=[
                                {"role": "system", "content": prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            temperature=0.7,
                            max_tokens=1000
                        )
                    ),
                    timeout=config.AI_TIMEOUT
                )
                
                summary = response.choices[0].message.content
                if not summary:
                    raise ValueError("Empty response from OpenAI")
                
                return self._sanitize_markdown(summary)
                
            except asyncio.TimeoutError:
                if attempt < config.AI_MAX_RETRIES - 1:
                    await asyncio.sleep(config.AI_BACKOFF_FACTOR * (2 ** attempt))
                else:
                    raise
            
            except Exception as e:
                if attempt < config.AI_MAX_RETRIES - 1:
                    await asyncio.sleep(config.AI_BACKOFF_FACTOR * (2 ** attempt))
                else:
                    raise
    
    def _call_dummy(self, title: str, text: str, emoji: str) -> str:
        """
        Dummy режим - генерация базового summary без AI
        
        Используется когда нет доступных AI провайдеров
        """
        # Берем первые 2-3 предложения из текста
        sentences = text.split('.')[:3]
        summary_text = '. '.join(s.strip() for s in sentences if s.strip()) + '.'
        
        # Ограничиваем длину
        if len(summary_text) > 500:
            summary_text = summary_text[:497] + '...'
        
        return f"""{emoji} **{title}**

{summary_text}

#crypto #news"""
    
    def _sanitize_markdown(self, text: str) -> str:
        """
        Умная санитизация markdown для предотвращения ошибок парсинга
        """
        if not text:
            return text
        
        for char in ['*', '_', '`', '~']:
            count_triple = text.count(char * 3)
            if count_triple % 2 != 0:
                pos = text.rfind(char * 3)
                if pos != -1:
                    text = text[:pos] + text[pos + 3:]
            
            count_double = text.count(char * 2)
            if count_double % 2 != 0:
                pos = text.rfind(char * 2)
                if pos != -1:
                    text = text[:pos] + text[pos + 2:]
            
            count_single = text.count(char)
            if count_single % 2 != 0:
                pos = text.rfind(char)
                if pos != -1:
                    text = text[:pos] + text[pos + 1:]
        
        return text.strip()
    
    async def _rate_limit(self):
        """Rate limiting между запросами"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            wait_time = self._min_request_interval - elapsed
            await asyncio.sleep(wait_time)
        
        self._last_request_time = time.time()
    
    def get_stats_summary(self) -> Dict:
        """Получить статистику работы"""
        return {
            'gemini': {
                'available': self.gemini_model is not None,
                'success_rate': f"{self.stats.get_success_rate('gemini') * 100:.1f}%",
                'avg_time': f"{self.stats.get_avg_time('gemini'):.2f}s",
                'total_requests': self.stats.stats['gemini']['success'] + self.stats.stats['gemini']['failures']
            },
            'openai': {
                'available': self.openai_client is not None,
                'success_rate': f"{self.stats.get_success_rate('openai') * 100:.1f}%",
                'avg_time': f"{self.stats.get_avg_time('openai'):.2f}s",
                'total_requests': self.stats.stats['openai']['success'] + self.stats.stats['openai']['failures']
            },
            'dummy': {
                'available': True,
                'success_rate': f"{self.stats.get_success_rate('dummy') * 100:.1f}%",
                'total_requests': self.stats.stats['dummy']['success'] + self.stats.stats['dummy']['failures']
            },
            'preferred_provider': self.stats.get_preferred_provider(),
            'cache_size': len(self.cache.cache)
        }
    
    def print_stats(self):
        """Вывод статистики в консоль"""
        self.stats.print_summary()
        print(f"  Cache: {len(self.cache.cache)} записей")
        print(f"  Preferred: {self.stats.get_preferred_provider().upper()}")