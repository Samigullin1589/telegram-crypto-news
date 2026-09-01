"""
AI HANDLER v3.2 - Enhanced with Translation Support
Умный обработчик AI с автоматическим переключением провайдеров и переводом

ВОЗМОЖНОСТИ:
✅ Gemini API (если доступен)
✅ OpenAI API (если доступен)
✅ Перевод текста (EN→RU, любые языки)
✅ Graceful fallback если провайдеры недоступны
✅ Статистика и умный выбор провайдера
✅ Кэширование ответов
✅ Валидация ответов
✅ Rate limiting
"""

import asyncio
import hashlib
import logging
import time
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

try:
    from openai import OpenAI
    import httpx
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None
    httpx = None

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
            GEMINI_API_KEY = ""
            GEMINI_MODEL = "gemini-pro"
            OPENAI_API_KEY = ""
            OPENAI_MODEL = "gpt-3.5-turbo"
            CHEAPVIBECODE_API_KEY = ""
            CHEAPVIBECODE_BASE_URL = "https://cheapvibecode.ru/v1"
            CHEAPVIBECODE_MODEL = ""
            MAX_ARTICLE_TEXT_LENGTH = 3000
            AI_MAX_RETRIES = 2
            AI_TIMEOUT = 30
            AI_BACKOFF_FACTOR = 2
            AI_MAX_TOKENS = 500
            AI_TRANSLATION_MAX_TOKENS = 800
            AI_TEMPERATURE = 0.3
            ai_prompt_template = """Создай краткое саммари этой новости для crypto-канала.
            
Формат ответа:
{emoji} **{title}**

[2-3 предложения о ключевых моментах]

#crypto #news"""
        
        config = DummyConfig()


class AIProviderStats:
    
    def __init__(self):
        self.stats = {
            'cheapvibecode': {'success': 0, 'failures': 0, 'total_time': 0.0, 'last_success': None, 'translations': 0},
            'gemini': {'success': 0, 'failures': 0, 'total_time': 0.0, 'last_success': None, 'translations': 0},
            'openai': {'success': 0, 'failures': 0, 'total_time': 0.0, 'last_success': None, 'translations': 0},
            'dummy': {'success': 0, 'failures': 0, 'total_time': 0.0, 'last_success': None, 'translations': 0}
        }
    
    def record_success(self, provider: str, elapsed_time: float, is_translation: bool = False):
        if provider in self.stats:
            self.stats[provider]['success'] += 1
            self.stats[provider]['total_time'] += elapsed_time
            self.stats[provider]['last_success'] = datetime.now()
            if is_translation:
                self.stats[provider]['translations'] += 1
    
    def record_failure(self, provider: str):
        if provider in self.stats:
            self.stats[provider]['failures'] += 1
    
    def get_success_rate(self, provider: str) -> float:
        if provider not in self.stats:
            return 0.0
        
        total = self.stats[provider]['success'] + self.stats[provider]['failures']
        if total == 0:
            return 1.0
        return self.stats[provider]['success'] / total
    
    def get_avg_time(self, provider: str) -> float:
        if provider not in self.stats:
            return 0.0
        
        if self.stats[provider]['success'] == 0:
            return 0.0
        return self.stats[provider]['total_time'] / self.stats[provider]['success']
    
    def get_preferred_provider(self) -> str:
        if (
            OPENAI_AVAILABLE
            and getattr(config, 'CHEAPVIBECODE_API_KEY', '')
            and getattr(config, 'CHEAPVIBECODE_MODEL', '')
        ):
            cheapvibecode_score = self.get_success_rate('cheapvibecode')
            if cheapvibecode_score >= 0.7:
                return 'cheapvibecode'

        if GEMINI_AVAILABLE and config.GEMINI_API_KEY:
            gemini_score = self.get_success_rate('gemini') * 1.2
            if gemini_score >= 0.7:
                return 'gemini'
        
        if OPENAI_AVAILABLE and config.OPENAI_API_KEY:
            openai_score = self.get_success_rate('openai')
            if openai_score >= 0.7:
                return 'openai'
        
        return 'dummy'
    
    def print_summary(self):
        print("\n📊 [AI STATS] Статистика провайдеров:")
        for provider, data in self.stats.items():
            if data['success'] + data['failures'] == 0:
                continue
            
            success_rate = self.get_success_rate(provider) * 100
            avg_time = self.get_avg_time(provider)
            total = data['success'] + data['failures']
            translations = data['translations']
            print(f"  {provider.upper()}: {data['success']}/{total} успешно ({success_rate:.1f}%), "
                  f"avg {avg_time:.2f}s, переводов: {translations}")


