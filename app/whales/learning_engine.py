# app/whales/learning_engine.py
"""
LEARNING ENGINE v1.0

Система машинного обучения для оптимизации параметров системы.

Обучает:
- Веса типов сигналов (smart_money, mining, onchain)
- Пороги confidence/size_rel/volume
- Паттерны успешных сигналов
- Скоринг кошельков

Методы:
- Reinforcement Learning (награды за успех)
- Gradient Descent (оптимизация весов)
- Pattern Mining (поиск закономерностей)
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import statistics

from app import settings


@dataclass
class LearningState:
    """Состояние обучения системы"""
    version: str = "1.0"
    last_updated: datetime = None
    
    # Веса типов сигналов
    signal_type_weights: Dict[str, float] = None
    
    # Оптимизированные пороги
    optimized_thresholds: Dict[str, float] = None
    
    # Обнаруженные паттерны
    patterns: List[Dict] = None
    
    # Статистика обучения
    training_samples: int = 0
    last_accuracy: float = 0.0
    improvement_rate: float = 0.0
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.utcnow()
        if self.signal_type_weights is None:
            self.signal_type_weights = settings.LEARNING_SIGNAL_TYPE_WEIGHTS.copy()
        if self.optimized_thresholds is None:
            self.optimized_thresholds = {}
        if self.patterns is None:
            self.patterns = []
    
    def to_dict(self):
        """Конвертация в словарь"""
        data = asdict(self)
        data["last_updated"] = self.last_updated.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict):
        """Создание из словаря"""
        data["last_updated"] = datetime.fromisoformat(data["last_updated"])
        return cls(**data)


class LearningEngine:
    """
    Движок машинного обучения для оптимизации системы
    """
    
    def __init__(self, weights_file: str = None):
        self.weights_file = weights_file or settings.LEARNING_WEIGHTS_FILE
        
        # Параметры обучения
        self.learning_rate = settings.LEARNING_RATE
        self.min_samples = settings.LEARNING_MIN_SAMPLES
        self.window_days = settings.LEARNING_WINDOW_DAYS
        self.max_weight_adjustment = settings.LEARNING_MAX_WEIGHT_ADJUSTMENT
        
        # Состояние
        self.state = self._load_state()
    
    # ========================================================================
    # SIGNAL TYPE WEIGHTS OPTIMIZATION
    # ========================================================================
    
    def update_signal_type_weights(self, performance_data: List[Dict]) -> Dict[str, float]:
        """
        Обновляет веса типов сигналов на основе производительности
        
        Args:
            performance_data: Список {
                "signal_type": str,
                "outcome": "success" | "failure",
                "confidence": int
            }
        
        Returns:
            Обновлённые веса
        """
        
        print(f"\n{'=' * 80}")
        print(f"🎓 LEARNING ENGINE - Оптимизация весов типов сигналов")
        print(f"{'=' * 80}")
        
        if len(performance_data) < self.min_samples:
            print(f"⚠️  Недостаточно данных ({len(performance_data)}/{self.min_samples})")
            return self.state.signal_type_weights
        
        # Рассчитываем точность по типам
        type_performance = defaultdict(lambda: {"success": 0, "total": 0})
        
        for data in performance_data:
            signal_type = data.get("signal_type", "smart_money")
            outcome = data.get("outcome")
            
            if outcome in ["success", "failure"]:
                type_performance[signal_type]["total"] += 1
                if outcome == "success":
                    type_performance[signal_type]["success"] += 1
        
        # Рассчитываем accuracy
        type_accuracy = {}
        for signal_type, perf in type_performance.items():
            if perf["total"] > 0:
                type_accuracy[signal_type] = perf["success"] / perf["total"]
            else:
                type_accuracy[signal_type] = 0.5  # нейтрально
        
        print(f"\n📊 Точность по типам (текущая):")
        for signal_type, accuracy in type_accuracy.items():
            current_weight = self.state.signal_type_weights.get(signal_type, 0)
            print(f"   {signal_type}: {accuracy:.1%} (вес: {current_weight:.1%})")
        
        # Обновляем веса с использованием Reinforcement Learning
        # Награда = accuracy - 0.5 (центрируем вокруг 50%)
        # Новый вес = старый вес + learning_rate * награда
        
        new_weights = {}
        total_adjustment = 0
        
        for signal_type in ["smart_money", "mining", "onchain", "social"]:
            old_weight = self.state.signal_type_weights.get(signal_type, 0.25)
            accuracy = type_accuracy.get(signal_type, 0.5)
            
            # Награда (от -0.5 до +0.5)
            reward = accuracy - 0.5
            
            # Обновление веса
            adjustment = self.learning_rate * reward
            
            # Ограничиваем максимальное изменение
            adjustment = max(-self.max_weight_adjustment, min(self.max_weight_adjustment, adjustment))
            
            new_weight = old_weight + adjustment
            new_weight = max(0.05, min(0.70, new_weight))  # Веса от 5% до 70%
            
            new_weights[signal_type] = new_weight
            total_adjustment += adjustment
        
        # Нормализуем веса (сумма = 1.0)
        total_weight = sum(new_weights.values())
        new_weights = {k: v / total_weight for k, v in new_weights.items()}
        
        # Сохраняем
        old_weights = self.state.signal_type_weights.copy()
        self.state.signal_type_weights = new_weights
        self.state.training_samples = len(performance_data)
        self.state.last_updated = datetime.utcnow()
        
        self._save_state()
        
        print(f"\n✅ Веса обновлены:")
        for signal_type in ["smart_money", "mining", "onchain", "social"]:
            old = old_weights.get(signal_type, 0)
            new = new_weights.get(signal_type, 0)
            change = new - old
            arrow = "↑" if change > 0 else "↓" if change < 0 else "="
            print(f"   {signal_type}: {old:.1%} → {new:.1%} {arrow} ({change:+.1%})")
        
        print(f"{'=' * 80}\n")
        
        return new_weights
    
    # ========================================================================
    # THRESHOLD OPTIMIZATION
    # ========================================================================
    
    def optimize_thresholds(
        self,
        performance_data: List[Dict],
        current_thresholds: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Оптимизирует пороги публикации на основе производительности
        
        Args:
            performance_data: Данные производительности
            current_thresholds: Текущие пороги {
                "min_confidence": int,
                "min_size_rel": float,
                "min_volume_24h": int
            }
        
        Returns:
            Оптимизированные пороги
        """
        
        print(f"\n{'=' * 80}")
        print(f"🎓 LEARNING ENGINE - Оптимизация порогов")
        print(f"{'=' * 80}")
        
        if len(performance_data) < self.min_samples:
            print(f"⚠️  Недостаточно данных ({len(performance_data)}/{self.min_samples})")
            return current_thresholds
        
        # Анализируем взаимосвязь confidence и успешности
        confidence_success = defaultdict(list)
        
        for data in performance_data:
            confidence = data.get("confidence", 50)
            outcome = data.get("outcome")
            
            if outcome in ["success", "failure"]:
                is_success = 1 if outcome == "success" else 0
                confidence_success[confidence].append(is_success)
        
        # Находим оптимальный порог confidence
        # (где accuracy максимальна при достаточном количестве сигналов)
        
        best_threshold = current_thresholds["min_confidence"]
        best_accuracy = 0.0
        
        for threshold in range(20, 91, 5):  # 20, 25, 30, ..., 90
            # Сигналы с confidence >= threshold
            above_threshold = [
                data for data in performance_data
                if data.get("confidence", 0) >= threshold and data.get("outcome") in ["success", "failure"]
            ]
            
            if len(above_threshold) < 10:  # Минимум 10 сигналов
                continue
            
            successful = sum(1 for d in above_threshold if d.get("outcome") == "success")
            accuracy = successful / len(above_threshold)
            
            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_threshold = threshold
        
        # Обновляем порог если улучшение >5%
        new_thresholds = current_thresholds.copy()
        
        current_min_conf = current_thresholds["min_confidence"]
        
        if best_accuracy > 0.65 and abs(best_threshold - current_min_conf) > 5:
            new_thresholds["min_confidence"] = best_threshold
            print(f"✅ Оптимальный min_confidence: {best_threshold} (accuracy: {best_accuracy:.1%})")
            print(f"   Изменение: {current_min_conf} → {best_threshold}")
        else:
            print(f"ℹ️  Текущий min_confidence оптимален: {current_min_conf}")
        
        # Сохраняем
        self.state.optimized_thresholds = new_thresholds
        self._save_state()
        
        print(f"{'=' * 80}\n")
        
        return new_thresholds
    
    # ========================================================================
    # PATTERN DETECTION
    # ========================================================================
    
    def detect_patterns(self, performance_data: List[Dict]) -> List[Dict]:
        """
        Обнаруживает успешные паттерны в данных
        
        Args:
            performance_data: История сигналов с результатами
        
        Returns:
            Список обнаруженных паттернов [{
                "pattern_type": str,
                "conditions": Dict,
                "accuracy": float,
                "sample_size": int
            }]
        """
        
        print(f"\n{'=' * 80}")
        print(f"🎓 LEARNING ENGINE - Обнаружение паттернов")
        print(f"{'=' * 80}")
        
        if not settings.LEARNING_ENABLE_PATTERN_DETECTION:
            print("⏭️  Pattern detection отключен")
            return []
        
        patterns = []
        
        # ====================================================================
        # ПАТТЕРН 1: Количество кошельков
        # ====================================================================
        
        # Группируем по количеству кошельков
        by_wallet_count = defaultdict(list)
        
        for data in performance_data:
            wallet_count = len(data.get("wallets_involved", []))
            outcome = data.get("outcome")
            
            if outcome in ["success", "failure"]:
                by_wallet_count[wallet_count].append(outcome == "success")
        
        # Анализируем
        for count, outcomes in by_wallet_count.items():
            if len(outcomes) >= 10:  # Минимум 10 сигналов
                accuracy = sum(outcomes) / len(outcomes)
                
                if accuracy > 0.70:  # >70% accuracy
                    patterns.append({
                        "pattern_type": "wallet_count",
                        "conditions": {"min_wallets": count},
                        "accuracy": accuracy,
                        "sample_size": len(outcomes)
                    })
        
        # ====================================================================
        # ПАТТЕРН 2: Специализация кошельков
        # ====================================================================
        
        # TODO: Анализ специализации (DeFi, Memecoins, etc)
        
        # ====================================================================
        # ПАТТЕРН 3: Комбинация confidence + verdict
        # ====================================================================
        
        # Группируем по (confidence_bin, verdict)
        combinations = defaultdict(list)
        
        for data in performance_data:
            confidence = data.get("confidence", 0)
            verdict = data.get("verdict", "neutral")
            outcome = data.get("outcome")
            
            # Бины confidence: <50, 50-70, 70-85, >85
            if confidence < 50:
                conf_bin = "<50"
            elif confidence < 70:
                conf_bin = "50-70"
            elif confidence < 85:
                conf_bin = "70-85"
            else:
                conf_bin = ">85"
            
            key = f"{conf_bin}_{verdict}"
            
            if outcome in ["success", "failure"]:
                combinations[key].append(outcome == "success")
        
        # Анализируем
        for key, outcomes in combinations.items():
            if len(outcomes) >= 10:
                accuracy = sum(outcomes) / len(outcomes)
                
                if accuracy > 0.75:
                    conf_bin, verdict = key.split("_")
                    patterns.append({
                        "pattern_type": "confidence_verdict",
                        "conditions": {"confidence_bin": conf_bin, "verdict": verdict},
                        "accuracy": accuracy,
                        "sample_size": len(outcomes)
                    })
        
        # Сохраняем паттерны
        self.state.patterns = patterns
        self._save_state()
        
        print(f"✅ Обнаружено {len(patterns)} паттернов с высокой точностью:")
        for pattern in patterns:
            print(f"   • {pattern['pattern_type']}: {pattern['conditions']} "
                  f"(accuracy: {pattern['accuracy']:.1%}, n={pattern['sample_size']})")
        
        print(f"{'=' * 80}\n")
        
        return patterns
    
    # ========================================================================
    # WALLET SCORING
    # ========================================================================
    
    def calculate_wallet_learning_score(
        self,
        wallet_performance: Dict,
        signal_history: List[Dict]
    ) -> int:
        """
        Рассчитывает динамический скор кошелька на основе обучения
        
        Args:
            wallet_performance: Производительность кошелька
            signal_history: История сигналов с участием этого кошелька
        
        Returns:
            Скор 0-100
        """
        
        if not settings.LEARNING_ENABLE_WALLET_SCORING:
            return wallet_performance.get("score", 50)
        
        # Базовый скор от ROI и winrate
        roi_30d = wallet_performance.get("roi_30d", 0)
        win_rate = wallet_performance.get("win_rate", 0.5)
        
        base_score = (roi_30d * 30 + win_rate * 50)
        base_score = max(0, min(100, base_score))
        
        # Модификатор от истории сигналов
        if signal_history:
            successful_signals = sum(1 for s in signal_history if s.get("outcome") == "success")
            signal_accuracy = successful_signals / len(signal_history)
            
            # Бонус/штраф за точность сигналов
            accuracy_bonus = (signal_accuracy - 0.5) * 40  # от -20 до +20
            
            final_score = base_score + accuracy_bonus
        else:
            final_score = base_score
        
        return int(max(0, min(100, final_score)))
    
    # ========================================================================
    # REPORTING
    # ========================================================================
    
    def get_learning_stats(self) -> Dict:
        """
        Статистика системы обучения
        
        Returns:
            {
                "signal_type_weights": Dict,
                "optimized_thresholds": Dict,
                "patterns_count": int,
                "training_samples": int,
                "last_updated": str
            }
        """
        
        return {
            "signal_type_weights": self.state.signal_type_weights,
            "optimized_thresholds": self.state.optimized_thresholds,
            "patterns_count": len(self.state.patterns),
            "training_samples": self.state.training_samples,
            "last_updated": self.state.last_updated.isoformat() if self.state.last_updated else None
        }
    
    def generate_report(self) -> str:
        """Генерирует отчёт об обучении"""
        
        lines = [
            "=" * 80,
            "🎓 LEARNING ENGINE REPORT",
            "=" * 80,
            "",
            f"📊 ВЕСА ТИПОВ СИГНАЛОВ"
        ]
        
        for signal_type, weight in self.state.signal_type_weights.items():
            lines.append(f"   {signal_type}: {weight:.1%}")
        
        lines.extend([
            "",
            f"⚙️  ОПТИМИЗИРОВАННЫЕ ПОРОГИ"
        ])
        
        if self.state.optimized_thresholds:
            for key, value in self.state.optimized_thresholds.items():
                lines.append(f"   {key}: {value}")
        else:
            lines.append("   (нет оптимизаций)")
        
        lines.extend([
            "",
            f"🔍 ОБНАРУЖЕННЫЕ ПАТТЕРНЫ: {len(self.state.patterns)}"
        ])
        
        for pattern in self.state.patterns[:5]:  # топ-5
            lines.append(f"   • {pattern['pattern_type']}: {pattern['accuracy']:.1%}")
        
        lines.extend([
            "",
            f"📈 СТАТИСТИКА ОБУЧЕНИЯ",
            f"   Обучающих примеров: {self.state.training_samples}",
            f"   Последнее обновление: {self.state.last_updated.strftime('%Y-%m-%d %H:%M')}",
            "",
            "=" * 80
        ])
        
        return "\n".join(lines)
    
    # ========================================================================
    # PERSISTENCE
    # ========================================================================
    
    def _save_state(self):
        """Сохраняет состояние обучения"""
        try:
            import os
            os.makedirs(os.path.dirname(self.weights_file), exist_ok=True)
            
            with open(self.weights_file, 'w') as f:
                json.dump(self.state.to_dict(), f, indent=2)
        
        except Exception as e:
            print(f"⚠️  Ошибка сохранения состояния: {e}")
    
    def _load_state(self) -> LearningState:
        """Загружает состояние обучения"""
        try:
            with open(self.weights_file, 'r') as f:
                data = json.load(f)
            
            state = LearningState.from_dict(data)
            print(f"📂 [LEARNING] Загружено состояние (samples: {state.training_samples})")
            return state
        
        except FileNotFoundError:
            print("📂 [LEARNING] Новое состояние")
            return LearningState()
        
        except Exception as e:
            print(f"⚠️  Ошибка загрузки состояния: {e}")
            return LearningState()


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_current_weights() -> Dict[str, float]:
    """
    Получает текущие обученные веса
    
    Usage:
        from app.whales.learning_engine import get_current_weights
        
        weights = get_current_weights()
        print(f"Smart money weight: {weights['smart_money']:.1%}")
    """
    
    engine = LearningEngine()
    return engine.state.signal_type_weights


