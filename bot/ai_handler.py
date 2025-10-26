# bot/ai_handler.py
import asyncio
import hashlib
import time
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
import google.generativeai as genai
from openai import OpenAI
from .config import config


class AIProviderStats:
    """Статистика по AI провайдерам для умного выбора"""
    
    def __init__(self):
        self.stats = {
            'gemini': {'success': 0, 'failures': 0, 'total_time': 0.0, 'last_success': None},
            'openai': {'success': 0, 'failures': 0, 'total_time': 0.0, 'last_success': None}
        }
    
    def record_success(self, provider: str, elapsed_time: float):
        """Запись успешного вызова"""
        self.stats[provider]['success'] += 1
        self.stats[provider]['total_time'] += elapsed_time
        self.stats[provider]['last_success'] = datetime.now()
    
    def record_failure(self, provider: str):
        """Запись неудачного вызова"""
        self.stats[provider]['failures'] += 1
    
    def get_success_rate(self, provider: str) -> float:
        """Процент успеха провайдера"""
        total = self.stats[provider]['success'] + self.stats[provider]['failures']
        if total == 0:
            return 1.0
        return self.stats[provider]['success'] / total
    
    def get_avg_time(self, provider: str) -> float:
        """Среднее время ответа"""
        if self.stats[provider]['success'] == 0:
            return 0.0
        return self.stats[provider]['total_time'] / self.stats[provider]['success']
    
    def get_preferred_provider(self) -> str:
        """Определяет лучший провайдер на основе статистики"""
        gemini_score = self.get_success_rate('gemini') * 1.2  # Приоритет Gemini
        openai_score = self.get_success_rate('openai')
        
        # Если Gemini работает хотя бы на 70% - используем его
        if gemini_score >= 0.7:
            return 'gemini'
        
        # Иначе выбираем лучший
        return 'gemini' if gemini_score >= openai_score else 'openai'
    
    def print_summary(self):
        """Вывод статистики"""
        print("\n📊 [AI STATS] Статистика провайдеров:")
        for provider, data in self.stats.items():
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
        if not text or len(text.strip()) < 50:
            return False, "Ответ слишком короткий"
        
        # Проверка наличия ключевых элементов
        required_patterns = [
            ('**', 'Отсутствует форматирование заголовка'),
            ('#', 'Отсутствуют хэштеги'),
        ]
        
        for pattern, error in required_patterns:
            if pattern not in text:
                return False, error
        
        # Проверка баланса markdown символов
        for char in ['*', '_', '`']:
            if text.count(char) % 2 != 0:
                return False, f"Несбалансированные markdown символы: {char}"
        
        # Проверка что это не английский текст (должен быть русский)
        cyrillic_chars = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
        if cyrillic_chars < len(text) * 0.3:  # Минимум 30% кириллицы
            return False, "Ответ не на русском языке"
        
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
        
        # Очистка старых записей
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
    """
    
    def __init__(self):
        # Инициализация провайдеров
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.gemini_model = genai.GenerativeModel(config.GEMINI_MODEL)
        self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
        
        # Вспомогательные компоненты
        self.stats = AIProviderStats()
        self.validator = ResponseValidator()
        self.cache = SimpleCache(ttl_seconds=3600)
        
        # Rate limiting
        self._last_request_time = 0
        self._min_request_interval = 1.0  # Минимум 1 секунда между запросами
        
        print("🤖 [AI] Handler инициализирован (Gemini + OpenAI)")
    
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
        # Проверка входных данных
        if not text or len(text.strip()) < 100:
            print("⚠️  [AI] Текст слишком короткий для анализа")
            return None
        
        # Проверка кэша
        cached = self.cache.get(title, text)
        if cached:
            print("⚡ [AI] Ответ получен из кэша")
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
        fallback = 'openai' if provider == 'gemini' else 'gemini'
        print(f"🔄 [AI] Переключение на {fallback.upper()}")
        
        result = await self._try_provider(fallback, title, text, category_emoji)
        if result:
            summary, elapsed = result
            self.stats.record_success(fallback, elapsed)
            self.cache.set(title, text, summary)
            return summary, fallback
        
        # Оба провайдера не сработали
        print("❌ [AI] Все провайдеры недоступны")
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
            if provider == 'gemini':
                summary = await self._call_gemini(title, text, emoji)
            else:
                summary = await self._call_openai(title, text, emoji)
            
            elapsed = time.time() - start_time
            
            # Валидация ответа
            is_valid, error = self.validator.validate(summary)
            if not is_valid:
                print(f"⚠️  [AI] Невалидный ответ от {provider}: {error}")
                self.stats.record_failure(provider)
                return None
            
            print(f"✅ [AI] {provider.upper()} успешно ({elapsed:.2f}s)")
            return summary, elapsed
            
        except Exception as e:
            error_str = str(e)
            print(f"❌ [AI] Ошибка {provider.upper()}: {error_str[:100]}")
            self.stats.record_failure(provider)
            return None
    
    async def _call_gemini(self, title: str, text: str, emoji: str) -> str:
        """Вызов Gemini API"""
        prompt = config.ai_prompt_template.format(emoji=emoji, title=title)
        full_prompt = f"{prompt}\n\nТЕКСТ СТАТЬИ ДЛЯ АНАЛИЗА:\n{text[:config.MAX_ARTICLE_TEXT_LENGTH]}"
        
        # Retry logic для Gemini
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
                print(f"⏱️  [AI] Gemini timeout (попытка {attempt + 1}/{config.AI_MAX_RETRIES})")
                if attempt < config.AI_MAX_RETRIES - 1:
                    await asyncio.sleep(config.AI_BACKOFF_FACTOR * (2 ** attempt))
                else:
                    raise
            
            except Exception as e:
                error_str = str(e).lower()
                
                # Критические ошибки - сразу выходим
                if any(kw in error_str for kw in ['404', 'not found', 'quota', '429', 'rate limit']):
                    raise
                
                # Остальные ошибки - retry
                if attempt < config.AI_MAX_RETRIES - 1:
                    await asyncio.sleep(config.AI_BACKOFF_FACTOR * (2 ** attempt))
                else:
                    raise
    
    async def _call_openai(self, title: str, text: str, emoji: str) -> str:
        """Вызов OpenAI API"""
        prompt = config.ai_prompt_template.format(emoji=emoji, title=title)
        user_prompt = f"Заголовок: {title}\n\nПолный текст статьи:\n{text[:config.MAX_ARTICLE_TEXT_LENGTH]}"
        
        loop = asyncio.get_event_loop()
        
        # Retry logic для OpenAI
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
                print(f"⏱️  [AI] OpenAI timeout (попытка {attempt + 1}/{config.AI_MAX_RETRIES})")
                if attempt < config.AI_MAX_RETRIES - 1:
                    await asyncio.sleep(config.AI_BACKOFF_FACTOR * (2 ** attempt))
                else:
                    raise
            
            except Exception as e:
                if attempt < config.AI_MAX_RETRIES - 1:
                    await asyncio.sleep(config.AI_BACKOFF_FACTOR * (2 ** attempt))
                else:
                    raise
    
    def _sanitize_markdown(self, text: str) -> str:
        """
        Умная санитизация markdown для предотвращения ошибок парсинга
        Удаляет несбалансированные символы
        """
        if not text:
            return text
        
        # Для каждого markdown символа проверяем баланс
        for char in ['*', '_', '`', '~']:
            # Тройные символы (***bold italic***)
            count_triple = text.count(char * 3)
            if count_triple % 2 != 0:
                # Удаляем последний нечётный тройной символ
                pos = text.rfind(char * 3)
                if pos != -1:
                    text = text[:pos] + text[pos + 3:]
            
            # Двойные символы (**bold**)
            count_double = text.count(char * 2)
            if count_double % 2 != 0:
                pos = text.rfind(char * 2)
                if pos != -1:
                    text = text[:pos] + text[pos + 2:]
            
            # Одинарные символы (*italic*)
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
                'success_rate': f"{self.stats.get_success_rate('gemini') * 100:.1f}%",
                'avg_time': f"{self.stats.get_avg_time('gemini'):.2f}s",
                'total_requests': self.stats.stats['gemini']['success'] + self.stats.stats['gemini']['failures']
            },
            'openai': {
                'success_rate': f"{self.stats.get_success_rate('openai') * 100:.1f}%",
                'avg_time': f"{self.stats.get_avg_time('openai'):.2f}s",
                'total_requests': self.stats.stats['openai']['success'] + self.stats.stats['openai']['failures']
            },
            'preferred_provider': self.stats.get_preferred_provider(),
            'cache_size': len(self.cache.cache)
        }
    
    def print_stats(self):
        """Вывод статистики в консоль"""
        self.stats.print_summary()
        print(f"  Cache: {len(self.cache.cache)} записей")
        print(f"  Preferred: {self.stats.get_preferred_provider().upper()}")