class ResponseValidator:
    
    @staticmethod
    def validate(text: str) -> Tuple[bool, Optional[str]]:
        if not text or len(text.strip()) < 30:
            return False, "Ответ слишком короткий"
        
        for char in ['*', '_', '`']:
            if text.count(char) % 2 != 0:
                return False, f"Несбалансированные markdown символы: {char}"
        
        return True, None
    
    @staticmethod
    def validate_translation(text: str, original_length: int) -> Tuple[bool, Optional[str]]:
        if not text or len(text.strip()) < 10:
            return False, "Перевод слишком короткий"
        
        if len(text) < original_length * 0.3:
            return False, "Перевод подозрительно короткий"
        
        if len(text) > original_length * 3:
            return False, "Перевод подозрительно длинный"
        
        return True, None


class SimpleCache:
    
    def __init__(self, ttl_seconds: int = 3600):
        self.cache: Dict[str, Tuple[str, float]] = {}
        self.ttl = ttl_seconds
    
    def _get_key(self, *args) -> str:
        content = ':'.join(str(arg) for arg in args)
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, *args) -> Optional[str]:
        key = self._get_key(*args)
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, *args):
        if len(args) < 2:
            return
        
        value = args[-1]
        key_parts = args[:-1]
        key = self._get_key(*key_parts)
        self.cache[key] = (value, time.time())
        
        if len(self.cache) > 200:
            self._cleanup()
    
    def _cleanup(self):
        current_time = time.time()
        expired_keys = [
            k for k, (_, ts) in self.cache.items()
            if current_time - ts >= self.ttl
        ]
        for key in expired_keys:
            del self.cache[key]


