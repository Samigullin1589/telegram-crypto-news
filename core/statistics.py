# core/statistics.py
"""
Statistics collection and reporting
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SystemStatistics:
    """Статистика работы системы"""
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_publications: int = 0
    news_publications: int = 0
    whale_publications: int = 0
    trading_publications: int = 0
    bot_commands: int = 0
    errors_caught: int = 0
    restarts: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        return {
            'start_time': self.start_time.isoformat(),
            'total_publications': self.total_publications,
            'news_publications': self.news_publications,
            'whale_publications': self.whale_publications,
            'trading_publications': self.trading_publications,
            'bot_commands': self.bot_commands,
            'errors_caught': self.errors_caught,
            'restarts': self.restarts
        }
    
    def get_uptime(self) -> timedelta:
        """Получает uptime"""
        return datetime.now(timezone.utc) - self.start_time
    
    def increment_news(self):
        """Увеличивает счетчик новостей"""
        self.news_publications += 1
        self.total_publications += 1
    
    def increment_whale(self):
        """Увеличивает счетчик whale"""
        self.whale_publications += 1
        self.total_publications += 1
    
    def increment_trading(self):
        """Увеличивает счетчик trading"""
        self.trading_publications += 1
        self.total_publications += 1
    
    def increment_bot_commands(self):
        """Увеличивает счетчик команд бота"""
        self.bot_commands += 1
    
    def increment_errors(self):
        """Увеличивает счетчик ошибок"""
        self.errors_caught += 1
    
    def increment_restarts(self):
        """Увеличивает счетчик перезапусков"""
        self.restarts += 1


class StatisticsReporter:
    """Отчеты по статистике"""
    
    def __init__(self, stats: SystemStatistics):
        self.stats = stats
    
    def print_startup_banner(
        self,
        has_news: bool,
        has_whale: bool,
        has_trading: bool,
        has_bot: bool,
        max_memory_mb: int,
        health_check_interval: int,
        gc_interval: int,
        solana_delay: float
    ):
        """Выводит startup banner"""
        logger.info("\n" + "=" * 80)
        logger.info("🚀 INTEGRATED CRYPTO MONITOR v4.5 - STARTING")
        logger.info("=" * 80)
        
        logger.info("\n📦 LOADED COMPONENTS:")
        logger.info(f"   News Bot:        {'✅ Loaded' if has_news else '❌ Not Available'}")
        logger.info(f"   Whale Monitor:   {'✅ Loaded' if has_whale else '❌ Not Available'}")
        logger.info(f"   Trading System:  {'✅ Loaded' if has_trading else '❌ Disabled'}")
        logger.info(f"   Bot Commands:    {'✅ Loaded (WEBHOOK)' if has_bot else '❌ Not Available'}")
        
        logger.info("\n🔧 CONFIGURATION:")
        logger.info(f"   Max Memory:      {max_memory_mb}MB")
        logger.info(f"   Health Checks:   Every {health_check_interval}s")
        logger.info(f"   GC Interval:     Every {gc_interval}s")
        logger.info(f"   Solana Delay:    {solana_delay}s между запросами")
        
        logger.info("\n" + "=" * 80)
        logger.info(f"⏰ Startup Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        logger.info("=" * 80 + "\n")
    
    def print_final_statistics(
        self,
        health_stats: Dict[str, Any],
        rate_stats: Dict[str, Any],
        resource_stats: Dict[str, Any]
    ):
        """Выводит финальную статистику"""
        logger.info("\n" + "=" * 80)
        logger.info("📊 ФИНАЛЬНАЯ СТАТИСТИКА")
        logger.info("=" * 80)
        
        uptime = self.stats.get_uptime()
        logger.info(f"\n⏱️  UPTIME: {self._format_duration(uptime.total_seconds())}")
        
        logger.info("\n💚 HEALTH MONITOR:")
        logger.info(f"   Total Cycles: {health_stats.get('total_cycles', 0)}")
        logger.info(f"   Total Errors: {health_stats.get('total_errors', 0)}")
        logger.info(f"   Bot Commands Processed: {health_stats.get('total_bot_commands', 0)}")
        
        total_cycles = health_stats.get('total_cycles', 0)
        if total_cycles > 0:
            error_rate = (health_stats.get('total_errors', 0) / total_cycles) * 100
            logger.info(f"   Error Rate: {error_rate:.2f}%")
        
        logger.info("\n🔒 RATE LIMITER:")
        for chain, chain_stats in rate_stats.get('chains', {}).items():
            total_reqs = chain_stats.get('total_requests', 0)
            success_reqs = chain_stats.get('successful_requests', 0)
            success_rate = (success_reqs / total_reqs * 100) if total_reqs > 0 else 0
            
            logger.info(f"   {chain}:")
            logger.info(f"     Requests: {total_reqs} (Success: {success_rate:.1f}%)")
            logger.info(f"     429 Errors: {chain_stats.get('total_429_errors', 0)}")
            logger.info(f"     Recovery Attempts: {chain_stats.get('recovery_attempts', 0)}")
        
        if resource_stats:
            logger.info("\n💾 RESOURCES:")
            logger.info(f"   Memory: {resource_stats.get('memory_mb', 0):.1f}MB ({resource_stats.get('memory_percent', 0):.1f}%)")
            logger.info(f"   CPU: {resource_stats.get('cpu_percent', 0):.1f}%")
            logger.info(f"   Threads: {resource_stats.get('num_threads', 0)}")
            logger.info(f"   Memory Warnings: {resource_stats.get('memory_warnings', 0)}")
            logger.info(f"   GC Runs: {resource_stats.get('gc_runs', 0)}")
        
        logger.info("\n📊 ОБЩАЯ СТАТИСТИКА:")
        logger.info(f"   Total Publications: {self.stats.total_publications}")
        logger.info(f"   ├─ News: {self.stats.news_publications}")
        logger.info(f"   ├─ Whale: {self.stats.whale_publications}")
        logger.info(f"   └─ Trading: {self.stats.trading_publications}")
        logger.info(f"   Bot Commands: {self.stats.bot_commands}")
        logger.info(f"   Errors Caught: {self.stats.errors_caught}")
        logger.info(f"   System Restarts: {self.stats.restarts}")
        
        logger.info("\n" + "=" * 80)
    
    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Форматирует длительность"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if secs > 0 or not parts:
            parts.append(f"{secs}s")
        
        return " ".join(parts)