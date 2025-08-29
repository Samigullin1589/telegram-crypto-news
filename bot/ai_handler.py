# bot/ai_handler.py
import asyncio
import google.generativeai as genai
from openai import OpenAI
from . import config

class AIHandler:
    def __init__(self):
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.gemini_model = genai.GenerativeModel('gemini-1.5-pro-latest')
        self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.prompt_template = """
        Ты — ведущий аналитик издания 'Bloomberg Crypto'. Твоя задача — проанализировать текст новости и подготовить профессиональный, структурированный пост для Telegram-канала 'Crypto Compass'.
        Твой ответ должен быть исключительно на русском языке и строго следовать формату Markdown ниже. Не добавляй никаких комментариев или вводных фраз. Твой ответ должен начинаться сразу с заголовка.

        {emoji} **{title}**

        *Здесь напиши главную суть новости в 2-3 предложениях. Используй профессиональный, но понятный язык. Объясни, почему это важно.*

        **Детали:**
        - Ключевой факт или цифра из статьи.
        - Контекст или причина произошедшего.
        - Возможные последствия для рынка или индустрии.

        *(Сгенерируй 3 релевантных хэштега на русском, например: #майнинг #россия #закон)*
        """

    async def get_summary(self, title, text, category):
        max_retries, backoff_factor = 3, 10
        category_emoji = category.split()[-1]
        if not text:
            print("⚠️ [AI] Текст для анализа пуст. Пропускаю саммари.")
            return None
        prompt = self.prompt_template.format(emoji=category_emoji, title=title)
        for attempt in range(max_retries):
            try:
                print(f"🤖 [AI] Попытка {attempt + 1}/{max_retries}. Отправляю в Gemini: {title}")
                response = await self.gemini_model.generate_content_async(f"{prompt}\n\nТЕКСТ СТАТЬИ ДЛЯ АНАЛИЗА:\n{text}")
                return self._sanitize_markdown(response.text)
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    print("🚨 [AI] Квота Gemini исчерпана. Немедленное переключение на GPT.")
                    break
                print(f"⚠️ [WARN] Ошибка Gemini: {e}. Попытка {attempt + 1} не удалась.")
                if attempt + 1 < max_retries:
                    delay = backoff_factor * (2 ** attempt)
                    print(f"⏳ [AI] Пауза на {delay} секунд перед следующей попыткой.")
                    await asyncio.sleep(delay)
        print("🤖 [AI] Переключаюсь на GPT (резерв).")
        try:
            user_prompt = f"Заголовок: {title}\n\nПолный текст статьи:\n{text}"
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: self.openai_client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user_prompt}]))
            summary = response.choices[0].message.content
            return self._sanitize_markdown(summary)
        except Exception as e_gpt:
            print(f"❌ [ERROR] Ошибка GPT: {e_gpt}. Оба AI провайдера недоступны.")
            return None

    def _sanitize_markdown(self, text):
        for char in ['*', '_', '`']:
            if text.count(char * 3) % 2 != 0: text = text.rsplit(char * 3, 1)[0]
            if text.count(char * 2) % 2 != 0: text = text.rsplit(char * 2, 1)[0]
            if text.count(char) % 2 != 0: text = text.rsplit(char, 1)[0]
        return text