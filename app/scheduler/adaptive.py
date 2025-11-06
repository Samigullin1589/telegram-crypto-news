# app/scheduler/adaptive.py
"""
Adaptive Thresholds System
Dynamic thresholds that adapt to market conditions and performance
"""

import logging
from typing import Dict
from collections import deque

from app.config import config

logger = logging.getLogger(__name__)


class AdaptiveThresholds:
    """Динамические пороги, адаптирующиеся под рынок и производительность"""
    
    def __init__(self):
        self.market_regime = "sideways"
        self.performance_history = deque(maxlen=100)
        
        base_confidence = config.adaptive_thresholds.base_min_confidence if config.is_feature_enabled('adaptive_thresholds') else 40
        
        self.base_thresholds = {
            "min_confidence": base_confidence,
            "min_size_rel": 0.10,
            "min_volume_24h": 1000000
        }
        
        self.regime_modifiers = {
            "bull": {"min_confidence": -5, "min_size_rel": -0.02, "min_volume_24h": 0.8},
            "bear": {"min_confidence": 5, "min_size_rel": 0.02, "min_volume_24h": 1.2},
            "sideways": {"min_confidence": 0, "min_size_rel": 0, "min_volume_24h": 1.0}
        }
        
        logger.info(f"⚙️ [ADAPTIVE] Инициализирован. Базовые пороги: "
                   f"confidence≥{self.base_thresholds['min_confidence']}, "
                   f"size_rel≥{self.base_thresholds['min_size_rel']:.2%}")
    
    def detect_market_regime(self, btc_change_7d: float) -> str:
        """Определение режима рынка на основе изменения BTC"""
        if btc_change_7d > 5.0:
            return "bull"
        elif btc_change_7d < -5.0:
            return "bear"
        else:
            return "sideways"
    
    def update_regime(self, btc_change_7d: float):
        """Обновление режима рынка"""
        old_regime = self.market_regime
        self.market_regime = self.detect_market_regime(btc_change_7d)
        
        if old_regime != self.market_regime:
            logger.info(f"📊 [REGIME] Режим рынка изменён: {old_regime} → {self.market_regime}")
    
    def get_current_thresholds(self) -> Dict:
        """Получение текущих порогов с учётом режима рынка и производительности"""
        modifiers = self.regime_modifiers[self.market_regime]
        
        thresholds = {
            "min_confidence": int(self.base_thresholds["min_confidence"] + modifiers["min_confidence"]),
            "min_size_rel": self.base_thresholds["min_size_rel"] + modifiers["min_size_rel"],
            "min_volume_24h": int(self.base_thresholds["min_volume_24h"] * modifiers["min_volume_24h"])
        }
        
        if len(self.performance_history) >= 10:
            recent_accuracy = self._calculate_recent_accuracy()
            
            if recent_accuracy < 0.4:
                thresholds["min_confidence"] += 5
                logger.warning(f"⚠️ [ADAPTIVE] Низкая точность ({recent_accuracy:.1%}), "
                             f"повышаю min_confidence до {thresholds['min_confidence']}")
            
            elif recent_accuracy > 0.7:
                thresholds["min_confidence"] = max(30, thresholds["min_confidence"] - 5)
                logger.info(f"✅ [ADAPTIVE] Высокая точность ({recent_accuracy:.1%}), "
                          f"понижаю min_confidence до {thresholds['min_confidence']}")
        
        return thresholds
    
    def add_performance_result(self, signal_data: Dict):
        """Добавление результата производительности"""
        self.performance_history.append(signal_data)
    
    def _calculate_recent_accuracy(self) -> float:
        """Расчёт точности на последних сигналах"""
        if len(self.performance_history) < 10:
            return 0.5
        
        recent = list(self.performance_history)[-10:]
        successful = sum(1 for s in recent if s.get("success", False))
        
        return successful / len(recent)
    
    def get_stats(self) -> Dict:
        """Получение статистики"""
        if not self.performance_history:
            return {
                "regime": self.market_regime,
                "signals_tracked": 0,
                "accuracy": 0.0,
                "current_thresholds": self.get_current_thresholds()
            }
        
        successful = sum(1 for s in self.performance_history if s.get("success", False))
        
        return {
            "regime": self.market_regime,
            "signals_tracked": len(self.performance_history),
            "accuracy": successful / len(self.performance_history),
            "current_thresholds": self.get_current_thresholds()
        }