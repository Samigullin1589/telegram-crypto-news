# bot/telegram_poster.py
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import re
from . import config

class TelegramPoster:
    def __init__(self):
        self.bot = telegram.Bot(token=config.TELEGRAM_BOT_TOKEN)
        self.channel_id = config.TELEGRAM_CHANNEL_ID

    async def post(self, message, link, image_url):
        # --- ГЛАВНОЕ ИЗМЕНЕНИЕ: Создаём кнопку ---
        # Ссылка больше не является частью текста сообщения.
        keyboard = [
            [InlineKeyboardButton("🔗 Читать первоисточник", url=link)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            # Первая попытка отправить с полным форматированием от AI
            if image_url:
                await self.bot.send_photo(
                    chat_id=self.channel_id,
                    photo=image_url,
                    caption=message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            else:
                await self.bot.send_message(
                    chat_id=self.channel_id,
                    text=message,
                    parse_mode='Markdown',
                    disable_web_page_preview=True,
                    reply_markup=reply_markup
                )
            print(f"✅ [POST] Новость '{link}' успешно опубликована.")
            return True
            
        except telegram.error.BadRequest as e:
            print(f"❌ [ERROR] Ошибка форматирования Markdown от AI: {e}. Пробую отправить без форматирования.")
            
            # Вторая (безопасная) попытка: отправляем без parse_mode='Markdown'
            # Кнопка `reply_markup` будет работать в любом случае.
            try:
                if image_url:
                    await self.bot.send_photo(
                        chat_id=self.channel_id,
                        photo=image_url,
                        caption=message,
                        reply_markup=reply_markup
                    )
                else:
                    await self.bot.send_message(
                        chat_id=self.channel_id,
                        text=message,
                        disable_web_page_preview=True,
                        reply_markup=reply_markup
                    )
                print("✅ [POST] Сообщение успешно отправлено в безопасном режиме (без Markdown).")
                return True
            except Exception as e_plain:
                print(f"❌ [FATAL] Повторная отправка также не удалась: {e_plain}")
                return False
                
        except Exception as e:
            print(f"❌ [ERROR] Неизвестная ошибка при отправке в Telegram: {e}")
            return False