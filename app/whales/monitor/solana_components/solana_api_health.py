# app/whales/monitor/solana_components/solana_api_health.py
"""
Solana API Health Monitor
Мониторинг здоровья Solana RPC endpoints
"""

import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SolanaAPIHealth:
    """
    Монитор здоровья Solana API
    Отслеживает доступность и производительность endpoints
    """
    
    def __init__(self, rpc_client):
        """
        Args:
            rpc_client: SolanaRPCClient
        """
        self.rpc_client = rpc_client
        
        self.last_check: Optional[datetime] = None
        self.check_interval = timedelta(minutes=5)
        
        self.health_status = {
            "is_healthy": True,
            "last_success": None,
            "last_failure": None,
            "consecutive_failures": 0,
            "total_checks": 0,
            "total_failures": 0
        }
        
        self.api_key_warning_shown = False
    
    async def check_health(self) -> bool:
        """
        Проверка здоровья API
        
        Returns:
            True если API доступен
        """
        now = datetime.utcnow()
        
        if self.last_check:
            if now - self.last_check < self.check_interval:
                return self.health_status["is_healthy"]
        
        self.last_check = now
        self.health_status["total_checks"] += 1
        
        try:
            test_result = await self._perform_health_check()
            
            if test_result:
                self.health_status["is_healthy"] = True
                self.health_status["last_success"] = now
                self.health_status["consecutive_failures"] = 0
                
                if self.health_status["total_checks"] == 1:
                    logger.info("✅ [HEALTH] Solana RPC доступен")
                
                return True
            else:
                self._record_failure(now)
                return False
        
        except Exception as e:
            logger.error(f"❌ [HEALTH] Ошибка проверки здоровья: {e}")
            self._record_failure(now)
            return False
    
    async def _perform_health_check(self) -> bool:
        """
        Выполнение проверки здоровья
        
        Returns:
            True если проверка успешна
        """
        try:
            slot = await self.rpc_client.get_slot()
            return slot is not None and slot > 0
        
        except Exception:
            return False
    
    def _record_failure(self, timestamp: datetime) -> None:
        """
        Регистрация неудачной проверки
        
        Args:
            timestamp: Время неудачи
        """
        self.health_status["is_healthy"] = False
        self.health_status["last_failure"] = timestamp
        self.health_status["consecutive_failures"] += 1
        self.health_status["total_failures"] += 1
        
        if self.health_status["consecutive_failures"] % 3 == 1:
            logger.warning(
                f"⚠️ [HEALTH] Solana RPC недоступен "
                f"(последовательных сбоев: {self.health_status['consecutive_failures']})"
            )
    
    def check_api_key_status(self) -> None:
        """
        Проверка наличия API ключа
        Показывает warning только один раз
        """
        if self.api_key_warning_shown:
            return
        
        if not self.rpc_client.has_api_key():
            logger.info(
                "ℹ️ [SOLANA] Работа без Helius API ключа - "
                "функциональность ограничена публичными RPC endpoints"
            )
            self.api_key_warning_shown = True
    
    def get_status(self) -> Dict:
        """
        Получение статуса здоровья
        
        Returns:
            Словарь со статусом
        """
        uptime = 0.0
        if self.health_status["total_checks"] > 0:
            successful = (
                self.health_status["total_checks"] -
                self.health_status["total_failures"]
            )
            uptime = (successful / self.health_status["total_checks"]) * 100
        
        return {
            **self.health_status,
            "uptime_percent": round(uptime, 2),
            "has_api_key": self.rpc_client.has_api_key()
        }