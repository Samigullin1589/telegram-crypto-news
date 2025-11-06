"""
System Health Monitor - Production Grade

Мониторинг здоровья всех подсистем с:
- Heartbeat tracking для каждой системы
- Silence detection (когда система не отвечает)
- Error tracking
- Uptime monitoring
- Health checks с thresholds
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)


class SystemHealthMonitor:
    """
    Production-grade мониторинг здоровья всех подсистем
    
    Features:
    - Per-subsystem heartbeat tracking
    - Configurable silence thresholds
    - Error rate monitoring
    - Health status reporting
    - Uptime tracking
    """
    
    def __init__(self):
        """Инициализация Health Monitor"""
        self.start_time = datetime.now(timezone.utc)
        self.check_interval = 300  # 5 minutes
        
        # Alive status
        self.news_alive = False
        self.whale_alive = False
        self.trading_alive = False
        self.bot_alive = False
        
        # Cycle counters
        self.news_cycles = 0
        self.whale_cycles = 0
        self.trading_cycles = 0
        self.bot_commands_processed = 0
        
        # Error counters
        self.news_errors = 0
        self.whale_errors = 0
        self.trading_errors = 0
        self.bot_errors = 0
        
        # Heartbeat timestamps
        self.last_news_heartbeat: Optional[datetime] = None
        self.last_whale_heartbeat: Optional[datetime] = None
        self.last_trading_heartbeat: Optional[datetime] = None
        self.last_bot_heartbeat: Optional[datetime] = None
        
        # Silence thresholds (seconds)
        self.news_silence_threshold = 3600      # 1 hour
        self.whale_silence_threshold = 600      # 10 minutes
        self.trading_silence_threshold = 3600   # 1 hour
        self.bot_silence_threshold = 86400      # 24 hours
        
        # First heartbeat flags
        self.news_first_heartbeat = False
        self.whale_first_heartbeat = False
        self.trading_first_heartbeat = False
        self.bot_first_heartbeat = False
        
        logger.info("💚 [HEALTH] Health Monitor инициализирован")
        logger.info(f"   Check Interval: {self.check_interval}s")
        logger.info(f"   News Silence Threshold: {self.news_silence_threshold}s")
        logger.info(f"   Whale Silence Threshold: {self.whale_silence_threshold}s")
        logger.info(f"   Trading Silence Threshold: {self.trading_silence_threshold}s")
        logger.info(f"   Bot Silence Threshold: {self.bot_silence_threshold}s")
    
    def update_news_heartbeat(self):
        """Обновление heartbeat новостной системы"""
        now = datetime.now(timezone.utc)
        self.news_alive = True
        self.last_news_heartbeat = now
        self.news_cycles += 1
        
        if not self.news_first_heartbeat:
            self.news_first_heartbeat = True
            logger.info("💚 [HEALTH] News Bot - Первый heartbeat получен")
        
        logger.debug(f"[HEALTH] News heartbeat: cycle {self.news_cycles}")
    
    def update_whale_heartbeat(self):
        """Обновление heartbeat whale системы"""
        now = datetime.now(timezone.utc)
        self.whale_alive = True
        self.last_whale_heartbeat = now
        self.whale_cycles += 1
        
        if not self.whale_first_heartbeat:
            self.whale_first_heartbeat = True
            logger.info("💚 [HEALTH] Whale Monitor - Первый heartbeat получен")
        
        logger.debug(f"[HEALTH] Whale heartbeat: cycle {self.whale_cycles}")
    
    def update_trading_heartbeat(self):
        """Обновление heartbeat trading системы"""
        now = datetime.now(timezone.utc)
        self.trading_alive = True
        self.last_trading_heartbeat = now
        self.trading_cycles += 1
        
        if not self.trading_first_heartbeat:
            self.trading_first_heartbeat = True
            logger.info("💚 [HEALTH] Trading System - Первый heartbeat получен")
        
        logger.debug(f"[HEALTH] Trading heartbeat: cycle {self.trading_cycles}")
    
    def update_bot_heartbeat(self):
        """Обновление heartbeat telegram bot"""
        now = datetime.now(timezone.utc)
        self.bot_alive = True
        self.last_bot_heartbeat = now
        
        if not self.bot_first_heartbeat:
            self.bot_first_heartbeat = True
            logger.info("💚 [HEALTH] Telegram Bot - Первый heartbeat получен")
        
        logger.debug("[HEALTH] Bot heartbeat")
    
    def record_bot_command(self):
        """Регистрация обработанной команды"""
        self.bot_commands_processed += 1
        self.update_bot_heartbeat()
        logger.debug(f"[HEALTH] Bot command processed: {self.bot_commands_processed}")
    
    def record_error(self, system: str):
        """
        Регистрация ошибки в системе
        
        Args:
            system: Название системы ("news", "whale", "trading", "bot")
        """
        if system == "news":
            self.news_errors += 1
            logger.debug(f"[HEALTH] News error recorded: {self.news_errors}")
        elif system == "whale":
            self.whale_errors += 1
            logger.debug(f"[HEALTH] Whale error recorded: {self.whale_errors}")
        elif system == "trading":
            self.trading_errors += 1
            logger.debug(f"[HEALTH] Trading error recorded: {self.trading_errors}")
        elif system == "bot":
            self.bot_errors += 1
            logger.debug(f"[HEALTH] Bot error recorded: {self.bot_errors}")
        else:
            logger.warning(f"[HEALTH] Unknown system for error recording: {system}")
    
    def check_health(self) -> Tuple[bool, List[str]]:
        """
        Проверка здоровья всех систем
        
        Returns:
            Tuple[bool, List[str]]: (is_healthy, list_of_issues)
        """
        issues = []
        now = datetime.now(timezone.utc)
        
        # Check News Bot silence
        if self.last_news_heartbeat:
            silence = (now - self.last_news_heartbeat).total_seconds()
            if silence > self.news_silence_threshold:
                issues.append(
                    f"📰 News Bot: Silent for {int(silence/60)} minutes "
                    f"(threshold: {self.news_silence_threshold//60}m)"
                )
        elif self.news_cycles > 0 and self.news_first_heartbeat:
            issues.append("📰 News Bot: No recent heartbeat")
        
        # Check Whale Monitor silence
        if self.last_whale_heartbeat:
            silence = (now - self.last_whale_heartbeat).total_seconds()
            if silence > self.whale_silence_threshold:
                issues.append(
                    f"🐋 Whale Monitor: Silent for {int(silence/60)} minutes "
                    f"(threshold: {self.whale_silence_threshold//60}m)"
                )
        elif self.whale_cycles > 0 and self.whale_first_heartbeat:
            issues.append("🐋 Whale Monitor: No recent heartbeat")
        
        # Check Trading System silence
        if self.last_trading_heartbeat:
            silence = (now - self.last_trading_heartbeat).total_seconds()
            if silence > self.trading_silence_threshold:
                issues.append(
                    f"📈 Trading System: Silent for {int(silence/60)} minutes "
                    f"(threshold: {self.trading_silence_threshold//60}m)"
                )
        elif self.trading_cycles > 0 and self.trading_first_heartbeat:
            issues.append("📈 Trading System: No recent heartbeat")
        
        # Check Bot silence
        if self.last_bot_heartbeat:
            silence = (now - self.last_bot_heartbeat).total_seconds()
            if silence > self.bot_silence_threshold:
                issues.append(
                    f"🤖 Bot Handler: Silent for {silence/3600:.1f} hours "
                    f"(threshold: {self.bot_silence_threshold//3600}h)"
                )
        
        # Check error rate
        total_cycles = self.news_cycles + self.whale_cycles + self.trading_cycles
        total_errors = self.news_errors + self.whale_errors + self.trading_errors + self.bot_errors
        
        if total_cycles > 10:  # Only check after some activity
            error_rate = (total_errors / total_cycles) * 100
            if error_rate > 10:
                issues.append(f"⚠️ High error rate: {error_rate:.1f}%")
        
        # Check for systems that never started
        uptime = self.get_uptime().total_seconds()
        if uptime > 600:  # After 10 minutes of uptime
            if self.news_cycles == 0 and self.news_first_heartbeat:
                issues.append("📰 News Bot: Never started cycling")
            if self.whale_cycles == 0 and self.whale_first_heartbeat:
                issues.append("🐋 Whale Monitor: Never started cycling")
        
        is_healthy = len(issues) == 0
        return is_healthy, issues
    
    def get_uptime(self) -> timedelta:
        """
        Получение времени работы системы
        
        Returns:
            timedelta: Время работы
        """
        return datetime.now(timezone.utc) - self.start_time
    
    def get_uptime_seconds(self) -> float:
        """
        Получение времени работы в секундах
        
        Returns:
            float: Время работы в секундах
        """
        return self.get_uptime().total_seconds()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Получение полной статистики здоровья
        
        Returns:
            Dict со статистикой всех систем
        """
        uptime = self.get_uptime()
        
        return {
            "uptime_seconds": uptime.total_seconds(),
            "uptime_formatted": self._format_duration(uptime.total_seconds()),
            "systems": {
                "news": {
                    "alive": self.news_alive,
                    "cycles": self.news_cycles,
                    "errors": self.news_errors,
                    "last_heartbeat": self.last_news_heartbeat.isoformat() if self.last_news_heartbeat else None,
                    "silence_threshold": self.news_silence_threshold,
                    "first_heartbeat_received": self.news_first_heartbeat,
                },
                "whale": {
                    "alive": self.whale_alive,
                    "cycles": self.whale_cycles,
                    "errors": self.whale_errors,
                    "last_heartbeat": self.last_whale_heartbeat.isoformat() if self.last_whale_heartbeat else None,
                    "silence_threshold": self.whale_silence_threshold,
                    "first_heartbeat_received": self.whale_first_heartbeat,
                },
                "trading": {
                    "alive": self.trading_alive,
                    "cycles": self.trading_cycles,
                    "errors": self.trading_errors,
                    "last_heartbeat": self.last_trading_heartbeat.isoformat() if self.last_trading_heartbeat else None,
                    "silence_threshold": self.trading_silence_threshold,
                    "first_heartbeat_received": self.trading_first_heartbeat,
                },
                "bot": {
                    "alive": self.bot_alive,
                    "commands_processed": self.bot_commands_processed,
                    "errors": self.bot_errors,
                    "last_heartbeat": self.last_bot_heartbeat.isoformat() if self.last_bot_heartbeat else None,
                    "silence_threshold": self.bot_silence_threshold,
                    "first_heartbeat_received": self.bot_first_heartbeat,
                }
            },
            "total_cycles": self.news_cycles + self.whale_cycles + self.trading_cycles,
            "total_errors": self.news_errors + self.whale_errors + self.trading_errors + self.bot_errors,
            "total_bot_commands": self.bot_commands_processed,
            "start_time": self.start_time.isoformat(),
        }
    
    def get_system_stats(self, system: str) -> Dict[str, Any]:
        """
        Получение статистики конкретной системы
        
        Args:
            system: Название системы ("news", "whale", "trading", "bot")
            
        Returns:
            Dict со статистикой системы
        """
        stats = self.get_stats()
        return stats['systems'].get(system, {})
    
    def print_health_report(self):
        """Вывести отчет о здоровье в лог"""
        is_healthy, issues = self.check_health()
        
        logger.info("\n💚 [HEALTH] Отчет о здоровье систем:")
        logger.info(f"   Общий статус: {'✅ Healthy' if is_healthy else '⚠️ Issues Detected'}")
        logger.info(f"   Uptime: {self._format_duration(self.get_uptime_seconds())}")
        
        logger.info("\n📊 Циклы:")
        logger.info(f"   News: {self.news_cycles}")
        logger.info(f"   Whale: {self.whale_cycles}")
        logger.info(f"   Trading: {self.trading_cycles}")
        logger.info(f"   Bot Commands: {self.bot_commands_processed}")
        
        logger.info("\n❌ Ошибки:")
        logger.info(f"   News: {self.news_errors}")
        logger.info(f"   Whale: {self.whale_errors}")
        logger.info(f"   Trading: {self.trading_errors}")
        logger.info(f"   Bot: {self.bot_errors}")
        
        if issues:
            logger.info("\n⚠️ Обнаруженные проблемы:")
            for issue in issues:
                logger.info(f"   • {issue}")
        else:
            logger.info("\n✅ Проблем не обнаружено")
    
    def _format_duration(self, seconds: float) -> str:
        """
        Форматирование длительности в читаемый вид
        
        Args:
            seconds: Длительность в секундах
            
        Returns:
            str: Отформатированная строка
        """
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds/60)}m"
        elif seconds < 86400:
            hours = seconds / 3600
            return f"{hours:.1f}h"
        else:
            days = int(seconds / 86400)
            hours = (seconds % 86400) / 3600
            return f"{days}d {hours:.1f}h"
    
    def reset_system_stats(self, system: str):
        """
        Сброс статистики конкретной системы
        
        Args:
            system: Название системы ("news", "whale", "trading", "bot")
        """
        if system == "news":
            self.news_cycles = 0
            self.news_errors = 0
            logger.info("[HEALTH] News stats reset")
        elif system == "whale":
            self.whale_cycles = 0
            self.whale_errors = 0
            logger.info("[HEALTH] Whale stats reset")
        elif system == "trading":
            self.trading_cycles = 0
            self.trading_errors = 0
            logger.info("[HEALTH] Trading stats reset")
        elif system == "bot":
            self.bot_commands_processed = 0
            self.bot_errors = 0
            logger.info("[HEALTH] Bot stats reset")
    
    def reset_all_stats(self):
        """Сброс всей статистики"""
        self.news_cycles = 0
        self.whale_cycles = 0
        self.trading_cycles = 0
        self.bot_commands_processed = 0
        
        self.news_errors = 0
        self.whale_errors = 0
        self.trading_errors = 0
        self.bot_errors = 0
        
        logger.info("[HEALTH] All stats reset")
    
    def get_error_rate(self) -> float:
        """
        Получить общий процент ошибок
        
        Returns:
            float: Процент ошибок (0-100)
        """
        total_cycles = self.news_cycles + self.whale_cycles + self.trading_cycles
        total_errors = self.news_errors + self.whale_errors + self.trading_errors + self.bot_errors
        
        if total_cycles == 0:
            return 0.0
        
        return (total_errors / total_cycles) * 100
    
    def is_system_healthy(self, system: str) -> bool:
        """
        Проверка здоровья конкретной системы
        
        Args:
            system: Название системы
            
        Returns:
            bool: True если система здорова
        """
        is_healthy, issues = self.check_health()
        
        # Check if this system has any issues
        system_prefix = {
            "news": "📰",
            "whale": "🐋",
            "trading": "📈",
            "bot": "🤖"
        }.get(system, "")
        
        for issue in issues:
            if issue.startswith(system_prefix):
                return False
        
        return True