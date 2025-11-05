"""
INTEGRATED CRYPTO MONITOR v4.4 - Production Ready Edition
Unified system: News Bot + Whale Monitor + Trading System + Telegram Commands

PRODUCTION FEATURES:
✅ News Bot - AI-powered crypto news aggregation
✅ Whale Monitor - Smart money tracking & discovery
✅ Trading System - Technical + Fundamental + ML signals
✅ Telegram Bot - Interactive command handler (WEBHOOK MODE)
✅ Unified Health Monitoring
✅ Graceful Shutdown
✅ Performance Analytics
✅ Multi-Chain Support with Adaptive Rate Limiting
✅ Automatic Chain Recovery from 429 Errors
✅ Advanced Analytics
✅ Position Management
✅ Risk Management
✅ User Commands
✅ HTTP Health Check Server (Render.com optimized)
✅ Production-grade error handling
✅ Memory optimization
✅ Rate limiting v2.1
"""

import asyncio
import signal
import sys
import os
import gc
import psutil
import json
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
import traceback as tb
from collections import defaultdict
from functools import wraps
import random

if sys.version_info < (3, 8):
    print("❌ Требуется Python 3.8 или выше")
    sys.exit(1)

from aiohttp import web
import aiohttp

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ChainRateLimiter:
    """
    Production-grade adaptive rate limiter для блокчейн RPC endpoints
    
    v2.1 Features:
    - Индивидуальные задержки для каждой цепи
    - Специальная обработка Solana (Helius API limits)
    - Экспоненциальный backoff с jitter
    - Кеширование результатов для снижения нагрузки
    - Thread-safe операции
    """
    
    def __init__(self):
        self.chain_stats = {}
        self.disabled_chains = {}
        self.last_request_time = {}
        self._locks = {}
        
        self.chain_delays = {
            'solana': 5.0,
            'ethereum': 2.0,
            'bsc': 2.0,
            'polygon': 2.0,
            'arbitrum': 2.0,
            'base': 2.0,
            'tron': 3.0,
        }
        
        self.max_consecutive_429 = 2
        self.backoff_periods = [120, 300, 600, 1200, 1800]
        self.current_backoff_index = {}
        
        logger.info("🔒 [RATE_LIMITER] Chain Rate Limiter v2.1 инициализирован")
        logger.info(f"   Специальная конфигурация для Solana: {self.chain_delays['solana']}s между запросами")
    
    def init_chain(self, chain: str):
        """Инициализация статистики для цепи"""
        if chain not in self.chain_stats:
            self.chain_stats[chain] = {
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'consecutive_429': 0,
                'total_429_errors': 0,
                'last_429_time': None,
                'recovery_attempts': 0
            }
            self.last_request_time[chain] = datetime.now(timezone.utc) - timedelta(seconds=10)
            self.current_backoff_index[chain] = 0
            self._locks[chain] = asyncio.Lock()
    
    def is_chain_enabled(self, chain: str) -> bool:
        """Проверка доступности цепи"""
        self.init_chain(chain)
        
        if chain not in self.disabled_chains:
            return True
        
        disabled_until = self.disabled_chains[chain]
        now = datetime.now(timezone.utc)
        
        if now >= disabled_until:
            logger.info(f"🔄 [RATE_LIMITER] {chain} - Попытка восстановления")
            del self.disabled_chains[chain]
            self.chain_stats[chain]['recovery_attempts'] += 1
            self.chain_stats[chain]['consecutive_429'] = 0
            return True
        
        return False
    
    async def wait_if_needed(self, chain: str):
        """Ожидание перед запросом если необходимо"""
        self.init_chain(chain)
        
        async with self._locks[chain]:
            min_delay = self.chain_delays.get(chain, 2.0)
            
            last_request = self.last_request_time.get(chain)
            if last_request:
                elapsed = (datetime.now(timezone.utc) - last_request).total_seconds()
                delay_needed = min_delay - elapsed
                
                if delay_needed > 0:
                    await asyncio.sleep(delay_needed)
            
            self.last_request_time[chain] = datetime.now(timezone.utc)
            self.chain_stats[chain]['total_requests'] += 1
    
    def record_success(self, chain: str):
        """Регистрация успешного запроса"""
        if chain not in self.chain_stats:
            self.init_chain(chain)
        
        self.chain_stats[chain]['successful_requests'] += 1
        self.chain_stats[chain]['consecutive_429'] = 0
        
        if self.current_backoff_index[chain] > 0:
            self.current_backoff_index[chain] = max(0, self.current_backoff_index[chain] - 1)
    
    def record_429_error(self, chain: str):
        """Регистрация 429 ошибки с экспоненциальным backoff"""
        if chain not in self.chain_stats:
            self.init_chain(chain)
        
        stats = self.chain_stats[chain]
        stats['failed_requests'] += 1
        stats['consecutive_429'] += 1
        stats['total_429_errors'] += 1
        stats['last_429_time'] = datetime.now(timezone.utc)
        
        if stats['consecutive_429'] >= self.max_consecutive_429:
            backoff_idx = min(
                self.current_backoff_index[chain],
                len(self.backoff_periods) - 1
            )
            backoff_duration = self.backoff_periods[backoff_idx]
            
            jitter = random.uniform(0.8, 1.2)
            backoff_duration = int(backoff_duration * jitter)
            
            disabled_until = datetime.now(timezone.utc) + timedelta(seconds=backoff_duration)
            self.disabled_chains[chain] = disabled_until
            
            self.current_backoff_index[chain] = min(
                self.current_backoff_index[chain] + 1,
                len(self.backoff_periods) - 1
            )
            
            logger.warning(
                f"⏸️ [RATE_LIMITER] {chain} - Временно отключен на {backoff_duration}с "
                f"(backoff level {backoff_idx + 1})"
            )
            logger.warning(
                f"   Причина: {stats['consecutive_429']} последовательных 429 ошибок"
            )
            logger.info(
                f"   Будет восстановлен: {disabled_until.strftime('%H:%M:%S UTC')}"
            )
    
    def record_other_error(self, chain: str):
        """Регистрация других ошибок"""
        if chain not in self.chain_stats:
            self.init_chain(chain)
        
        self.chain_stats[chain]['failed_requests'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику rate limiter"""
        return {
            'chains': self.chain_stats,
            'disabled_chains': {
                chain: until.isoformat()
                for chain, until in self.disabled_chains.items()
            }
        }
    
    def print_stats(self):
        """Вывести статистику"""
        logger.info("\n📊 [RATE_LIMITER] Статистика:")
        
        for chain, stats in self.chain_stats.items():
            status = "✅ Active"
            if chain in self.disabled_chains:
                until = self.disabled_chains[chain]
                remaining = (until - datetime.now(timezone.utc)).total_seconds()
                status = f"⏸️ Disabled ({int(remaining)}s remaining)"
            
            success_rate = 0
            if stats['total_requests'] > 0:
                success_rate = (stats['successful_requests'] / stats['total_requests']) * 100
            
            logger.info(f"\n{chain}:")
            logger.info(f"  Status: {status}")
            logger.info(
                f"  Requests: {stats['total_requests']} "
                f"(Success: {stats['successful_requests']}, Failed: {stats['failed_requests']})"
            )
            logger.info(f"  Success Rate: {success_rate:.1f}%")
            logger.info(
                f"  429 Errors: {stats['total_429_errors']} "
                f"(Current streak: {stats['consecutive_429']})"
            )
            logger.info(f"  Recovery Attempts: {stats['recovery_attempts']}")


class ResourceMonitor:
    """Production-grade мониторинг системных ресурсов"""
    
    def __init__(self, max_memory_mb: int = 450):
        self.max_memory_mb = max_memory_mb
        self.process = psutil.Process()
        self.last_gc = datetime.now(timezone.utc)
        self.gc_interval = 300
        self.memory_warnings = 0
        self.gc_runs = 0
    
    def check_memory(self) -> bool:
        """
        Проверка использования памяти
        
        Returns:
            bool: True если память в норме, False если превышен лимит
        """
        try:
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            if memory_mb > self.max_memory_mb:
                self.memory_warnings += 1
                logger.warning(
                    f"⚠️ [MEMORY] Использовано {memory_mb:.1f}MB из {self.max_memory_mb}MB"
                )
                logger.info("   Запускаем garbage collection...")
                
                gc.collect()
                self.gc_runs += 1
                
                memory_info_after = self.process.memory_info()
                memory_mb_after = memory_info_after.rss / 1024 / 1024
                freed = memory_mb - memory_mb_after
                
                logger.info(
                    f"   Освобождено {freed:.1f}MB (осталось {memory_mb_after:.1f}MB)"
                )
                
                if memory_mb_after > self.max_memory_mb:
                    return False
            
            return True
        
        except Exception as e:
            logger.error(f"❌ [MEMORY] Ошибка проверки памяти: {e}")
            return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику ресурсов"""
        try:
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            memory_percent = self.process.memory_percent()
            cpu_percent = self.process.cpu_percent(interval=0.1)
            
            return {
                'memory_mb': round(memory_mb, 2),
                'memory_percent': round(memory_percent, 2),
                'cpu_percent': round(cpu_percent, 2),
                'num_threads': self.process.num_threads(),
                'max_memory_mb': self.max_memory_mb,
                'memory_warnings': self.memory_warnings,
                'gc_runs': self.gc_runs
            }
        
        except Exception as e:
            logger.error(f"❌ [RESOURCE] Ошибка получения статистики: {e}")
            return {}


class SystemHealthMonitor:
    """Production-grade мониторинг здоровья всех подсистем"""
    
    def __init__(self):
        self.start_time = datetime.now(timezone.utc)
        self.check_interval = 300
        
        self.news_alive = False
        self.whale_alive = False
        self.trading_alive = False
        self.bot_alive = False
        
        self.news_cycles = 0
        self.whale_cycles = 0
        self.trading_cycles = 0
        self.bot_commands_processed = 0
        
        self.news_errors = 0
        self.whale_errors = 0
        self.trading_errors = 0
        self.bot_errors = 0
        
        self.last_news_heartbeat = None
        self.last_whale_heartbeat = None
        self.last_trading_heartbeat = None
        self.last_bot_heartbeat = None
        
        self.news_silence_threshold = 3600
        self.whale_silence_threshold = 600
        self.trading_silence_threshold = 3600
        self.bot_silence_threshold = 86400
        
        logger.info("💚 [HEALTH] Health Monitor инициализирован")
    
    def update_news_heartbeat(self):
        """Обновление heartbeat новостной системы"""
        self.news_alive = True
        self.last_news_heartbeat = datetime.now(timezone.utc)
        self.news_cycles += 1
    
    def update_whale_heartbeat(self):
        """Обновление heartbeat whale системы"""
        self.whale_alive = True
        self.last_whale_heartbeat = datetime.now(timezone.utc)
        self.whale_cycles += 1
    
    def update_trading_heartbeat(self):
        """Обновление heartbeat trading системы"""
        self.trading_alive = True
        self.last_trading_heartbeat = datetime.now(timezone.utc)
        self.trading_cycles += 1
    
    def update_bot_heartbeat(self):
        """Обновление heartbeat telegram bot"""
        self.bot_alive = True
        self.last_bot_heartbeat = datetime.now(timezone.utc)
    
    def record_bot_command(self):
        """Регистрация обработанной команды"""
        self.bot_commands_processed += 1
        self.update_bot_heartbeat()
    
    def record_error(self, system: str):
        """Регистрация ошибки в системе"""
        if system == "news":
            self.news_errors += 1
        elif system == "whale":
            self.whale_errors += 1
        elif system == "trading":
            self.trading_errors += 1
        elif system == "bot":
            self.bot_errors += 1
    
    def check_health(self) -> Tuple[bool, List[str]]:
        """Проверка здоровья всех систем"""
        issues = []
        now = datetime.now(timezone.utc)
        
        if self.last_news_heartbeat:
            silence = (now - self.last_news_heartbeat).seconds
            if silence > self.news_silence_threshold:
                issues.append(
                    f"📰 News Bot: Silent for {silence//60} minutes "
                    f"(threshold: {self.news_silence_threshold//60}m)"
                )
        elif self.news_cycles > 0:
            issues.append("📰 News Bot: No recent heartbeat")
        
        if self.last_whale_heartbeat:
            silence = (now - self.last_whale_heartbeat).seconds
            if silence > self.whale_silence_threshold:
                issues.append(
                    f"🐋 Whale Monitor: Silent for {silence//60} minutes "
                    f"(threshold: {self.whale_silence_threshold//60}m)"
                )
        elif self.whale_cycles > 0:
            issues.append("🐋 Whale Monitor: No recent heartbeat")
        
        if self.last_trading_heartbeat:
            silence = (now - self.last_trading_heartbeat).seconds
            if silence > self.trading_silence_threshold:
                issues.append(
                    f"📈 Trading System: Silent for {silence//60} minutes "
                    f"(threshold: {self.trading_silence_threshold//60}m)"
                )
        elif self.trading_cycles > 0:
            issues.append("📈 Trading System: No recent heartbeat")
        
        if self.last_bot_heartbeat:
            silence = (now - self.last_bot_heartbeat).seconds
            if silence > self.bot_silence_threshold:
                issues.append(
                    f"🤖 Bot Handler: Silent for {silence//3600:.1f} hours "
                    f"(threshold: {self.bot_silence_threshold//3600}h)"
                )
        
        total_cycles = self.news_cycles + self.whale_cycles + self.trading_cycles
        total_errors = self.news_errors + self.whale_errors + self.trading_errors + self.bot_errors
        
        if total_cycles > 0:
            error_rate = (total_errors / total_cycles) * 100
            if error_rate > 10:
                issues.append(f"⚠️ High error rate: {error_rate:.1f}%")
        
        return len(issues) == 0, issues
    
    def get_uptime(self) -> timedelta:
        """Получение времени работы системы"""
        return datetime.now(timezone.utc) - self.start_time
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики здоровья"""
        uptime = self.get_uptime()
        
        return {
            "uptime_seconds": uptime.total_seconds(),
            "uptime_formatted": self._format_duration(uptime.total_seconds()),
            "systems": {
                "news": {
                    "alive": self.news_alive,
                    "cycles": self.news_cycles,
                    "errors": self.news_errors,
                    "last_heartbeat": self.last_news_heartbeat.isoformat() if self.last_news_heartbeat else None
                },
                "whale": {
                    "alive": self.whale_alive,
                    "cycles": self.whale_cycles,
                    "errors": self.whale_errors,
                    "last_heartbeat": self.last_whale_heartbeat.isoformat() if self.last_whale_heartbeat else None
                },
                "trading": {
                    "alive": self.trading_alive,
                    "cycles": self.trading_cycles,
                    "errors": self.trading_errors,
                    "last_heartbeat": self.last_trading_heartbeat.isoformat() if self.last_trading_heartbeat else None
                },
                "bot": {
                    "alive": self.bot_alive,
                    "commands_processed": self.bot_commands_processed,
                    "errors": self.bot_errors,
                    "last_heartbeat": self.last_bot_heartbeat.isoformat() if self.last_bot_heartbeat else None
                }
            },
            "total_cycles": self.news_cycles + self.whale_cycles + self.trading_cycles,
            "total_errors": self.news_errors + self.whale_errors + self.trading_errors + self.bot_errors,
            "total_bot_commands": self.bot_commands_processed
        }
    
    def _format_duration(self, seconds: float) -> str:
        """Форматирование длительности"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds/60)}m"
        elif seconds < 86400:
            return f"{seconds/3600:.1f}h"
        else:
            days = int(seconds / 86400)
            hours = (seconds % 86400) / 3600
            return f"{days}d {hours:.1f}h"


class IntegratedCryptoMonitor:
    """
    Production-ready интегрированная система мониторинга криптовалют
    
    Компоненты:
    1. News Bot - Умная агрегация криптовалютных новостей с AI обработкой
    2. Whale Monitor - Отслеживание крупных перемещений и smart money
    3. Trading System - Генерация торговых сигналов с ML предсказаниями
    4. Telegram Bot - Интерактивный обработчик команд пользователя (WEBHOOK)
    5. HTTP Health Server - Endpoint для мониторинга и webhook (Render.com)
    6. Chain Rate Limiter v2.1 - Адаптивное управление запросами к RPC
    
    Все системы публикуют в один канал с умной приоритизацией
    и координацией для избежания перегрузки канала
    """
    
    def __init__(self):
        logger.info("\n" + "="*80)
        logger.info("🚀 INITIALIZING INTEGRATED CRYPTO MONITOR v4.4")
        logger.info("="*80 + "\n")
        
        self.news_processor = self._load_news_processor()
        self.whale_scheduler = self._load_whale_scheduler()
        self.bot_application = self._load_bot_application()
        
        self.health_monitor = SystemHealthMonitor()
        self.resource_monitor = ResourceMonitor(
            max_memory_mb=int(os.getenv('MAX_MEMORY_MB', '450'))
        )
        self.rate_limiter = ChainRateLimiter()
        
        if self.whale_scheduler and hasattr(self.whale_scheduler, 'set_rate_limiter'):
            self.whale_scheduler.set_rate_limiter(self.rate_limiter)
            logger.info("✅ Rate Limiter v2.1 подключен к Whale Scheduler")
        
        self.shutdown_event = asyncio.Event()
        self._tasks: List[asyncio.Task] = []
        self._shutdown_in_progress = False
        
        self._http_app = None
        self._http_runner = None
        self._http_site = None
        
        self.stats = {
            "start_time": datetime.now(timezone.utc),
            "total_publications": 0,
            "news_publications": 0,
            "whale_publications": 0,
            "trading_publications": 0,
            "bot_commands": 0,
            "errors_caught": 0,
            "restarts": 0
        }
        
        logger.info("\n✅ Integrated Crypto Monitor v4.4 инициализирован")
    
    def _load_news_processor(self) -> Optional[Any]:
        """Загрузка News Processor с расширенной обработкой ошибок"""
        try:
            from bot.processor import NewsProcessor
            processor = NewsProcessor()
            logger.info("✅ News Processor loaded")
            return processor
        except ImportError as e:
            logger.warning(f"⚠️ News Processor not available: {e}")
            return None
        except Exception as e:
            logger.error(f"⚠️ Failed to load News Processor: {e}")
            tb.print_exc()
            return None
    
    def _load_whale_scheduler(self) -> Optional[Any]:
        """Загрузка Whale Scheduler с расширенной обработкой ошибок"""
        try:
            from app.scheduler import scheduler as whale_scheduler
            logger.info("✅ Whale Scheduler loaded")
            return whale_scheduler
        except ImportError as e:
            logger.warning(f"⚠️ Whale Scheduler not available: {e}")
            return None
        except Exception as e:
            logger.error(f"⚠️ Failed to load Whale Scheduler: {e}")
            tb.print_exc()
            return None
    
    def _load_bot_application(self) -> Optional[Any]:
        """Загрузка Bot Application с расширенной обработкой ошибок"""
        try:
            from app.bot import application as bot_application
            logger.info("✅ Bot Commands Handler loaded")
            
            if self._patch_bot_handlers(bot_application):
                logger.info("   ✓ Bot handlers патчинг успешен")
            else:
                logger.warning("   ⚠️ Bot handlers патчинг не требуется или недоступен")
            
            return bot_application
        except ImportError as e:
            logger.warning(f"⚠️ Bot Commands Handler not available: {e}")
            return None
        except Exception as e:
            logger.error(f"⚠️ Bot Commands Handler not loaded: {e}")
            tb.print_exc()
            return None
    
    def _patch_bot_handlers(self, bot_app: Any) -> bool:
        """
        Патчим обработчики команд для мониторинга
        
        Production-grade версия с правильной обработкой handlers
        """
        if not bot_app:
            return False
        
        try:
            if not hasattr(bot_app, 'handlers'):
                logger.warning("   ⚠️ Bot application не имеет handlers")
                return False
            
            handlers_dict = bot_app.handlers
            
            if not handlers_dict or 0 not in handlers_dict:
                logger.warning("   ⚠️ Handlers пусты или группа 0 не существует")
                return False
            
            handlers_list = handlers_dict[0]
            
            if not handlers_list:
                logger.warning("   ⚠️ Список handlers пуст")
                return False
            
            patched_count = 0
            
            for handler in handlers_list:
                if not hasattr(handler, 'callback'):
                    continue
                
                original_callback = handler.callback
                health_monitor = self.health_monitor
                stats = self.stats
                
                @wraps(original_callback)
                async def wrapped_callback(update, context, original=original_callback, monitor=health_monitor, stats_dict=stats):
                    monitor.record_bot_command()
                    stats_dict["bot_commands"] += 1
                    
                    try:
                        return await original(update, context)
                    except Exception as e:
                        monitor.record_error("bot")
                        logger.error(f"❌ [BOT] Error in command handler: {e}")
                        raise
                
                handler.callback = wrapped_callback
                patched_count += 1
            
            if patched_count > 0:
                logger.info(f"   ✓ Патчинг {patched_count} handlers успешен")
                return True
            else:
                logger.warning("   ⚠️ Нет handlers для патчинга")
                return False
            
        except Exception as e:
            logger.error(f"   ⚠️ Ошибка при патчинге handlers: {e}")
            tb.print_exc()
            return False
    
    async def _health_handler(self, request: web.Request) -> web.Response:
        """HTTP handler для health check"""
        try:
            health_status = {
                'status': 'healthy',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'service': 'crypto-compass-v4.4',
                'version': '4.4'
            }
            
            if self.resource_monitor:
                resource_stats = self.resource_monitor.get_stats()
                health_status['resources'] = resource_stats
            
            if self.rate_limiter:
                rate_stats = self.rate_limiter.get_stats()
                health_status['rate_limiter'] = {
                    'active_chains': len([c for c in rate_stats['chains'] if c not in rate_stats['disabled_chains']]),
                    'disabled_chains': list(rate_stats['disabled_chains'].keys())
                }
            
            health_stats = self.health_monitor.get_stats()
            health_status['uptime'] = health_stats['uptime_formatted']
            health_status['systems'] = health_stats['systems']
            health_status['total_cycles'] = health_stats['total_cycles']
            health_status['total_errors'] = health_stats['total_errors']
            
            return web.json_response(health_status)
        
        except Exception as e:
            logger.error(f"❌ [HEALTH] Error in health handler: {e}")
            tb.print_exc()
            return web.json_response({
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, status=500)
    
    async def _webhook_handler(self, request: web.Request) -> web.Response:
        """HTTP handler для Telegram webhook"""
        try:
            if not self.bot_application:
                logger.error("❌ [WEBHOOK] Bot not initialized")
                return web.json_response({'error': 'Bot not initialized'}, status=503)
            
            update_data = await request.json()
            
            from telegram import Update
            update = Update.de_json(update_data, self.bot_application.bot)
            
            await self.bot_application.process_update(update)
            
            return web.json_response({'ok': True})
        
        except json.JSONDecodeError as e:
            logger.error(f"❌ [WEBHOOK] Invalid JSON: {e}")
            return web.json_response({'error': 'Invalid JSON'}, status=400)
        
        except Exception as e:
            logger.error(f"❌ [WEBHOOK] Ошибка обработки: {e}")
            tb.print_exc()
            return web.json_response({'error': str(e)}, status=500)
    
    async def _start_http_server(self):
        """
        Запуск HTTP сервера для health checks и webhooks
        
        Production-ready v4.4:
        - Правильная последовательность: AppRunner -> setup -> TCPSite -> start
        - Корректное управление жизненным циклом объектов
        - Расширенная обработка ошибок
        """
        try:
            logger.info("🌐 [HTTP] Инициализация health server...")
            
            self._http_app = web.Application()
            
            self._http_app.router.add_get('/', self._health_handler)
            self._http_app.router.add_get('/health', self._health_handler)
            self._http_app.router.add_post('/webhook/telegram', self._webhook_handler)
            
            self._http_runner = web.AppRunner(self._http_app)
            
            await self._http_runner.setup()
            
            port = int(os.environ.get('PORT', 8000))
            self._http_site = web.TCPSite(
                self._http_runner,
                '0.0.0.0',
                port
            )
            
            await self._http_site.start()
            
            logger.info(f"🌐 [HTTP] Health server запущен на порту {port}")
            logger.info("   Endpoints:")
            logger.info("   • GET  / или /health - Health check")
            logger.info("   • POST /webhook/telegram - Telegram webhook")
            
        except OSError as e:
            logger.error(f"❌ [HTTP] Ошибка привязки к порту: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ [HTTP] Ошибка запуска сервера: {e}")
            tb.print_exc()
            raise
    
    async def _stop_http_server(self):
        """
        Остановка HTTP сервера
        
        Production-ready v4.4:
        - Правильная последовательность остановки
        - Обработка всех возможных состояний
        """
        try:
            logger.info("🌐 [HTTP] Останавливаем health server...")
            
            if self._http_site:
                await self._http_site.stop()
                logger.info("   ✓ Site остановлен")
            
            if self._http_runner:
                await self._http_runner.cleanup()
                logger.info("   ✓ Runner очищен")
            
            if self._http_app:
                await self._http_app.shutdown()
                await self._http_app.cleanup()
                logger.info("   ✓ Application очищен")
            
            logger.info("✅ [HTTP] Health server остановлен")
        
        except Exception as e:
            logger.warning(f"⚠️ [HTTP] Ошибка остановки сервера: {e}")
            tb.print_exc()
    
    async def run(self):
        """Главный цикл выполнения"""
        
        self._print_startup_banner()
        
        self._setup_signal_handlers()
        
        await self._start_http_server()
        
        try:
            self._tasks = []
            
            if self.news_processor:
                self._tasks.append(
                    asyncio.create_task(
                        self._run_news_system(),
                        name="news_system"
                    )
                )
            
            if self.whale_scheduler:
                self._tasks.append(
                    asyncio.create_task(
                        self._run_whale_system(),
                        name="whale_system"
                    )
                )
            
            if self.bot_application:
                self._tasks.append(
                    asyncio.create_task(
                        self._run_bot_webhook(),
                        name="bot_commands"
                    )
                )
            
            self._tasks.append(
                asyncio.create_task(
                    self._health_check_loop(),
                    name="health_monitor"
                )
            )
            
            self._tasks.append(
                asyncio.create_task(
                    self._coordination_loop(),
                    name="coordinator"
                )
            )
            
            self._tasks.append(
                asyncio.create_task(
                    self._wait_for_shutdown(),
                    name="shutdown_waiter"
                )
            )
            
            logger.info(f"\n🚀 Запущено {len(self._tasks)} задач:")
            for task in self._tasks:
                logger.info(f"   • {task.get_name()}")
            logger.info("")
            
            done, pending = await asyncio.wait(
                self._tasks,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            for task in done:
                task_name = task.get_name()
                
                if task_name == "shutdown_waiter":
                    logger.info("✅ Получен сигнал graceful shutdown")
                else:
                    exc = task.exception()
                    if exc:
                        logger.error(f"\n❌ [CRITICAL] Task '{task_name}' crashed with exception:")
                        logger.error("="*80)
                        tb.print_exception(type(exc), exc, exc.__traceback__)
                        logger.error("="*80)
                        self.stats["errors_caught"] += 1
                    else:
                        logger.warning(f"⚠️ Task '{task_name}' завершилась без ошибок")
            
            if not self._shutdown_in_progress:
                logger.info("\n⚠️ Инициируется shutdown из-за завершения задачи...")
                await self.shutdown()
        
        except asyncio.CancelledError:
            logger.info("\n⏹️ [INFO] Задачи отменены")
        
        except KeyboardInterrupt:
            logger.info("\n⏹️ [STOP] Получен Ctrl+C")
            await self.shutdown()
        
        except Exception as e:
            logger.error(f"\n❌ [FATAL] Критическая ошибка в main loop:")
            logger.error("="*80)
            tb.print_exc()
            logger.error("="*80)
            self.stats["errors_caught"] += 1
        
        finally:
            await self.cleanup()
    
    async def _run_news_system(self):
        """
        Запуск новостной системы
        
        Production-ready v4.4: Правильная интеграция с NewsProcessor
        """
        logger.info("📰 [NEWS] Запуск News Bot...")
        
        max_consecutive_errors = 5
        consecutive_errors = 0
        
        await asyncio.sleep(5)
        
        while not self.shutdown_event.is_set():
            try:
                self.health_monitor.update_news_heartbeat()
                
                if hasattr(self.news_processor, 'run_cycle'):
                    await asyncio.wait_for(
                        self.news_processor.run_cycle(),
                        timeout=180.0
                    )
                elif hasattr(self.news_processor, 'process_news'):
                    await asyncio.wait_for(
                        self.news_processor.process_news(),
                        timeout=180.0
                    )
                elif hasattr(self.news_processor, 'run'):
                    await asyncio.wait_for(
                        self.news_processor.run(),
                        timeout=180.0
                    )
                else:
                    logger.warning("⚠️ [NEWS] NewsProcessor не имеет известных методов выполнения")
                    available_methods = [m for m in dir(self.news_processor) if not m.startswith('_') and callable(getattr(self.news_processor, m))]
                    logger.info(f"   Доступные методы: {', '.join(available_methods)}")
                    await asyncio.sleep(300)
                    continue
                
                consecutive_errors = 0
                self.stats['news_publications'] += 1
                self.stats['total_publications'] += 1
                
                if not self.resource_monitor.check_memory():
                    logger.warning("⚠️ [NEWS] Memory pressure detected, slowing down...")
                    await asyncio.sleep(30)
                
                await asyncio.sleep(300)
            
            except asyncio.TimeoutError:
                logger.warning("⚠️ [NEWS] Timeout (180s)")
                consecutive_errors += 1
            
            except asyncio.CancelledError:
                logger.info("📰 [NEWS] Получен сигнал остановки")
                break
            
            except Exception as e:
                consecutive_errors += 1
                self.health_monitor.record_error("news")
                self.stats["errors_caught"] += 1
                
                logger.error(f"\n❌ [NEWS] Ошибка ({consecutive_errors}/{max_consecutive_errors}):")
                logger.error(f"   {e}")
                tb.print_exc()
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("❌ [NEWS] Слишком много ошибок подряд, перезапуск через 5 минут...")
                    await asyncio.sleep(300)
                    consecutive_errors = 0
                    self.stats["restarts"] += 1
                else:
                    delay = min(30 * (2 ** consecutive_errors), 300)
                    logger.info(f"⏳ [NEWS] Повторная попытка через {delay}с...")
                    await asyncio.sleep(delay)
        
        logger.info("📰 [NEWS] News system остановлена")
    
    async def _run_whale_system(self):
        """Запуск whale monitoring системы"""
        logger.info("🐋 [WHALE] Запуск Whale Monitor...")
        
        max_consecutive_errors = 5
        consecutive_errors = 0
        
        await asyncio.sleep(10)
        
        while not self.shutdown_event.is_set():
            try:
                self.health_monitor.update_whale_heartbeat()
                
                await asyncio.wait_for(
                    self.whale_scheduler.run_cycle(),
                    timeout=120.0
                )
                
                consecutive_errors = 0
                self.stats['whale_publications'] += 1
                self.stats['total_publications'] += 1
                
                if not self.resource_monitor.check_memory():
                    logger.warning("⚠️ [WHALE] Memory pressure detected, slowing down...")
                    await asyncio.sleep(30)
                
                await asyncio.sleep(1)
            
            except asyncio.TimeoutError:
                logger.warning("⚠️ [WHALE] Timeout (120s)")
                consecutive_errors += 1
            
            except asyncio.CancelledError:
                logger.info("🐋 [WHALE] Получен сигнал остановки")
                break
            
            except Exception as e:
                consecutive_errors += 1
                self.health_monitor.record_error("whale")
                self.stats["errors_caught"] += 1
                
                logger.error(f"\n❌ [WHALE] Ошибка ({consecutive_errors}/{max_consecutive_errors}):")
                logger.error(f"   {e}")
                tb.print_exc()
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("❌ [WHALE] Слишком много ошибок подряд, перезапуск через 5 минут...")
                    await asyncio.sleep(300)
                    consecutive_errors = 0
                    self.stats["restarts"] += 1
                else:
                    delay = min(30 * (2 ** consecutive_errors), 300)
                    logger.info(f"⏳ [WHALE] Повторная попытка через {delay}с...")
                    await asyncio.sleep(delay)
        
        logger.info("🐋 [WHALE] Whale system остановлена")
    
    async def _run_bot_webhook(self):
        """
        Запуск Telegram bot в режиме WEBHOOK
        
        Production-ready WEBHOOK MODE:
        - Нет конфликтов между экземплярами
        - Меньше нагрузка на Telegram API
        - Мгновенная доставка обновлений
        - Production-grade решение
        """
        try:
            logger.info("🤖 [BOT] Инициализация command handler (WEBHOOK MODE)...")
            
            await asyncio.wait_for(
                self.bot_application.initialize(),
                timeout=30.0
            )
            await asyncio.wait_for(
                self.bot_application.start(),
                timeout=30.0
            )
            
            webhook_url = os.environ.get('WEBHOOK_URL', '')
            
            if not webhook_url:
                render_url = os.environ.get('RENDER_EXTERNAL_URL', '')
                if render_url:
                    webhook_url = f"{render_url}/webhook/telegram"
                else:
                    service_name = os.environ.get('RENDER_SERVICE_NAME', 'crypto-compass')
                    webhook_url = f"https://{service_name}.onrender.com/webhook/telegram"
            
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
                logger.warning("⚠️ [BOT] Webhook set вернул False, но продолжаем")
            
            self.health_monitor.update_bot_heartbeat()
            
            logger.info("✅ [BOT] Command handler активен в WEBHOOK режиме")
            logger.info(f"   Webhook URL: {webhook_url}")
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
            self.health_monitor.record_error("bot")
            self.stats["errors_caught"] += 1
            
            logger.error(f"\n❌ [BOT] Ошибка при установке webhook:")
            logger.error(f"   {e}")
            tb.print_exc()
        
        finally:
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
                logger.warning("   ⚠️ Timeout при shutdown")
            except Exception as e:
                logger.warning(f"   ⚠️ Ошибка при shutdown: {e}")
            
            logger.info("✅ [BOT] Command handler полностью остановлен")
    
    async def _health_check_loop(self):
        """Периодическая проверка здоровья всех систем"""
        await asyncio.sleep(300)
        
        while not self.shutdown_event.is_set():
            try:
                is_healthy, issues = self.health_monitor.check_health()
                
                if not is_healthy:
                    logger.warning("\n" + "="*80)
                    logger.warning("⚠️ [HEALTH] ОБНАРУЖЕНЫ ПРОБЛЕМЫ:")
                    logger.warning("="*80)
                    for issue in issues:
                        logger.warning(f"   {issue}")
                    logger.warning("="*80 + "\n")
                
                self.resource_monitor.check_memory()
                
                self.rate_limiter.print_stats()
                
                await asyncio.sleep(self.health_monitor.check_interval)
            
            except asyncio.CancelledError:
                break
            
            except Exception as e:
                logger.error(f"❌ [HEALTH] Ошибка проверки здоровья: {e}")
                tb.print_exc()
                await asyncio.sleep(self.health_monitor.check_interval)
        
        logger.info("💚 [HEALTH] Health monitor остановлен")
    
    async def _coordination_loop(self):
        """Координация публикаций между системами"""
        await asyncio.sleep(10)
        
        while not self.shutdown_event.is_set():
            try:
                if (datetime.now(timezone.utc) - self.resource_monitor.last_gc).seconds > self.resource_monitor.gc_interval:
                    gc.collect()
                    self.resource_monitor.last_gc = datetime.now(timezone.utc)
                
                await asyncio.sleep(60)
            
            except asyncio.CancelledError:
                break
            
            except Exception as e:
                logger.error(f"❌ [COORDINATOR] Ошибка: {e}")
                tb.print_exc()
                await asyncio.sleep(60)
        
        logger.info("🔄 [COORDINATOR] Coordinator остановлен")
    
    async def _wait_for_shutdown(self):
        """Ожидание сигнала shutdown"""
        await self.shutdown_event.wait()
        logger.info("✅ [SHUTDOWN] Shutdown signal получен")
    
    def _setup_signal_handlers(self):
        """Настройка обработчиков сигналов для graceful shutdown"""
        def signal_handler(signum, frame):
            signal_name = signal.Signals(signum).name
            logger.info(f"\n⚠️ [SIGNAL] Получен сигнал {signal_name}")
            self.shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("✅ Установлен обработчик для SIGINT")
        logger.info("✅ Установлен обработчик для SIGTERM")
    
    async def shutdown(self):
        """Graceful shutdown всех систем"""
        if self._shutdown_in_progress:
            logger.warning("⚠️ [SHUTDOWN] Shutdown уже в процессе, игнорируем")
            return
        
        self._shutdown_in_progress = True
        self.shutdown_event.set()
        
        logger.info("\n" + "="*80)
        logger.info("🛑 INITIATING GRACEFUL SHUTDOWN")
        logger.info("="*80 + "\n")
        
        logger.info("⏳ [1/4] Останавливаем HTTP health server...")
        await self._stop_http_server()
        
        logger.info("\n⏳ [2/4] Ждём завершения всех задач...")
        if self._tasks:
            for task in self._tasks:
                if not task.done() and task.get_name() != "shutdown_waiter":
                    task.cancel()
            
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._tasks, return_exceptions=True),
                    timeout=30.0
                )
                logger.info("   ✓ Все задачи завершены")
            except asyncio.TimeoutError:
                logger.warning("   ⚠️ Timeout ожидания задач")
        
        logger.info("\n⏳ [3/4] Останавливаем компоненты...")
        
        if self.whale_scheduler and hasattr(self.whale_scheduler, 'cleanup'):
            try:
                await asyncio.wait_for(
                    self.whale_scheduler.cleanup(),
                    timeout=10.0
                )
                logger.info("   ✓ Whale Scheduler остановлен")
            except asyncio.TimeoutError:
                logger.warning("   ⚠️ Timeout остановки Whale Scheduler")
            except Exception as e:
                logger.warning(f"   ⚠️ Ошибка остановки Whale Scheduler: {e}")
        
        if self.news_processor and hasattr(self.news_processor, 'cleanup'):
            try:
                await asyncio.wait_for(
                    self.news_processor.cleanup(),
                    timeout=10.0
                )
                logger.info("   ✓ News Processor остановлен")
            except asyncio.TimeoutError:
                logger.warning("   ⚠️ Timeout остановки News Processor")
            except Exception as e:
                logger.warning(f"   ⚠️ Ошибка остановки News Processor: {e}")
        
        logger.info("\n⏳ [4/4] Финализация...")
        gc.collect()
        logger.info("   ✓ Garbage collection выполнен")
        
        logger.info("\n" + "="*80)
        logger.info("✅ SHUTDOWN COMPLETE")
        logger.info("="*80)
    
    async def cleanup(self):
        """Финальная очистка ресурсов"""
        logger.info("\n🧹 [CLEANUP] Финальная очистка ресурсов...")
        
        self._print_final_statistics()
        
        gc.collect()
        
        logger.info("✅ [CLEANUP] Очистка завершена")
    
    def _print_startup_banner(self):
        """Вывод startup banner"""
        logger.info("\n" + "="*80)
        logger.info("🚀 INTEGRATED CRYPTO MONITOR v4.4 - STARTING")
        logger.info("="*80)
        
        logger.info("\n📦 LOADED COMPONENTS:")
        logger.info(f"   News Bot:        {'✅ Loaded' if self.news_processor else '❌ Not Available'}")
        logger.info(f"   Whale Monitor:   {'✅ Loaded' if self.whale_scheduler else '❌ Not Available'}")
        trading_status = '✅ Loaded' if self.whale_scheduler and hasattr(self.whale_scheduler, 'trading_enabled') and self.whale_scheduler.trading_enabled else '❌ Disabled'
        logger.info(f"   Trading System:  {trading_status}")
        logger.info(f"   Bot Commands:    {'✅ Loaded (WEBHOOK)' if self.bot_application else '❌ Not Available'}")
        
        logger.info("\n🔧 CONFIGURATION:")
        logger.info(f"   Max Memory:      {self.resource_monitor.max_memory_mb}MB")
        logger.info(f"   Health Checks:   Every {self.health_monitor.check_interval}s")
        logger.info(f"   GC Interval:     Every {self.resource_monitor.gc_interval}s")
        logger.info(f"   Solana Delay:    {self.rate_limiter.chain_delays.get('solana', 0)}s между запросами")
        
        logger.info("\n" + "="*80)
        logger.info(f"⏰ Startup Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        logger.info("="*80 + "\n")
    
    def _print_final_statistics(self):
        """Вывод финальной статистики"""
        logger.info("\n" + "="*80)
        logger.info("📊 ФИНАЛЬНАЯ СТАТИСТИКА")
        logger.info("="*80)
        
        uptime = self.health_monitor.get_uptime()
        logger.info(f"\n⏱️ UPTIME: {self.health_monitor._format_duration(uptime.total_seconds())}")
        
        health_stats = self.health_monitor.get_stats()
        
        logger.info("\n💚 HEALTH MONITOR:")
        logger.info(f"   Total Cycles: {health_stats['total_cycles']}")
        logger.info(f"   Total Errors: {health_stats['total_errors']}")
        logger.info(f"   Bot Commands Processed: {health_stats['total_bot_commands']}")
        
        if health_stats['total_cycles'] > 0:
            error_rate = (health_stats['total_errors'] / health_stats['total_cycles']) * 100
            logger.info(f"   Error Rate: {error_rate:.2f}%")
        
        logger.info("\n🔒 RATE LIMITER:")
        rate_stats = self.rate_limiter.get_stats()
        for chain, stats in rate_stats['chains'].items():
            success_rate = 0
            if stats['total_requests'] > 0:
                success_rate = (stats['successful_requests'] / stats['total_requests']) * 100
            
            logger.info(f"   {chain}:")
            logger.info(f"     Requests: {stats['total_requests']} (Success rate: {success_rate:.1f}%)")
            logger.info(f"     429 Errors: {stats['total_429_errors']}")
            logger.info(f"     Recovery Attempts: {stats['recovery_attempts']}")
        
        resource_stats = self.resource_monitor.get_stats()
        if resource_stats:
            logger.info("\n💾 RESOURCES:")
            logger.info(f"   Memory: {resource_stats.get('memory_mb', 0):.1f}MB ({resource_stats.get('memory_percent', 0):.1f}%)")
            logger.info(f"   CPU: {resource_stats.get('cpu_percent', 0):.1f}%")
            logger.info(f"   Threads: {resource_stats.get('num_threads', 0)}")
            logger.info(f"   Memory Warnings: {resource_stats.get('memory_warnings', 0)}")
            logger.info(f"   GC Runs: {resource_stats.get('gc_runs', 0)}")
        
        if self.news_processor and hasattr(self.news_processor, 'metrics'):
            news_metrics = self.news_processor.metrics
            
            logger.info("\n📰 NEWS BOT:")
            logger.info(f"   Cycles: {news_metrics.cycles_completed}")
            logger.info(f"   Articles Processed: {news_metrics.articles_processed}")
            logger.info(f"   Articles Published: {news_metrics.articles_published}")
            
            if news_metrics.articles_processed > 0:
                publish_rate = (news_metrics.articles_published / news_metrics.articles_processed) * 100
                logger.info(f"   Publish Rate: {publish_rate:.1f}%")
            
            logger.info(f"   Errors: {news_metrics.errors}")
        
        if self.whale_scheduler and hasattr(self.whale_scheduler, 'stats'):
            whale_stats = self.whale_scheduler.stats
            
            logger.info("\n🐋 WHALE MONITOR:")
            logger.info(f"   Events Collected: {whale_stats.get('events_collected', 0)}")
            logger.info(f"   Events Qualified: {whale_stats.get('events_qualified', 0)}")
            logger.info(f"   Events Published: {whale_stats.get('events_published', 0)}")
            
            successful = whale_stats.get('events_successful', 0)
            failed = whale_stats.get('events_failed', 0)
            
            if successful + failed > 0:
                accuracy = (successful / (successful + failed)) * 100
                logger.info(f"   Accuracy: {accuracy:.1f}% ({successful}/{successful + failed})")
            
            logger.info(f"   Wallets Discovered: {whale_stats.get('wallets_discovered', 0)}")
            logger.info(f"   Wallets Removed: {whale_stats.get('wallets_removed', 0)}")
            
            if self.whale_scheduler.trading_enabled:
                logger.info("\n📈 TRADING SYSTEM:")
                logger.info(f"   Signals Generated: {whale_stats.get('trading_signals_generated', 0)}")
                logger.info(f"   Signals Sent: {whale_stats.get('trading_signals_sent', 0)}")
                logger.info(f"   Positions Opened: {whale_stats.get('positions_opened', 0)}")
                logger.info(f"   Positions Closed: {whale_stats.get('positions_closed', 0)}")
        
        if self.bot_application:
            logger.info("\n🤖 TELEGRAM BOT:")
            logger.info(f"   Commands Processed: {health_stats['total_bot_commands']}")
            logger.info(f"   Errors: {health_stats['systems']['bot']['errors']}")
        
        logger.info("\n📊 ОБЩАЯ СТАТИСТИКА:")
        logger.info(f"   Total Publications: {self.stats['total_publications']}")
        logger.info(f"   ├─ News: {self.stats['news_publications']}")
        logger.info(f"   ├─ Whale: {self.stats['whale_publications']}")
        logger.info(f"   └─ Trading: {self.stats['trading_publications']}")
        logger.info(f"   Bot Commands: {self.stats['bot_commands']}")
        logger.info(f"   Errors Caught: {self.stats['errors_caught']}")
        logger.info(f"   System Restarts: {self.stats['restarts']}")
        
        logger.info("\n" + "="*80)


def check_dependencies():
    """Проверка установленных зависимостей"""
    logger.info("🔍 Проверка зависимостей...\n")
    
    required_packages = {
        'telegram': 'python-telegram-bot',
        'aiohttp': 'aiohttp',
        'feedparser': 'feedparser',
        'pandas': 'pandas',
        'numpy': 'numpy',
        'sklearn': 'scikit-learn',
        'psutil': 'psutil'
    }
    
    missing = []
    
    for module, package in required_packages.items():
        try:
            __import__(module)
            logger.info(f"   ✅ {package}")
        except ImportError:
            logger.error(f"   ❌ {package}")
            missing.append(package)
    
    if missing:
        logger.error(f"\n❌ Отсутствуют зависимости: {', '.join(missing)}")
        logger.info("\nУстановите их командой:")
        logger.info(f"pip install {' '.join(missing)}")
        return False
    
    logger.info("\n✅ Все зависимости установлены")
    return True


def create_directories():
    """Создание необходимых директорий"""
    logger.info("\n📁 Создание директорий...\n")
    
    directories = [
        Path("data"),
        Path("data/history"),
        Path("data/learning"),
        Path("data/wallets"),
        Path("data/positions"),
        Path("data/performance"),
        Path("logs"),
    ]
    
    if not Path("/tmp").exists():
        directories.append(Path("/tmp"))
    
    for directory in directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"   ✅ {directory}")
        except Exception as e:
            logger.warning(f"   ⚠️ {directory}: {e}")
    
    logger.info("")


def print_system_info():
    """Вывод информации о системе"""
    logger.info("="*80)
    logger.info("💎 CRYPTO COMPASS - Integrated Monitoring System v4.4")
    logger.info("="*80)
    logger.info(f"📅 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    logger.info(f"🐍 Python {sys.version.split()[0]}")
    logger.info(f"💻 Platform: {sys.platform}")
    logger.info(f"📂 Working Directory: {os.getcwd()}")
    logger.info("="*80 + "\n")


def main():
    """Главная точка входа в приложение"""
    print_system_info()
    
    if not check_dependencies():
        sys.exit(1)
    
    create_directories()
    
    logger.info("🚀 Запуск Integrated Crypto Monitor v4.4...\n")
    
    bot = IntegratedCryptoMonitor()
    
    try:
        if sys.version_info >= (3, 7):
            asyncio.run(bot.run())
        else:
            loop = asyncio.get_event_loop()
            try:
                loop.run_until_complete(bot.run())
            finally:
                loop.close()
    
    except KeyboardInterrupt:
        logger.info("\n⏹️ Остановка по Ctrl+C")
    
    except Exception as e:
        logger.error(f"\n❌ Критическая ошибка в main:")
        logger.error("="*80)
        tb.print_exc()
        logger.error("="*80)
        sys.exit(1)
    
    logger.info("\n👋 Goodbye!")


if __name__ == '__main__':
    main()