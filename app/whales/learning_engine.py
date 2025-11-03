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
    
    signal_type_weights: Dict[str, float] = None
    optimized_thresholds: Dict[str, float] = None
    patterns: List[Dict] = None
    
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
        
        self.learning_rate = settings.LEARNING_RATE
        self.min_samples = settings.LEARNING_MIN_SAMPLES
        self.window_days = settings.LEARNING_WINDOW_DAYS
        self.max_weight_adjustment = settings.LEARNING_MAX_WEIGHT_ADJUSTMENT
        
        self.state = self._load_state()
        
        # История обучения
        self.training_history: List[Dict] = []
    
    # ========================================================================
    # SIGNAL TYPE WEIGHTS OPTIMIZATION
    # ========================================================================
    
    def update_signal_type_weights(self, performance_data: List[Dict]) -> Dict[str, float]:
        """
        Обновляет веса типов сигналов на основе производительности
        
        Args:
            performance_data: Список результатов сигналов
        
        Returns:
            Обновлённые веса
        """
        
        print(f"\n{'=' * 80}")
        print(f"🎓 LEARNING ENGINE - Оптимизация весов типов сигналов")
        print(f"{'=' * 80}")
        
        if len(performance_data) < self.min_samples:
            print(f"⚠️  Недостаточно данных ({len(performance_data)}/{self.min_samples})")
            return self.state.signal_type_weights
        
        # Фильтруем по периоду
        cutoff = datetime.utcnow() - timedelta(days=self.window_days)
        recent_data = [
            d for d in performance_data
            if datetime.fromisoformat(d.get("published_at", datetime.utcnow().isoformat())) >= cutoff
        ]
        
        if len(recent_data) < self.min_samples:
            print(f"⚠️  Недостаточно данных за {self.window_days} дней")
            return self.state.signal_type_weights
        
        # Рассчитываем точность по типам
        type_performance = defaultdict(lambda: {"success": 0, "total": 0})
        
        for data in recent_data:
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
                type_accuracy[signal_type] = 0.5
        
        print(f"\n📊 Точность по типам (текущая):")
        for signal_type, accuracy in type_accuracy.items():
            current_weight = self.state.signal_type_weights.get(signal_type, 0)
            sample_size = type_performance[signal_type]["total"]
            print(f"   {signal_type}: {accuracy:.1%} (вес: {current_weight:.1%}, n={sample_size})")
        
        # Обновляем веса с использованием Reinforcement Learning
        new_weights = {}
        total_adjustment = 0
        
        for signal_type in ["smart_money", "mining", "onchain", "social"]:
            old_weight = self.state.signal_type_weights.get(signal_type, 0.25)
            accuracy = type_accuracy.get(signal_type, 0.5)
            
            # Reward (от -0.5 до +0.5)
            reward = accuracy - 0.5
            
            # Обновление веса
            adjustment = self.learning_rate * reward
            
            # Ограничиваем максимальное изменение
            adjustment = max(-self.max_weight_adjustment, min(self.max_weight_adjustment, adjustment))
            
            new_weight = old_weight + adjustment
            new_weight = max(0.05, min(0.70, new_weight))
            
            new_weights[signal_type] = new_weight
            total_adjustment += adjustment
        
        # Нормализуем веса (сумма = 1.0)
        total_weight = sum(new_weights.values())
        new_weights = {k: v / total_weight for k, v in new_weights.items()}
        
        # Сохраняем
        old_weights = self.state.signal_type_weights.copy()
        self.state.signal_type_weights = new_weights
        self.state.training_samples = len(recent_data)
        self.state.last_updated = datetime.utcnow()
        
        # Рассчитываем общую точность
        total_success = sum(p["success"] for p in type_performance.values())
        total_count = sum(p["total"] for p in type_performance.values())
        self.state.last_accuracy = total_success / total_count if total_count > 0 else 0.0
        
        self._save_state()
        
        # Сохраняем в историю
        self.training_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "type": "weight_update",
            "old_weights": old_weights,
            "new_weights": new_weights,
            "accuracy": self.state.last_accuracy,
            "samples": len(recent_data)
        })
        
        print(f"\n✅ Веса обновлены:")
        for signal_type in ["smart_money", "mining", "onchain", "social"]:
            old = old_weights.get(signal_type, 0)
            new = new_weights.get(signal_type, 0)
            change = new - old
            arrow = "↑" if change > 0 else "↓" if change < 0 else "="
            print(f"   {signal_type}: {old:.1%} → {new:.1%} {arrow} ({change:+.1%})")
        
        print(f"\n🎯 Общая точность: {self.state.last_accuracy:.1%}")
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
            current_thresholds: Текущие пороги
        
        Returns:
            Оптимизированные пороги
        """
        
        print(f"\n{'=' * 80}")
        print(f"🎓 LEARNING ENGINE - Оптимизация порогов")
        print(f"{'=' * 80}")
        
        if len(performance_data) < self.min_samples:
            print(f"⚠️  Недостаточно данных ({len(performance_data)}/{self.min_samples})")
            return current_thresholds
        
        # Оптимизируем min_confidence
        best_confidence = self._optimize_confidence_threshold(performance_data)
        
        # Оптимизируем min_size_rel
        best_size_rel = self._optimize_size_threshold(performance_data)
        
        # Оптимизируем min_volume_24h
        best_volume = self._optimize_volume_threshold(performance_data)
        
        # Создаём новые пороги
        new_thresholds = current_thresholds.copy()
        
        changes_made = False
        
        if best_confidence is not None:
            old_conf = current_thresholds["min_confidence"]
            if abs(best_confidence - old_conf) > 5:
                new_thresholds["min_confidence"] = best_confidence
                changes_made = True
                print(f"✅ min_confidence: {old_conf} → {best_confidence}")
        
        if best_size_rel is not None:
            old_size = current_thresholds["min_size_rel"]
            if abs(best_size_rel - old_size) > 0.01:
                new_thresholds["min_size_rel"] = best_size_rel
                changes_made = True
                print(f"✅ min_size_rel: {old_size:.3f} → {best_size_rel:.3f}")
        
        if best_volume is not None:
            old_vol = current_thresholds["min_volume_24h"]
            if abs(best_volume - old_vol) > 10000:
                new_thresholds["min_volume_24h"] = best_volume
                changes_made = True
                print(f"✅ min_volume_24h: ${old_vol:,.0f} → ${best_volume:,.0f}")
        
        if not changes_made:
            print(f"ℹ️  Текущие пороги оптимальны")
        
        # Сохраняем
        self.state.optimized_thresholds = new_thresholds
        self._save_state()
        
        print(f"{'=' * 80}\n")
        
        return new_thresholds
    
    def _optimize_confidence_threshold(self, performance_data: List[Dict]) -> Optional[int]:
        """
        Находит оптимальный порог confidence
        
        Returns:
            Оптимальный min_confidence или None
        """
        
        best_threshold = None
        best_accuracy = 0.0
        best_sample_size = 0
        
        for threshold in range(20, 91, 5):
            above_threshold = [
                d for d in performance_data
                if d.get("confidence", 0) >= threshold and d.get("outcome") in ["success", "failure"]
            ]
            
            if len(above_threshold) < 10:
                continue
            
            successful = sum(1 for d in above_threshold if d.get("outcome") == "success")
            accuracy = successful / len(above_threshold)
            
            # Предпочитаем высокую accuracy с достаточным количеством сигналов
            score = accuracy * (1 - 0.1 * (100 - len(above_threshold)) / 100)
            
            if score > best_accuracy or (score == best_accuracy and len(above_threshold) > best_sample_size):
                best_accuracy = score
                best_threshold = threshold
                best_sample_size = len(above_threshold)
        
        if best_threshold and best_accuracy > 0.60:
            print(f"   Оптимальный min_confidence: {best_threshold} (accuracy: {best_accuracy:.1%}, n={best_sample_size})")
            return best_threshold
        
        return None
    
    def _optimize_size_threshold(self, performance_data: List[Dict]) -> Optional[float]:
        """
        Находит оптимальный порог size_rel
        
        Returns:
            Оптимальный min_size_rel или None
        """
        
        # Группируем по размерам сделок
        size_performance = defaultdict(lambda: {"success": 0, "total": 0})
        
        for d in performance_data:
            size_rel = d.get("size_rel", 0)
            outcome = d.get("outcome")
            
            if outcome not in ["success", "failure"]:
                continue
            
            # Группируем по диапазонам
            if size_rel < 0.05:
                size_range = "small"
            elif size_rel < 0.10:
                size_range = "medium"
            else:
                size_range = "large"
            
            size_performance[size_range]["total"] += 1
            if outcome == "success":
                size_performance[size_range]["success"] += 1
        
        # Находим наиболее успешный диапазон
        best_range = None
        best_accuracy = 0.0
        
        for size_range, perf in size_performance.items():
            if perf["total"] < 10:
                continue
            
            accuracy = perf["success"] / perf["total"]
            
            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_range = size_range
        
        if best_range == "large":
            return 0.10
        elif best_range == "medium":
            return 0.05
        elif best_range == "small":
            return 0.02
        
        return None
    
    def _optimize_volume_threshold(self, performance_data: List[Dict]) -> Optional[int]:
        """
        Находит оптимальный порог volume_24h
        
        Returns:
            Оптимальный min_volume_24h или None
        """
        
        # Группируем по объёмам
        volume_performance = defaultdict(lambda: {"success": 0, "total": 0})
        
        for d in performance_data:
            volume = d.get("volume_24h", 0)
            outcome = d.get("outcome")
            
            if outcome not in ["success", "failure"]:
                continue
            
            # Группируем по диапазонам
            if volume < 100000:
                vol_range = "very_low"
            elif volume < 500000:
                vol_range = "low"
            elif volume < 1000000:
                vol_range = "medium"
            else:
                vol_range = "high"
            
            volume_performance[vol_range]["total"] += 1
            if outcome == "success":
                volume_performance[vol_range]["success"] += 1
        
        # Находим наиболее успешный диапазон
        best_range = None
        best_accuracy = 0.0
        
        for vol_range, perf in volume_performance.items():
            if perf["total"] < 10:
                continue
            
            accuracy = perf["success"] / perf["total"]
            
            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_range = vol_range
        
        if best_range == "high":
            return 1000000
        elif best_range == "medium":
            return 500000
        elif best_range == "low":
            return 100000
        
        return None
    
    # ========================================================================
    # PATTERN DETECTION
    # ========================================================================
    
    def detect_patterns(self, performance_data: List[Dict]) -> List[Dict]:
        """
        Обнаруживает успешные паттерны в данных
        
        Args:
            performance_data: История сигналов с результатами
        
        Returns:
            Список обнаруженных паттернов
        """
        
        print(f"\n{'=' * 80}")
        print(f"🎓 LEARNING ENGINE - Обнаружение паттернов")
        print(f"{'=' * 80}")
        
        if not settings.LEARNING_ENABLE_PATTERN_DETECTION:
            print("⏭️  Pattern detection отключен")
            return []
        
        patterns = []
        
        # ПАТТЕРН 1: Количество кошельков
        wallet_patterns = self._detect_wallet_count_patterns(performance_data)
        patterns.extend(wallet_patterns)
        
        # ПАТТЕРН 2: Специализация кошельков
        specialization_patterns = self._detect_specialization_patterns(performance_data)
        patterns.extend(specialization_patterns)
        
        # ПАТТЕРН 3: Комбинация confidence + verdict
        combo_patterns = self._detect_confidence_verdict_patterns(performance_data)
        patterns.extend(combo_patterns)
        
        # ПАТТЕРН 4: Временные паттерны
        time_patterns = self._detect_time_patterns(performance_data)
        patterns.extend(time_patterns)
        
        # ПАТТЕРН 5: Размер сделки
        size_patterns = self._detect_size_patterns(performance_data)
        patterns.extend(size_patterns)
        
        # Сохраняем паттерны
        self.state.patterns = patterns
        self._save_state()
        
        print(f"✅ Обнаружено {len(patterns)} паттернов с высокой точностью:")
        for pattern in patterns[:10]:
            print(f"   • {pattern['pattern_type']}: {pattern['conditions']} "
                  f"(accuracy: {pattern['accuracy']:.1%}, n={pattern['sample_size']})")
        
        print(f"{'=' * 80}\n")
        
        return patterns
    
    def _detect_wallet_count_patterns(self, performance_data: List[Dict]) -> List[Dict]:
        """Обнаруживает паттерны по количеству кошельков"""
        
        patterns = []
        
        by_wallet_count = defaultdict(list)
        
        for data in performance_data:
            wallet_count = len(data.get("wallets_involved", []))
            outcome = data.get("outcome")
            
            if outcome in ["success", "failure"]:
                by_wallet_count[wallet_count].append(outcome == "success")
        
        for count, outcomes in by_wallet_count.items():
            if len(outcomes) >= 10:
                accuracy = sum(outcomes) / len(outcomes)
                
                if accuracy > 0.70:
                    patterns.append({
                        "pattern_type": "wallet_count",
                        "conditions": {"min_wallets": count},
                        "accuracy": accuracy,
                        "sample_size": len(outcomes),
                        "discovered_at": datetime.utcnow().isoformat()
                    })
        
        return patterns
    
    def _detect_specialization_patterns(self, performance_data: List[Dict]) -> List[Dict]:
        """Обнаруживает паттерны по специализации кошельков"""
        
        patterns = []
        
        by_specialization = defaultdict(list)
        
        for data in performance_data:
            # Получаем специализацию из wallet_data
            wallet_data = data.get("wallet_data", {})
            specialization = wallet_data.get("specialization", "unknown")
            outcome = data.get("outcome")
            
            if outcome in ["success", "failure"]:
                by_specialization[specialization].append(outcome == "success")
        
        for spec, outcomes in by_specialization.items():
            if len(outcomes) >= 10:
                accuracy = sum(outcomes) / len(outcomes)
                
                if accuracy > 0.70:
                    patterns.append({
                        "pattern_type": "specialization",
                        "conditions": {"specialization": spec},
                        "accuracy": accuracy,
                        "sample_size": len(outcomes),
                        "discovered_at": datetime.utcnow().isoformat()
                    })
        
        return patterns
    
    def _detect_confidence_verdict_patterns(self, performance_data: List[Dict]) -> List[Dict]:
        """Обнаруживает паттерны по комбинации confidence + verdict"""
        
        patterns = []
        
        combinations = defaultdict(list)
        
        for data in performance_data:
            confidence = data.get("confidence", 0)
            verdict = data.get("verdict", "neutral")
            outcome = data.get("outcome")
            
            # Бины confidence
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
        
        for key, outcomes in combinations.items():
            if len(outcomes) >= 10:
                accuracy = sum(outcomes) / len(outcomes)
                
                if accuracy > 0.75:
                    conf_bin, verdict = key.split("_")
                    patterns.append({
                        "pattern_type": "confidence_verdict",
                        "conditions": {"confidence_bin": conf_bin, "verdict": verdict},
                        "accuracy": accuracy,
                        "sample_size": len(outcomes),
                        "discovered_at": datetime.utcnow().isoformat()
                    })
        
        return patterns
    
    def _detect_time_patterns(self, performance_data: List[Dict]) -> List[Dict]:
        """Обнаруживает временные паттерны"""
        
        patterns = []
        
        by_hour = defaultdict(list)
        by_day_of_week = defaultdict(list)
        
        for data in performance_data:
            published_at_str = data.get("published_at")
            outcome = data.get("outcome")
            
            if not published_at_str or outcome not in ["success", "failure"]:
                continue
            
            published_at = datetime.fromisoformat(published_at_str)
            
            hour = published_at.hour
            day_of_week = published_at.weekday()
            
            by_hour[hour].append(outcome == "success")
            by_day_of_week[day_of_week].append(outcome == "success")
        
        # Анализируем по часам
        for hour, outcomes in by_hour.items():
            if len(outcomes) >= 10:
                accuracy = sum(outcomes) / len(outcomes)
                
                if accuracy > 0.75:
                    patterns.append({
                        "pattern_type": "time_of_day",
                        "conditions": {"hour": hour},
                        "accuracy": accuracy,
                        "sample_size": len(outcomes),
                        "discovered_at": datetime.utcnow().isoformat()
                    })
        
        # Анализируем по дням недели
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        for day, outcomes in by_day_of_week.items():
            if len(outcomes) >= 10:
                accuracy = sum(outcomes) / len(outcomes)
                
                if accuracy > 0.75:
                    patterns.append({
                        "pattern_type": "day_of_week",
                        "conditions": {"day": day_names[day]},
                        "accuracy": accuracy,
                        "sample_size": len(outcomes),
                        "discovered_at": datetime.utcnow().isoformat()
                    })
        
        return patterns
    
    def _detect_size_patterns(self, performance_data: List[Dict]) -> List[Dict]:
        """Обнаруживает паттерны по размеру сделки"""
        
        patterns = []
        
        by_size = defaultdict(list)
        
        for data in performance_data:
            size_usd = data.get("size_usd", 0)
            outcome = data.get("outcome")
            
            if outcome not in ["success", "failure"]:
                continue
            
            # Группируем по размерам
            if size_usd < 10000:
                size_bin = "small"
            elif size_usd < 50000:
                size_bin = "medium"
            elif size_usd < 100000:
                size_bin = "large"
            else:
                size_bin = "whale"
            
            by_size[size_bin].append(outcome == "success")
        
        for size_bin, outcomes in by_size.items():
            if len(outcomes) >= 10:
                accuracy = sum(outcomes) / len(outcomes)
                
                if accuracy > 0.70:
                    patterns.append({
                        "pattern_type": "transaction_size",
                        "conditions": {"size_category": size_bin},
                        "accuracy": accuracy,
                        "sample_size": len(outcomes),
                        "discovered_at": datetime.utcnow().isoformat()
                    })
        
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
            accuracy_bonus = (signal_accuracy - 0.5) * 40
            
            # Учитываем количество сигналов
            confidence_multiplier = min(1.0, len(signal_history) / 20)
            
            final_score = base_score + (accuracy_bonus * confidence_multiplier)
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
            Полная статистика
        """
        
        return {
            "signal_type_weights": self.state.signal_type_weights,
            "optimized_thresholds": self.state.optimized_thresholds,
            "patterns_count": len(self.state.patterns),
            "training_samples": self.state.training_samples,
            "last_accuracy": self.state.last_accuracy,
            "last_updated": self.state.last_updated.isoformat() if self.state.last_updated else None,
            "training_history_size": len(self.training_history)
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
            bar = "█" * int(weight * 40)
            lines.append(f"   {signal_type:15s}: {bar:40s} {weight:.1%}")
        
        lines.extend([
            "",
            f"⚙️  ОПТИМИЗИРОВАННЫЕ ПОРОГИ"
        ])
        
        if self.state.optimized_thresholds:
            for key, value in self.state.optimized_thresholds.items():
                if isinstance(value, float):
                    if value < 1:
                        lines.append(f"   {key}: {value:.3f}")
                    else:
                        lines.append(f"   {key}: {value:,.0f}")
                else:
                    lines.append(f"   {key}: {value}")
        else:
            lines.append("   (нет оптимизаций)")
        
        lines.extend([
            "",
            f"🔍 ОБНАРУЖЕННЫЕ ПАТТЕРНЫ: {len(self.state.patterns)}"
        ])
        
        # Группируем по типам
        patterns_by_type = defaultdict(list)
        for pattern in self.state.patterns:
            patterns_by_type[pattern["pattern_type"]].append(pattern)
        
        for pattern_type, patterns in patterns_by_type.items():
            lines.append(f"   {pattern_type}: {len(patterns)} паттернов")
            
            # Показываем топ-3 по accuracy
            top_patterns = sorted(patterns, key=lambda p: p["accuracy"], reverse=True)[:3]
            for p in top_patterns:
                lines.append(f"     • {p['conditions']}: {p['accuracy']:.1%} (n={p['sample_size']})")
        
        lines.extend([
            "",
            f"📈 СТАТИСТИКА ОБУЧЕНИЯ",
            f"   Обучающих примеров: {self.state.training_samples}",
            f"   Последняя точность: {self.state.last_accuracy:.1%}",
            f"   Последнее обновление: {self.state.last_updated.strftime('%Y-%m-%d %H:%M')}",
        ])
        
        # История обучения
        if self.training_history:
            lines.extend([
                "",
                f"📜 ИСТОРИЯ ОБУЧЕНИЯ (последние 5 обновлений):"
            ])
            
            for entry in self.training_history[-5:]:
                timestamp = datetime.fromisoformat(entry["timestamp"]).strftime('%Y-%m-%d %H:%M')
                entry_type = entry["type"]
                accuracy = entry.get("accuracy", 0)
                samples = entry.get("samples", 0)
                
                lines.append(f"   [{timestamp}] {entry_type}: {accuracy:.1%} (n={samples})")
        
        lines.extend([
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
            
            data = {
                "state": self.state.to_dict(),
                "training_history": self.training_history[-100:]  # Последние 100 записей
            }
            
            with open(self.weights_file, 'w') as f:
                json.dump(data, f, indent=2)
        
        except Exception as e:
            print(f"⚠️  Ошибка сохранения состояния: {e}")
    
    def _load_state(self) -> LearningState:
        """Загружает состояние обучения"""
        try:
            with open(self.weights_file, 'r') as f:
                data = json.load(f)
            
            state = LearningState.from_dict(data.get("state", {}))
            self.training_history = data.get("training_history", [])
            
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
                "wallets_involved": [f"0x{i}" for _ in range(random.randint(3, 8))],
                "published_at": (datetime.utcnow() - timedelta(days=random.randint(0, 30))).isoformat(),
                "size_usd": random.randint(10000, 100000),
                "verdict": random.choice(["bullish", "bearish"])
            })
        
        # Mining - средняя точность
        for i in range(30):
            test_data.append({
                "signal_type": "mining",
                "outcome": "success" if random.random() < 0.60 else "failure",
                "confidence": random.randint(50, 80),
                "wallets_involved": [],
                "published_at": (datetime.utcnow() - timedelta(days=random.randint(0, 30))).isoformat(),
                "size_usd": random.randint(5000, 50000),
                "verdict": random.choice(["bullish", "bearish"])
            })
        
        # Onchain - низкая точность
        for i in range(20):
            test_data.append({
                "signal_type": "onchain",
                "outcome": "success" if random.random() < 0.45 else "failure",
                "confidence": random.randint(40, 70),
                "wallets_involved": [],
                "published_at": (datetime.utcnow() - timedelta(days=random.randint(0, 30))).isoformat(),
                "size_usd": random.randint(3000, 30000),
                "verdict": random.choice(["bullish", "bearish"])
            })
        
        print(f"✅ Создано {len(test_data)} тестовых сигналов\n")
        
        # Обучаем
        result = train_on_performance_data(test_data)
        
        # Отчёт
        print("\n" + engine.generate_report())
        
        print("\n✅ Тестирование завершено!")
    
    main()