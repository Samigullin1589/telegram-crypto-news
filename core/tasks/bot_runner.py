# core/tasks/bot_runner.py
"""
Bot Webhook Runner - ИСПРАВЛЕНО: добавлена регистрация handlers
"""

import asyncio
import logging
import traceback
import os

logger = logging.getLogger(__name__)


class BotWebhookRunner:
    """Запуск Telegram bot в режиме WEBHOOK"""
    
    def __init__(self, bot_application, health_monitor, statistics, shutdown_event):
        self.bot_application = bot_application
        self.health_monitor = health_monitor
        self.statistics = statistics
        self.shutdown_event = shutdown_event
    
    async def run(self):
        """Основной цикл бота"""
        try:
            logger.info("🤖 [BOT] Инициализация command handler (WEBHOOK MODE)...")
            
            await asyncio.wait_for(self.bot_application.initialize(), timeout=30.0)
            await asyncio.wait_for(self.bot_application.start(), timeout=30.0)
            
            # ⭐ КРИТИЧЕСКИ ВАЖНО: Регистрация handlers!
            self._register_handlers()
            
            webhook_url = self._determine_webhook_url()
            
            logger.info(f"🤖 [BOT] Устанавливаем webhook: {webhook_url}")
            
            await asyncio.wait_for(
                self.bot_application.bot.delete_webhook(drop_pending_updates=True),
                timeout=10.0
            )
            
            webhook_info = await asyncio.wait_for(
                self.bot_application.bot.set_webhook(
                    url=webhook_url,
                    allowed_updates=None,
                    drop_pending_updates=True
                ),
                timeout=10.0
            )
            
            if webhook_info:
                logger.info("✅ [BOT] Webhook установлен успешно")
            else:
                logger.warning("⚠️  [BOT] Webhook set вернул False, но продолжаем")
            
            self.health_monitor.update_bot_heartbeat()
            
            # Подтверждение что handlers зарегистрированы
            handlers_count = self._count_handlers()
            
            logger.info("✅ [BOT] Command handler активен в WEBHOOK режиме")
            logger.info(f"   Webhook URL: {webhook_url}")
            logger.info(f"   Зарегистрировано handlers: {handlers_count}")
            logger.info("   Доступные команды: /start, /help, /status, /positions, /performance")
            
            while not self.shutdown_event.is_set():
                self.health_monitor.update_bot_heartbeat()
                await asyncio.sleep(60)
            
            logger.info("🤖 [BOT] Получен сигнал остановки")
        
        except asyncio.TimeoutError:
            logger.error("❌ [BOT] Timeout при инициализации")
        
        except asyncio.CancelledError:
            logger.info("🤖 [BOT] Получен сигнал отмены")
        
        except Exception as e:
            self.health_monitor.record_error('bot')
            self.statistics.increment_errors()
            logger.error(f"❌ [BOT] Ошибка при установке webhook: {e}")
            traceback.print_exc()
        
        finally:
            await self._cleanup()
    
    def _register_handlers(self):
        """⭐ КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Регистрация handlers"""
        try:
            from app.bot import register_all_handlers, handlers_registered
            
            if handlers_registered():
                logger.info("✅ [BOT] Handlers уже зарегистрированы")
                return
            
            logger.info("🔧 [BOT] Регистрация command handlers...")
            
            register_all_handlers()
            
            if handlers_registered():
                logger.info("✅ [BOT] Handlers успешно зарегистрированы")
            else:
                logger.warning("⚠️  [BOT] Статус регистрации handlers неизвестен")
        
        except ImportError as e:
            logger.error(f"❌ [BOT] Не удалось импортировать register_all_handlers: {e}")
            traceback.print_exc()
        
        except Exception as e:
            logger.error(f"❌ [BOT] Ошибка регистрации handlers: {e}")
            traceback.print_exc()
    
    def _count_handlers(self) -> int:
        """Подсчет зарегистрированных handlers"""
        try:
            total = 0
            for group in self.bot_application.handlers.values():
                total += len(group)
            return total
        except Exception:
            return 0
    
    def _determine_webhook_url(self) -> str:
        """Определяет URL для webhook"""
        webhook_url = os.environ.get('WEBHOOK_URL', '')
        
        if not webhook_url:
            render_url = os.environ.get('RENDER_EXTERNAL_URL', '')
            if render_url:
                webhook_url = f"{render_url}/webhook/telegram"
            else:
                service_name = os.environ.get('RENDER_SERVICE_NAME', 'crypto-compass')
                webhook_url = f"https://{service_name}.onrender.com/webhook/telegram"
        
        return webhook_url
    
    async def _cleanup(self):
        """Cleanup bot resources"""
        logger.info("🤖 [BOT] Останавливаем command handler...")
        
        try:
            await asyncio.wait_for(
                self.bot_application.bot.delete_webhook(),
                timeout=10.0
            )
            logger.info("   ✓ Webhook удалён")
            
            if self.bot_application.running:
                await asyncio.wait_for(
                    self.bot_application.stop(),
                    timeout=10.0
                )
                logger.info("   ✓ Application остановлен")
            
            await asyncio.wait_for(
                self.bot_application.shutdown(),
                timeout=10.0
            )
            logger.info("   ✓ Shutdown завершён")
        
        except asyncio.TimeoutError:
            logger.warning("   ⚠️  Timeout при shutdown")
        except Exception as e:
            logger.warning(f"   ⚠️  Ошибка при shutdown: {e}")
        
        logger.info("✅ [BOT] Command handler полностью остановлен")


__all__ = ['BotWebhookRunner']