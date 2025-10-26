# app/analytics/correlation.py
"""
CORRELATION DETECTOR

Находит корреляции между:
- Активами (BTC-ETH correlation)
- Wallet actions (киты покупают вместе)
- DEX volumes
- Cross-chain patterns

Использует Pearson correlation для временных рядов.
"""

import statistics
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import math


class CorrelationDetector:
    """
    Детектор корреляций в крипто-рынке
    
    Находит статистически значимые связи между активами и событиями
    """
    
    def __init__(self):
        # История цен для расчёта корреляций
        self.price_history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        
        # История wallet actions
        self.wallet_actions: Dict[str, List[Dict]] = defaultdict(list)
        
        # Минимальный порог correlation для significance
        self.min_correlation = 0.7
    
    # ========================================================================
    # PRICE CORRELATIONS
    # ========================================================================
    
    def add_price_data(self, asset: str, price: float, timestamp: datetime = None):
        """Добавляет price datapoint"""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        self.price_history[asset].append((timestamp, price))
        
        # Ограничиваем размер истории
        if len(self.price_history[asset]) > 1000:
            self.price_history[asset] = self.price_history[asset][-1000:]
    
    def calculate_asset_correlation(
        self, 
        asset1: str, 
        asset2: str, 
        hours: int = 24
    ) -> Optional[float]:
        """
        Рассчитывает correlation между двумя активами
        
        Args:
            asset1: Первый актив
            asset2: Второй актив
            hours: За какой период
        
        Returns:
            Correlation coefficient (-1 to +1) or None
        """
        
        if asset1 not in self.price_history or asset2 not in self.price_history:
            return None
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        # Фильтруем по времени
        prices1 = [price for ts, price in self.price_history[asset1] if ts >= cutoff]
        prices2 = [price for ts, price in self.price_history[asset2] if ts >= cutoff]
        
        if len(prices1) < 2 or len(prices2) < 2:
            return None
        
        # Синхронизируем длины (берём минимальную)
        min_len = min(len(prices1), len(prices2))
        prices1 = prices1[-min_len:]
        prices2 = prices2[-min_len:]
        
        # Pearson correlation
        return self._pearson_correlation(prices1, prices2)
    
    def find_correlated_assets(
        self, 
        target_asset: str, 
        min_correlation: float = None
    ) -> List[Tuple[str, float]]:
        """
        Находит активы коррелирующие с target_asset
        
        Args:
            target_asset: Целевой актив
            min_correlation: Минимальная correlation (default: 0.7)
        
        Returns:
            [(asset, correlation), ...] sorted by correlation
        """
        
        if min_correlation is None:
            min_correlation = self.min_correlation
        
        if target_asset not in self.price_history:
            return []
        
        correlations = []
        
        for asset in self.price_history:
            if asset == target_asset:
                continue
            
            corr = self.calculate_asset_correlation(target_asset, asset)
            
            if corr is not None and abs(corr) >= min_correlation:
                correlations.append((asset, corr))
        
        # Сортируем по абсолютному значению correlation
        correlations.sort(key=lambda x: abs(x[1]), reverse=True)
        
        return correlations
    
    # ========================================================================
    # WALLET ACTION CORRELATIONS
    # ========================================================================
    
    def add_wallet_action(self, wallet: str, action: Dict):
        """
        Добавляет действие кошелька
        
        Args:
            wallet: Адрес кошелька
            action: {"asset": str, "type": "buy"|"sell", "timestamp": datetime}
        """
        self.wallet_actions[wallet].append(action)
        
        if len(self.wallet_actions[wallet]) > 100:
            self.wallet_actions[wallet] = self.wallet_actions[wallet][-100:]
    
    def find_coordinated_wallets(
        self, 
        timeframe_minutes: int = 60
    ) -> List[Dict]:
        """
        Находит кошельки которые действуют координированно
        
        Если несколько кошельков покупают/продают одинаковые активы
        в одно время - возможна координация
        
        Returns:
            [
                {
                    "wallets": List[str],
                    "asset": str,
                    "action": str,
                    "time_spread_minutes": float,
                    "coordination_score": float
                }
            ]
        """
        
        coordinated_groups = []
        
        # Группируем действия по активу и типу
        action_groups = defaultdict(list)
        
        for wallet, actions in self.wallet_actions.items():
            for action in actions:
                key = (action["asset"], action["type"])
                action_groups[key].append((wallet, action["timestamp"]))
        
        # Ищем группы с близким временем
        for (asset, action_type), wallet_times in action_groups.items():
            if len(wallet_times) < 3:  # Минимум 3 кошелька
                continue
            
            # Сортируем по времени
            wallet_times.sort(key=lambda x: x[1])
            
            # Проверяем временной разброс
            first_time = wallet_times[0][1]
            last_time = wallet_times[-1][1]
            time_spread = (last_time - first_time).total_seconds() / 60
            
            if time_spread <= timeframe_minutes:
                # Координированные действия!
                coordination_score = 1.0 - (time_spread / timeframe_minutes)
                
                coordinated_groups.append({
                    "wallets": [w for w, _ in wallet_times],
                    "asset": asset,
                    "action": action_type,
                    "time_spread_minutes": time_spread,
                    "coordination_score": coordination_score,
                    "first_action": first_time,
                    "last_action": last_time
                })
        
        # Сортируем по coordination score
        coordinated_groups.sort(key=lambda x: x["coordination_score"], reverse=True)
        
        return coordinated_groups
    
    # ========================================================================
    # STATISTICAL HELPERS
    # ========================================================================
    
    def _pearson_correlation(self, x: List[float], y: List[float]) -> Optional[float]:
        """
        Рассчитывает Pearson correlation coefficient
        
        Returns correlation from -1 to +1
        """
        
        if len(x) != len(y) or len(x) < 2:
            return None
        
        n = len(x)
        
        mean_x = statistics.mean(x)
        mean_y = statistics.mean(y)
        
        # Covariance
        covariance = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / n
        
        # Standard deviations
        std_x = statistics.stdev(x)
        std_y = statistics.stdev(y)
        
        if std_x == 0 or std_y == 0:
            return None
        
        # Pearson correlation
        correlation = covariance / (std_x * std_y)
        
        return max(-1.0, min(1.0, correlation))  # Clamp to [-1, 1]
    
    # ========================================================================
    # REPORTING
    # ========================================================================
    
    def generate_correlation_report(self) -> str:
        """Генерирует отчёт о корреляциях"""
        
        lines = [
            "=" * 80,
            "🔗 CORRELATION ANALYSIS REPORT",
            "=" * 80,
            ""
        ]
        
        # Asset correlations
        lines.append("📈 ASSET CORRELATIONS")
        lines.append("-" * 80)
        
        assets = list(self.price_history.keys())
        
        for i, asset1 in enumerate(assets):
            correlations = self.find_correlated_assets(asset1)
            
            if correlations:
                lines.append(f"\n{asset1}:")
                for asset2, corr in correlations[:5]:  # Топ-5
                    sign = "+" if corr > 0 else ""
                    lines.append(f"  • {asset2}: {sign}{corr:.2f}")
        
        # Coordinated wallets
        lines.append("\n\n👥 COORDINATED WALLET ACTIONS")
        lines.append("-" * 80)
        
        coordinated = self.find_coordinated_wallets()
        
        if coordinated:
            for group in coordinated[:10]:  # Топ-10
                lines.append(f"\n{len(group['wallets'])} wallets {group['action']}ing {group['asset']}")
                lines.append(f"  Time spread: {group['time_spread_minutes']:.1f} min")
                lines.append(f"  Coordination: {group['coordination_score']:.1%}")
        else:
            lines.append("  No coordinated actions detected")
        
        lines.extend([
            "",
            "=" * 80
        ])
        
        return "\n".join(lines)