class AIHandler:
    
    def __init__(self):
        print("\n🤖 [AI] Инициализация AI Handler v3.2...")
        
        self.gemini_model = None
        if GEMINI_AVAILABLE and hasattr(config, 'GEMINI_API_KEY') and config.GEMINI_API_KEY:
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
        
        self.openai_client = None
        if OPENAI_AVAILABLE and hasattr(config, 'OPENAI_API_KEY') and config.OPENAI_API_KEY:
            try:
                http_client = httpx.Client(
                    timeout=httpx.Timeout(
                        float(config.AI_TIMEOUT),
                        connect=min(30.0, float(config.AI_TIMEOUT))
                    ),
                    follow_redirects=True,
                    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
                )
                
                self.openai_client = OpenAI(
                    api_key=config.OPENAI_API_KEY,
                    http_client=http_client,
                    timeout=float(config.AI_TIMEOUT)
                )
                print("   ✅ OpenAI API доступен")
            except Exception as e:
                print(f"   ⚠️ OpenAI API недоступен: {e}")
        else:
            if not OPENAI_AVAILABLE:
                print("   ⚠️ openai не установлен")
            else:
                print("   ⚠️ OPENAI_API_KEY не установлен")

        self.cheapvibecode_client = None
        if (
            OPENAI_AVAILABLE
            and getattr(config, 'CHEAPVIBECODE_API_KEY', '')
            and getattr(config, 'CHEAPVIBECODE_MODEL', '')
        ):
            try:
                http_client = httpx.Client(
                    timeout=httpx.Timeout(
                        float(config.AI_TIMEOUT),
                        connect=min(30.0, float(config.AI_TIMEOUT))
                    ),
                    follow_redirects=True,
                    limits=httpx.Limits(
                        max_keepalive_connections=5,
                        max_connections=10
                    )
                )

                self.cheapvibecode_client = OpenAI(
                    api_key=config.CHEAPVIBECODE_API_KEY,
                    base_url=config.CHEAPVIBECODE_BASE_URL,
                    http_client=http_client,
                    timeout=float(config.AI_TIMEOUT)
                )
                print("   ✅ CheapVibeCode API настроен")
            except Exception as e:
                print(f"   ⚠️ CheapVibeCode API недоступен: {type(e).__name__}")
        elif OPENAI_AVAILABLE and getattr(config, 'CHEAPVIBECODE_API_KEY', ''):
            print("   ⚠️ CHEAPVIBECODE_MODEL не установлен")
        
        self.stats = AIProviderStats()
        self.validator = ResponseValidator()
        self.cache = SimpleCache(ttl_seconds=3600)
        
        self._last_request_time = 0
        self._min_request_interval = 1.0
        
        if self.gemini_model or self.openai_client or self.cheapvibecode_client:
            print("✅ [AI] Handler инициализирован (AI режим)")
            print("   • Translation: ✅ Enabled (EN→RU)")
        else:
            print("⚠️ [AI] Handler в dummy режиме (нет доступных провайдеров)")
            print("   • Translation: ❌ Disabled")
    
    async def analyze_article(self, article: Dict) -> Optional[Dict]:
        title = article.get('title', '')
        text = article.get('summary', '') or article.get('content', '') or article.get('description', '')
        
        if not title or not text:
            return None
        
        score = 70
        
        crypto_keywords = ['bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'blockchain', 
                          'биткоин', 'эфириум', 'крипто', 'блокчейн', 'defi', 'nft',
                          'solana', 'cardano', 'polkadot', 'binance', 'coinbase']
        
        text_lower = (title + ' ' + text).lower()
        keyword_matches = sum(1 for kw in crypto_keywords if kw in text_lower)
        score += min(keyword_matches * 5, 20)
        
        positive_words = ['рост', 'прибыль', 'успех', 'новый рекорд', 'breakthrough', 'gain', 
                         'rally', 'surge', 'bullish', 'launch', 'partnership', 'adoption']
        negative_words = ['падение', 'потери', 'скам', 'взлом', 'loss', 'hack', 'crash',
                         'scam', 'fraud', 'bearish', 'drop', 'decline', 'ban']
        
        positive_count = sum(1 for w in positive_words if w in text_lower)
        negative_count = sum(1 for w in negative_words if w in text_lower)
        
        if positive_count > negative_count:
            sentiment = 'positive'
            score += 5
        elif negative_count > positive_count:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        if len(title) > 50:
            score += 3
        
        if len(text) > 200:
            score += 2
        
        return {
            'provider': 'analyzer',
            'score': min(score, 95),
            'sentiment': sentiment,
            'relevance': 'high' if score > 80 else 'medium',
            'topics': []
        }
    
    async def translate_text(self, text: str, source_lang: str = 'en', target_lang: str = 'ru') -> Optional[str]:
        if not text or len(text.strip()) < 5:
            return None
        
        if source_lang == target_lang:
            return text
        
        cached = self.cache.get('translate', source_lang, target_lang, text[:100])
        if cached:
            return cached
        
        await self._rate_limit()
        
        provider = self.stats.get_preferred_provider()

        for candidate in self._get_provider_order(provider, include_dummy=False):
            result = await self._try_translation(
                candidate,
                text,
                source_lang,
                target_lang
            )
            if result:
                translated, elapsed = result
                self.stats.record_success(
                    candidate,
                    elapsed,
                    is_translation=True
                )
                self.cache.set(
                    'translate',
                    source_lang,
                    target_lang,
                    text[:100],
                    translated
                )
                return translated
        
        return None
    
    async def _try_translation(
        self,
        provider: str,
        text: str,
        source_lang: str,
        target_lang: str
    ) -> Optional[Tuple[str, float]]:
        start_time = time.time()
        
        try:
            if provider == 'cheapvibecode' and self.cheapvibecode_client:
                translated = await self._translate_with_openai_compatible(
                    self.cheapvibecode_client,
                    config.CHEAPVIBECODE_MODEL,
                    text,
                    source_lang,
                    target_lang
                )
            elif provider == 'gemini' and self.gemini_model:
                translated = await self._translate_with_gemini(text, source_lang, target_lang)
            elif provider == 'openai' and self.openai_client:
                translated = await self._translate_with_openai_compatible(
                    self.openai_client,
                    config.OPENAI_MODEL,
                    text,
                    source_lang,
                    target_lang
                )
            else:
                return None
            
            elapsed = time.time() - start_time
            
            is_valid, error = self.validator.validate_translation(translated, len(text))
            if not is_valid:
                self.stats.record_failure(provider)
                return None
            
            return translated, elapsed
            
        except Exception as e:
            self.stats.record_failure(provider)
            logger.warning(
                "AI translation provider %s failed: %s (HTTP %s)",
                provider,
                type(e).__name__,
                getattr(e, 'status_code', 'unknown'),
            )
            return None
    
    async def _translate_with_gemini(self, text: str, source_lang: str, target_lang: str) -> str:
        lang_names = {
            'en': 'English',
            'ru': 'Russian',
            'es': 'Spanish',
            'de': 'German',
            'fr': 'French',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh': 'Chinese'
        }
        
        source_name = lang_names.get(source_lang, source_lang)
        target_name = lang_names.get(target_lang, target_lang)
        
        prompt = f"""Translate the following text from {source_name} to {target_name}.
Return ONLY the translation, without any explanations or comments.

Text to translate:
{text}

Translation:"""
        
        for attempt in range(config.AI_MAX_RETRIES):
            try:
                response = await asyncio.wait_for(
                    self.gemini_model.generate_content_async(prompt),
                    timeout=config.AI_TIMEOUT
                )
                
                if not response.text:
                    raise ValueError("Empty response from Gemini")
                
                translated = response.text.strip()
                
                if translated.startswith('Translation:'):
                    translated = translated.replace('Translation:', '').strip()
                
                return translated
                
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
    
    async def _translate_with_openai(self, text: str, source_lang: str, target_lang: str) -> str:
        return await self._translate_with_openai_compatible(
            self.openai_client,
            config.OPENAI_MODEL,
            text,
            source_lang,
            target_lang
        )

    async def _translate_with_openai_compatible(
        self,
        client,
        model: str,
        text: str,
        source_lang: str,
        target_lang: str
    ) -> str:
        lang_names = {
            'en': 'English',
            'ru': 'Russian',
            'es': 'Spanish',
            'de': 'German',
            'fr': 'French',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh': 'Chinese'
        }
        
        source_name = lang_names.get(source_lang, source_lang)
        target_name = lang_names.get(target_lang, target_lang)
        
        system_prompt = f"You are a professional translator. Translate text from {source_name} to {target_name}. Return ONLY the translation, nothing else."
        
        response = await self._create_openai_chat_completion(
            client=client,
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.1,
            max_tokens=config.AI_TRANSLATION_MAX_TOKENS
        )

        translated = response.choices[0].message.content
        if not translated:
            raise ValueError("Empty response from OpenAI-compatible provider")

        return translated.strip()
    
    async def get_summary(
        self,
        title: str,
        text: str,
        category: str,
        force_provider: Optional[str] = None
    ) -> Optional[Tuple[str, str]]:
        if not text or len(text.strip()) < 100:
            return None
        
        cached = self.cache.get('summary', title, text[:100])
        if cached:
            return cached, 'cache'
        
        await self._rate_limit()
        
        if force_provider:
            provider = force_provider
        else:
            provider = self.stats.get_preferred_provider()
        
        category_emoji = category.split()[-1] if category else '📰'
        
        for candidate in self._get_provider_order(provider, include_dummy=True):
            result = await self._try_provider(
                candidate,
                title,
                text,
                category_emoji
            )
            if result:
                summary, elapsed = result
                self.stats.record_success(
                    candidate,
                    elapsed,
                    is_translation=False
                )
                self.cache.set('summary', title, text[:100], summary)
                return summary, candidate
        
        return None

    def _get_provider_order(
        self,
        preferred: str,
        include_dummy: bool
    ) -> list:
        available = []
        if self.cheapvibecode_client:
            available.append('cheapvibecode')
        if self.gemini_model:
            available.append('gemini')
        if self.openai_client:
            available.append('openai')

        ordered = []
        if preferred == 'dummy' and include_dummy:
            ordered.append('dummy')

        for provider in [preferred, *available]:
            if provider in available and provider not in ordered:
                ordered.append(provider)

        if include_dummy and 'dummy' not in ordered:
            ordered.append('dummy')
        return ordered
    
    async def _try_provider(
        self,
        provider: str,
        title: str,
        text: str,
        emoji: str
    ) -> Optional[Tuple[str, float]]:
        start_time = time.time()
        
        try:
            if provider == 'cheapvibecode' and self.cheapvibecode_client:
                summary = await self._call_openai_compatible(
                    self.cheapvibecode_client,
                    config.CHEAPVIBECODE_MODEL,
                    title,
                    text,
                    emoji
                )
            elif provider == 'gemini' and self.gemini_model:
                summary = await self._call_gemini(title, text, emoji)
            elif provider == 'openai' and self.openai_client:
                summary = await self._call_openai_compatible(
                    self.openai_client,
                    config.OPENAI_MODEL,
                    title,
                    text,
                    emoji
                )
            elif provider == 'dummy':
                summary = self._call_dummy(title, text, emoji)
            else:
                return None
            
            elapsed = time.time() - start_time
            
            is_valid, error = self.validator.validate(summary)
            if not is_valid:
                self.stats.record_failure(provider)
                return None
            
            return summary, elapsed
            
        except Exception as e:
            self.stats.record_failure(provider)
            logger.warning(
                "AI summary provider %s failed: %s (HTTP %s)",
                provider,
                type(e).__name__,
                getattr(e, 'status_code', 'unknown'),
            )
            return None
    
    async def _call_gemini(self, title: str, text: str, emoji: str) -> str:
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
        return await self._call_openai_compatible(
            self.openai_client,
            config.OPENAI_MODEL,
            title,
            text,
            emoji
        )

    async def _call_openai_compatible(
        self,
        client,
        model: str,
        title: str,
        text: str,
        emoji: str
    ) -> str:
        prompt = config.ai_prompt_template.format(emoji=emoji, title=title)
        user_prompt = f"Заголовок: {title}\n\nПолный текст статьи:\n{text[:config.MAX_ARTICLE_TEXT_LENGTH]}"

        response = await self._create_openai_chat_completion(
            client=client,
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=config.AI_TEMPERATURE,
            max_tokens=config.AI_MAX_TOKENS
        )

        summary = response.choices[0].message.content
        if not summary:
            raise ValueError("Empty response from OpenAI-compatible provider")

        return self._sanitize_markdown(summary)

    async def _create_openai_chat_completion(
        self,
        client,
        model: str,
        messages: list,
        temperature: float,
        max_tokens: int
    ):
        loop = asyncio.get_running_loop()

        for attempt in range(config.AI_MAX_RETRIES):
            try:
                return await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: client.chat.completions.create(
                            model=model,
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens
                        )
                    ),
                    timeout=config.AI_TIMEOUT
                )
            except asyncio.TimeoutError:
                if attempt >= config.AI_MAX_RETRIES - 1:
                    raise
            except Exception as e:
                if (
                    not self._is_transient_ai_error(e)
                    or attempt >= config.AI_MAX_RETRIES - 1
                ):
                    raise

            await asyncio.sleep(config.AI_BACKOFF_FACTOR * (2 ** attempt))

    @staticmethod
    def _is_transient_ai_error(error: Exception) -> bool:
        status_code = getattr(error, 'status_code', None)
        # 520 используется Cloudflare, когда origin провайдера временно не отвечает.
        if status_code in {408, 409, 425, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524}:
            return True

        if isinstance(error, (ConnectionError, TimeoutError)):
            return True

        error_text = str(error).lower()
        transient_markers = (
            'timeout', 'timed out', 'rate limit',
            'connection', 'temporarily unavailable',
            'service unavailable', 'gateway timeout',
            'web server is returning an unknown error', 'cloudflare 520'
        )
        return any(marker in error_text for marker in transient_markers)
    
    def _call_dummy(self, title: str, text: str, emoji: str) -> str:
        sentences = text.split('.')[:3]
        summary_text = '. '.join(s.strip() for s in sentences if s.strip()) + '.'
        
        if len(summary_text) > 500:
            summary_text = summary_text[:497] + '...'
        
        return f"""{emoji} **{title}**

{summary_text}

#crypto #news"""
    
    def _sanitize_markdown(self, text: str) -> str:
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
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            wait_time = self._min_request_interval - elapsed
            await asyncio.sleep(wait_time)
        
        self._last_request_time = time.time()
    
    def get_stats(self) -> Dict:
        total_requests = sum(
            self.stats.stats[p]['success'] + self.stats.stats[p]['failures']
            for p in ['cheapvibecode', 'gemini', 'openai', 'dummy']
        )
        
        successful_requests = sum(
            self.stats.stats[p]['success']
            for p in ['cheapvibecode', 'gemini', 'openai', 'dummy']
        )
        
        total_translations = sum(
            self.stats.stats[p]['translations']
            for p in ['cheapvibecode', 'gemini', 'openai', 'dummy']
        )
        
        return {
            'provider': self.stats.get_preferred_provider(),
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': total_requests - successful_requests,
            'success_rate': (successful_requests / total_requests * 100) if total_requests > 0 else 0.0,
            'translations': total_translations
        }
    
    def get_stats_summary(self) -> Dict:
        return {
            'cheapvibecode': {
                'available': self.cheapvibecode_client is not None,
                'success_rate': f"{self.stats.get_success_rate('cheapvibecode') * 100:.1f}%",
                'avg_time': f"{self.stats.get_avg_time('cheapvibecode'):.2f}s",
                'total_requests': self.stats.stats['cheapvibecode']['success'] + self.stats.stats['cheapvibecode']['failures'],
                'translations': self.stats.stats['cheapvibecode']['translations']
            },
            'gemini': {
                'available': self.gemini_model is not None,
                'success_rate': f"{self.stats.get_success_rate('gemini') * 100:.1f}%",
                'avg_time': f"{self.stats.get_avg_time('gemini'):.2f}s",
                'total_requests': self.stats.stats['gemini']['success'] + self.stats.stats['gemini']['failures'],
                'translations': self.stats.stats['gemini']['translations']
            },
            'openai': {
                'available': self.openai_client is not None,
                'success_rate': f"{self.stats.get_success_rate('openai') * 100:.1f}%",
                'avg_time': f"{self.stats.get_avg_time('openai'):.2f}s",
                'total_requests': self.stats.stats['openai']['success'] + self.stats.stats['openai']['failures'],
                'translations': self.stats.stats['openai']['translations']
            },
            'dummy': {
                'available': True,
                'success_rate': f"{self.stats.get_success_rate('dummy') * 100:.1f}%",
                'total_requests': self.stats.stats['dummy']['success'] + self.stats.stats['dummy']['failures'],
                'translations': self.stats.stats['dummy']['translations']
            },
            'preferred_provider': self.stats.get_preferred_provider(),
            'cache_size': len(self.cache.cache)
        }
    
    def print_stats(self):
        self.stats.print_summary()
        print(f"  Cache: {len(self.cache.cache)} записей")
        print(f"  Preferred: {self.stats.get_preferred_provider().upper()}")


__all__ = ['AIHandler']