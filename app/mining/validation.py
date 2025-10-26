# app/mining/validation.py
"""
WALLET VALIDATION MODULE

Проверяет активность и производительность отслеживаемых кошельков.
Удаляет неактивных и неэффективных.
"""

import aiohttp
from typing import Dict, Optional
from datetime import datetime, timedelta


class WalletValidator:
    """
    Система валидации кошельков
    """
    
    def __init__(self):
        # Пороги для деактивации
        self.max_days_inactive = 60
        self.min_score = 30
        self.min_roi = -0.20  # Максимальные потери -20%
    
    async def validate_wallet(
        self,
        address: str,
        chain: str,
        current_data: Dict
    ) -> Dict:
        """
        Валидирует кошелёк
        
        Returns:
            {
                "is_valid": bool,
                "reason": str,
                "score_update": bool,
                "new_score": int
            }
        """
        
        result = {
            "is_valid": True,
            "reason": "",
            "score_update": False,
            "new_score": current_data.get("score", 50)
        }
        
        # Проверка 1: Неактивность
        last_trade = datetime.fromisoformat(
            current_data.get("last_trade_at", datetime.utcnow().isoformat())
        )
        days_inactive = (datetime.utcnow() - last_trade).days
        
        if days_inactive > self.max_days_inactive:
            result["is_valid"] = False
            result["reason"] = f"Неактивен {days_inactive} дней"
            return result
        
        # Проверка 2: Низкий скор
        score = current_data.get("score", 50)
        if score < self.min_score:
            result["is_valid"] = False
            result["reason"] = f"Низкий скор ({score})"
            return result
        
        # Проверка 3: Отрицательный ROI
        roi = current_data.get("roi_30d", 0)
        if roi < self.min_roi:
            result["is_valid"] = False
            result["reason"] = f"Плохой ROI ({roi:.1%})"
            return result
        
        # Проверка 4: Обновление скора на основе активности
        if days_inactive > 30:
            # Снижаем скор за неактивность
            penalty = int((days_inactive - 30) / 10) * 5
            new_score = max(0, score - penalty)
            
            if new_score != score:
                result["score_update"] = True
                result["new_score"] = new_score
        
        return result
    
    async def batch_validate(
        self,
        wallets: list[Dict]
    ) -> Dict[str, Dict]:
        """
        Валидирует несколько кошельков параллельно
        
        Returns:
            {address: validation_result}
        """
        
        results = {}
        
        for wallet in wallets:
            address = wallet["address"]
            chain = wallet["chain"]
            
            validation = await self.validate_wallet(address, chain, wallet)
            results[address] = validation
        
        return results