# ============================================================================
# ANOMALY DETECTION
# ============================================================================

class AnomalyDetector:
    """
    Детектор аномалий в данных
    
    Использует статистические методы для обнаружения:
    - Необычных объёмов
    - Аномальных цен
    - Странных паттернов активности
    """
    
    def __init__(self, sensitivity: float = 2.0):
        """
        Args:
            sensitivity: Чувствительность (в standard deviations)
                        2.0 = обнаружит 5% аномалий
                        3.0 = обнаружит 0.3% аномалий
        """
        self.sensitivity = sensitivity
        self.data_history: Dict[str, List[float]] = defaultdict(list)
    
    def add_datapoint(self, key: str, value: float):
        """Добавляет datapoint для мониторинга"""
        self.data_history[key].append(value)
        
        if len(self.data_history[key]) > 1000:
            self.data_history[key] = self.data_history[key][-1000:]
    
    def detect_anomaly(
        self, 
        key: str, 
        value: float, 
        add_to_history: bool = True
    ) -> Dict:
        """
        Проверяет является ли value аномалией
        
        Args:
            key: Идентификатор метрики
            value: Новое значение
            add_to_history: Добавить в историю после проверки
        
        Returns:
            {
                "is_anomaly": bool,
                "severity": float (0-1),
                "z_score": float,
                "explanation": str
            }
        """
        
        if key not in self.data_history or len(self.data_history[key]) < 10:
            # Недостаточно данных
            if add_to_history:
                self.add_datapoint(key, value)
            
            return {
                "is_anomaly": False,
                "severity": 0.0,
                "z_score": 0.0,
                "explanation": "Insufficient data for anomaly detection"
            }
        
        # Статистика
        mean = statistics.mean(self.data_history[key])
        stdev = statistics.stdev(self.data_history[key])
        
        if stdev == 0:
            z_score = 0.0
        else:
            z_score = (value - mean) / stdev
        
        is_anomaly = abs(z_score) > self.sensitivity
        
        # Severity (0-1)
        severity = min(1.0, abs(z_score) / (self.sensitivity * 2))
        
        # Explanation
        if is_anomaly:
            direction = "higher" if z_score > 0 else "lower"
            explanation = f"Value is {abs(z_score):.1f}σ {direction} than normal"
        else:
            explanation = "Normal value"
        
        if add_to_history:
            self.add_datapoint(key, value)
        
        return {
            "is_anomaly": is_anomaly,
            "severity": severity,
            "z_score": z_score,
            "explanation": explanation,
            "mean": mean,
            "stdev": stdev
        }
    
    def scan_for_anomalies(self) -> List[Dict]:
        """
        Сканирует все метрики на аномалии
        
        Returns:
            Список обнаруженных аномалий
        """
        
        anomalies = []
        
        for key, history in self.data_history.items():
            if len(history) < 10:
                continue
            
            # Проверяем последнее значение
            latest = history[-1]
            result = self.detect_anomaly(key, latest, add_to_history=False)
            
            if result["is_anomaly"]:
                anomalies.append({
                    "metric": key,
                    "value": latest,
                    **result
                })
        
        # Сортируем по severity
        anomalies.sort(key=lambda x: x["severity"], reverse=True)
        
        return anomalies


# CLI TESTING
if __name__ == "__main__":
    print("🧪 TESTING CORRELATION & ANOMALY DETECTION\n")
    
    # Test correlation
    detector = CorrelationDetector()
    
    # Добавляем синтетические данные
    import random
    
    for i in range(100):
        btc_price = 50000 + random.gauss(0, 1000)
        eth_price = btc_price * 0.06 + random.gauss(0, 50)  # Коррелированный с BTC
        
        detector.add_price_data("BTC", btc_price)
        detector.add_price_data("ETH", eth_price)
    
    corr = detector.calculate_asset_correlation("BTC", "ETH")
    print(f"BTC-ETH correlation: {corr:.2f}")
    
    # Test anomaly
    anomaly = AnomalyDetector(sensitivity=2.0)
    
    # Нормальные значения
    for i in range(50):
        anomaly.add_datapoint("volume", random.gauss(1000000, 100000))
    
    # Аномалия
    result = anomaly.detect_anomaly("volume", 2000000)
    print(f"\nAnomaly detected: {result['is_anomaly']}")
    print(f"Severity: {result['severity']:.1%}")
    print(f"Z-score: {result['z_score']:.2f}")
    
    print("\n✅ Testing complete!")