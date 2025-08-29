# bot/telegram_poster.py
import telegram
import re
from . import config

class TelegramPoster:
    def __init__(self):
        self.bot = telegram.Bot(token=config.TELEGRAM_BOT_TOKEN)
        self.channel_id = config.TELEGRAM_CHANNEL_ID

    async def post(self, message, link, image_url):
        full_message = f"{message}\n\n🔗 [Читать первоисточник]({link})"
        try:
            if image_url:
                await self.bot.send_photo(chat_id=self.channel_id, photo=image_url, caption=full_message[:1024], parse_mode='Markdown')
            else:
                await self.bot.send_message(chat_id=self.channel_id, text=full_message, parse_mode='Markdown', disable_web_page_preview=True)
            print(f"✅ [POST] Новость '{link}' успешно опубликована.")
            return True
        except telegram.error.BadRequest as e:
            print(f"❌ [ERROR] Ошибка форматирования Markdown: {e}. Пробую отправить без него.")
            plain_text_message = re.sub(r'[*_`\[\]()~>#+\-=|{}.!]', '', full_message)
            try:
                if image_url:
                    await self.bot.send_photo(chat_id=self.channel_id, photo=image_url, caption=plain_text_message[:1024])
                else:
                    await self.bot.send_message(chat_id=self.channel_id, text=plain_text_message, disable_web_page_preview=True)
                print("✅ [POST] Сообщение успешно отправлено в текстовом виде.")
                return True
            except Exception as e_plain:
                print(f"❌ [FATAL] Повторная отправка также не удалась: {e_plain}")
                return False
        except Exception as e:
            print(f"❌ [ERROR] Неизвестная ошибка при отправке в Telegram: {e}")
            return False