def train_on_performance_data(performance_data: List[Dict]) -> Dict:
    """
    Convenience function для обучения на данных
    
    Usage:
        from app.whales.learning_engine import train_on_performance_data
        
        result = train_on_performance_data(performance_data)
        print(f"Новые веса: {result['weights']}")
    """
    
    engine = LearningEngine()
    
    # Обновляем веса
    new_weights = engine.update_signal_type_weights(performance_data)
    
    # Оптимизируем пороги
    current_thresholds = {
        "min_confidence": settings.ADAPTIVE_BASE_MIN_CONFIDENCE,
        "min_size_rel": settings.ADAPTIVE_BASE_MIN_SIZE_REL,
        "min_volume_24h": settings.ADAPTIVE_BASE_MIN_VOLUME_24H
    }
    new_thresholds = engine.optimize_thresholds(performance_data, current_thresholds)
    
    # Ищем паттерны
    patterns = engine.detect_patterns(performance_data)
    
    return {
        "weights": new_weights,
        "thresholds": new_thresholds,
        "patterns": patterns
    }


# ============================================================================
# CLI TESTING
# ============================================================================

if __name__ == "__main__":
    import random
    
    def main():
        print("🧪 TESTING LEARNING ENGINE\n")
        
        engine = LearningEngine()
        
        # Генерируем тестовые данные
        print("📊 Генерация тестовых данных...")
        
        test_data = []
        
        # Smart money - высокая точность
        for i in range(50):
            test_data.append({
                "signal_type": "smart_money",
                "outcome": "success" if random.random() < 0.75 else "failure",
                "confidence": random.randint(60, 95),
                "wallets_involved": [f"0x{i}" for _ in range(random.randint(3, 8))]
            })
        
        # Mining - средняя точность
        for i in range(30):
            test_data.append({
                "signal_type": "mining",
                "outcome": "success" if random.random() < 0.60 else "failure",
                "confidence": random.randint(50, 80),
                "wallets_involved": []
            })
        
        # Onchain - низкая точность
        for i in range(20):
            test_data.append({
                "signal_type": "onchain",
                "outcome": "success" if random.random() < 0.45 else "failure",
                "confidence": random.randint(40, 70),
                "wallets_involved": []
            })
        
        print(f"✅ Создано {len(test_data)} тестовых сигналов\n")
        
        # Обучаем
        result = train_on_performance_data(test_data)
        
        # Отчёт
        print("\n" + engine.generate_report())
        
        print("\n✅ Тестирование завершено!")
    
    main()