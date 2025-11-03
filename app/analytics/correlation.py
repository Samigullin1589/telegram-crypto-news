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
        self.price_history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        self.wallet_actions: Dict[str, List[Dict]] = defaultdict(list)
        self.min_correlation = 0.7
        
        # Кэш для часто запрашиваемых корреляций
        self.correlation_cache: Dict[str, Tuple[float, datetime]] = {}
        self.cache_ttl = timedelta(minutes=5)
    
    # ========================================================================
    # PRICE CORRELATIONS
    # ========================================================================
    
    def add_price_data(self, asset: str, price: float, timestamp: datetime = None):
        """Добавляет price datapoint"""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        self.price_history[asset].append((timestamp, price))
        
        if len(self.price_history[asset]) > 1000:
            self.price_history[asset] = self.price_history[asset][-1000:]
        
        # Инвалидируем кэш для этого актива
        keys_to_remove = [k for k in self.correlation_cache.keys() if asset in k]
        for key in keys_to_remove:
            del self.correlation_cache[key]
    
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
        
        # Проверяем кэш
        cache_key = f"{asset1}_{asset2}_{hours}"
        if cache_key in self.correlation_cache:
            corr, cached_at = self.correlation_cache[cache_key]
            if datetime.utcnow() - cached_at < self.cache_ttl:
                return corr
        
        if asset1 not in self.price_history or asset2 not in self.price_history:
            return None
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        prices1 = [price for ts, price in self.price_history[asset1] if ts >= cutoff]
        prices2 = [price for ts, price in self.price_history[asset2] if ts >= cutoff]
        
        if len(prices1) < 2 or len(prices2) < 2:
            return None
        
        min_len = min(len(prices1), len(prices2))
        prices1 = prices1[-min_len:]
        prices2 = prices2[-min_len:]
        
        corr = self._pearson_correlation(prices1, prices2)
        
        # Кэшируем результат
        if corr is not None:
            self.correlation_cache[cache_key] = (corr, datetime.utcnow())
        
        return corr
    
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
        
        correlations.sort(key=lambda x: abs(x[1]), reverse=True)
        
        return correlations
    
    def find_inverse_correlations(
        self,
        target_asset: str,
        min_correlation: float = 0.7
    ) -> List[Tuple[str, float]]:
        """
        Находит активы с обратной корреляцией (хедж)
        
        Returns:
            [(asset, negative_correlation), ...]
        """
        
        all_correlations = self.find_correlated_assets(target_asset, 0.0)
        
        inverse = [(asset, corr) for asset, corr in all_correlations if corr < -min_correlation]
        
        inverse.sort(key=lambda x: x[1])
        
        return inverse
    
    # ========================================================================
    # WALLET ACTION CORRELATIONS
    # ========================================================================
    
    def add_wallet_action(self, wallet: str, action: Dict):
        """
        Добавляет действие кошелька
        
        Args:
            wallet: Адрес кошелька
            action: {"asset": str, "type": "buy"|"sell", "timestamp": datetime, "amount_usd": float}
        """
        if "timestamp" not in action:
            action["timestamp"] = datetime.utcnow()
        
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
            Список координированных групп
        """
        
        coordinated_groups = []
        
        action_groups = defaultdict(list)
        
        for wallet, actions in self.wallet_actions.items():
            for action in actions:
                key = (action["asset"], action["type"])
                action_groups[key].append((wallet, action["timestamp"], action.get("amount_usd", 0)))
        
        for (asset, action_type), wallet_times in action_groups.items():
            if len(wallet_times) < 3:
                continue
            
            wallet_times.sort(key=lambda x: x[1])
            
            first_time = wallet_times[0][1]
            last_time = wallet_times[-1][1]
            time_spread = (last_time - first_time).total_seconds() / 60
            
            if time_spread <= timeframe_minutes:
                total_volume = sum(amount for _, _, amount in wallet_times)
                
                coordination_score = 1.0 - (time_spread / timeframe_minutes)
                
                # Бонус за большой объём
                if total_volume > 1_000_000:
                    coordination_score = min(1.0, coordination_score * 1.2)
                
                coordinated_groups.append({
                    "wallets": [w for w, _, _ in wallet_times],
                    "asset": asset,
                    "action": action_type,
                    "time_spread_minutes": time_spread,
                    "coordination_score": coordination_score,
                    "total_volume_usd": total_volume,
                    "first_action": first_time,
                    "last_action": last_time,
                    "wallet_count": len(wallet_times)
                })
        
        coordinated_groups.sort(key=lambda x: x["coordination_score"], reverse=True)
        
        return coordinated_groups
    
    def analyze_wallet_cluster(
        self,
        wallets: List[str],
        hours: int = 24
    ) -> Dict:
        """
        Анализирует кластер кошельков на предмет координации
        
        Args:
            wallets: Список адресов кошельков
            hours: Период анализа
        
        Returns:
            Статистика координации
        """
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        common_assets = defaultdict(int)
        common_actions = defaultdict(int)
        timeline_density = defaultdict(int)
        
        for wallet in wallets:
            if wallet not in self.wallet_actions:
                continue
            
            recent_actions = [
                a for a in self.wallet_actions[wallet]
                if a["timestamp"] >= cutoff
            ]
            
            for action in recent_actions:
                asset = action["asset"]
                action_type = action["type"]
                
                common_assets[asset] += 1
                common_actions[f"{asset}_{action_type}"] += 1
                
                # Группируем по 10-минутным интервалам
                interval = int(action["timestamp"].timestamp() / 600)
                timeline_density[interval] += 1
        
        # Находим наиболее популярные активы
        top_assets = sorted(
            common_assets.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        # Находим пиковые периоды активности
        peak_intervals = sorted(
            timeline_density.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        # Рассчитываем coordination score
        total_actions = sum(common_assets.values())
        unique_assets = len(common_assets)
        
        if total_actions > 0 and unique_assets > 0:
            # Чем больше действий на меньше активов = выше координация
            coordination = (total_actions / unique_assets) / len(wallets)
            coordination_score = min(1.0, coordination / 5.0)
        else:
            coordination_score = 0.0
        
        return {
            "coordination_score": coordination_score,
            "total_actions": total_actions,
            "unique_assets": unique_assets,
            "top_assets": top_assets,
            "peak_activity_times": [
                datetime.fromtimestamp(interval * 600) 
                for interval, _ in peak_intervals
            ],
            "most_coordinated_action": max(
                common_actions.items(),
                key=lambda x: x[1]
            ) if common_actions else None
        }
    
    # ========================================================================
    # CROSS-CHAIN ANALYSIS
    # ========================================================================
    
    def find_cross_chain_patterns(
        self,
        asset: str,
        chains: List[str] = None
    ) -> Dict:
        """
        Находит cross-chain паттерны для актива
        
        Args:
            asset: Актив (например "USDC")
            chains: Список chains для анализа
        
        Returns:
            Паттерны перемещений между chains
        """
        
        if chains is None:
            chains = ["ethereum", "base", "arbitrum", "optimism", "polygon"]
        
        chain_actions = defaultdict(list)
        
        # Собираем действия по chains
        for wallet, actions in self.wallet_actions.items():
            for action in actions:
                if action["asset"] != asset:
                    continue
                
                chain = action.get("chain", "unknown")
                if chain in chains:
                    chain_actions[chain].append({
                        "wallet": wallet,
                        "type": action["type"],
                        "timestamp": action["timestamp"],
                        "amount": action.get("amount_usd", 0)
                    })
        
        # Анализируем потоки между chains
        flows = defaultdict(lambda: {"count": 0, "volume": 0.0})
        
        for wallet, actions in self.wallet_actions.items():
            wallet_actions = [a for a in actions if a["asset"] == asset]
            
            # Сортируем по времени
            wallet_actions.sort(key=lambda x: x["timestamp"])
            
            # Ищем последовательности sell -> buy на разных chains
            for i in range(len(wallet_actions) - 1):
                current = wallet_actions[i]
                next_action = wallet_actions[i + 1]
                
                if current["type"] == "sell" and next_action["type"] == "buy":
                    from_chain = current.get("chain", "unknown")
                    to_chain = next_action.get("chain", "unknown")
                    
                    if from_chain in chains and to_chain in chains and from_chain != to_chain:
                        # Проверяем временной интервал (должно быть быстро)
                        time_diff = (next_action["timestamp"] - current["timestamp"]).total_seconds() / 60
                        
                        if time_diff < 60:  # В течение часа
                            flow_key = f"{from_chain}->{to_chain}"
                            flows[flow_key]["count"] += 1
                            flows[flow_key]["volume"] += current.get("amount_usd", 0)
        
        # Находим доминирующие потоки
        dominant_flows = sorted(
            flows.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )[:5]
        
        return {
            "asset": asset,
            "chain_activity": {
                chain: len(actions)
                for chain, actions in chain_actions.items()
            },
            "dominant_flows": [
                {
                    "route": route,
                    "count": data["count"],
                    "volume_usd": data["volume"]
                }
                for route, data in dominant_flows
            ],
            "total_cross_chain_moves": sum(data["count"] for data in flows.values())
        }
    
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
        
        covariance = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / n
        
        std_x = statistics.stdev(x)
        std_y = statistics.stdev(y)
        
        if std_x == 0 or std_y == 0:
            return None
        
        correlation = covariance / (std_x * std_y)
        
        return max(-1.0, min(1.0, correlation))
    
    def calculate_rolling_correlation(
        self,
        asset1: str,
        asset2: str,
        window_hours: int = 24,
        step_hours: int = 6
    ) -> List[Tuple[datetime, float]]:
        """
        Рассчитывает скользящую корреляцию
        
        Returns:
            [(timestamp, correlation), ...]
        """
        
        if asset1 not in self.price_history or asset2 not in self.price_history:
            return []
        
        results = []
        
        # Находим самую раннюю точку данных
        earliest1 = min(ts for ts, _ in self.price_history[asset1])
        earliest2 = min(ts for ts, _ in self.price_history[asset2])
        earliest = max(earliest1, earliest2)
        
        current_time = earliest + timedelta(hours=window_hours)
        end_time = datetime.utcnow()
        
        while current_time <= end_time:
            start_window = current_time - timedelta(hours=window_hours)
            
            prices1 = [
                price for ts, price in self.price_history[asset1]
                if start_window <= ts <= current_time
            ]
            
            prices2 = [
                price for ts, price in self.price_history[asset2]
                if start_window <= ts <= current_time
            ]
            
            if len(prices1) >= 2 and len(prices2) >= 2:
                min_len = min(len(prices1), len(prices2))
                corr = self._pearson_correlation(prices1[-min_len:], prices2[-min_len:])
                
                if corr is not None:
                    results.append((current_time, corr))
            
            current_time += timedelta(hours=step_hours)
        
        return results
    
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
        
        lines.append("📈 ASSET CORRELATIONS")
        lines.append("-" * 80)
        
        assets = list(self.price_history.keys())
        
        if not assets:
            lines.append("  No asset data available")
        else:
            for i, asset1 in enumerate(assets):
                correlations = self.find_correlated_assets(asset1)
                
                if correlations:
                    lines.append(f"\n{asset1}:")
                    for asset2, corr in correlations[:5]:
                        sign = "+" if corr > 0 else ""
                        strength = "Strong" if abs(corr) > 0.8 else "Moderate"
                        lines.append(f"  • {asset2}: {sign}{corr:.2f} ({strength})")
        
        lines.append("\n\n👥 COORDINATED WALLET ACTIONS")
        lines.append("-" * 80)
        
        coordinated = self.find_coordinated_wallets()
        
        if coordinated:
            for group in coordinated[:10]:
                lines.append(
                    f"\n{group['wallet_count']} wallets {group['action']}ing {group['asset']}"
                )
                lines.append(f"  Time spread: {group['time_spread_minutes']:.1f} min")
                lines.append(f"  Coordination: {group['coordination_score']:.1%}")
                lines.append(f"  Total volume: ${group['total_volume_usd']:,.0f}")
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
        
        # Адаптивные пороги
        self.adaptive_thresholds: Dict[str, Dict] = {}
    
    def add_datapoint(self, key: str, value: float):
        """Добавляет datapoint для мониторинга"""
        self.data_history[key].append(value)
        
        if len(self.data_history[key]) > 1000:
            self.data_history[key] = self.data_history[key][-1000:]
        
        # Обновляем адаптивные пороги
        self._update_adaptive_threshold(key)
    
    def _update_adaptive_threshold(self, key: str):
        """Обновляет адаптивный порог для метрики"""
        
        if len(self.data_history[key]) < 30:
            return
        
        recent_data = self.data_history[key][-100:]
        
        mean = statistics.mean(recent_data)
        stdev = statistics.stdev(recent_data)
        
        # Используем экспоненциальное сглаживание
        alpha = 0.1  # Фактор сглаживания
        
        if key in self.adaptive_thresholds:
            old_mean = self.adaptive_thresholds[key]["mean"]
            old_stdev = self.adaptive_thresholds[key]["stdev"]
            
            mean = alpha * mean + (1 - alpha) * old_mean
            stdev = alpha * stdev + (1 - alpha) * old_stdev
        
        self.adaptive_thresholds[key] = {
            "mean": mean,
            "stdev": stdev,
            "upper_bound": mean + (self.sensitivity * stdev),
            "lower_bound": mean - (self.sensitivity * stdev)
        }
    
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
            Детальный отчёт об аномалии
        """
        
        if key not in self.data_history or len(self.data_history[key]) < 10:
            if add_to_history:
                self.add_datapoint(key, value)
            
            return {
                "is_anomaly": False,
                "severity": 0.0,
                "z_score": 0.0,
                "explanation": "Insufficient data for anomaly detection"
            }
        
        mean = statistics.mean(self.data_history[key])
        stdev = statistics.stdev(self.data_history[key])
        
        if stdev == 0:
            z_score = 0.0
        else:
            z_score = (value - mean) / stdev
        
        is_anomaly = abs(z_score) > self.sensitivity
        
        severity = min(1.0, abs(z_score) / (self.sensitivity * 2))
        
        # Определяем тип аномалии
        if is_anomaly:
            direction = "higher" if z_score > 0 else "lower"
            
            if abs(z_score) > self.sensitivity * 2:
                anomaly_type = "extreme"
            elif abs(z_score) > self.sensitivity * 1.5:
                anomaly_type = "strong"
            else:
                anomaly_type = "moderate"
            
            explanation = f"{anomaly_type.capitalize()} anomaly: Value is {abs(z_score):.1f}σ {direction} than normal (mean: {mean:.2f}, stdev: {stdev:.2f})"
        else:
            anomaly_type = "none"
            explanation = "Normal value"
        
        if add_to_history:
            self.add_datapoint(key, value)
        
        return {
            "is_anomaly": is_anomaly,
            "severity": severity,
            "z_score": z_score,
            "anomaly_type": anomaly_type,
            "explanation": explanation,
            "mean": mean,
            "stdev": stdev,
            "value": value
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
            
            latest = history[-1]
            result = self.detect_anomaly(key, latest, add_to_history=False)
            
            if result["is_anomaly"]:
                anomalies.append({
                    "metric": key,
                    **result
                })
        
        anomalies.sort(key=lambda x: x["severity"], reverse=True)
        
        return anomalies
    
    def detect_trend_change(
        self,
        key: str,
        window: int = 20
    ) -> Optional[Dict]:
        """
        Обнаруживает изменение тренда
        
        Args:
            key: Идентификатор метрики
            window: Размер окна для анализа
        
        Returns:
            Информация об изменении тренда или None
        """
        
        if key not in self.data_history or len(self.data_history[key]) < window * 2:
            return None
        
        recent_data = self.data_history[key][-window*2:]
        
        first_half = recent_data[:window]
        second_half = recent_data[window:]
        
        mean_first = statistics.mean(first_half)
        mean_second = statistics.mean(second_half)
        
        change_pct = ((mean_second - mean_first) / mean_first * 100) if mean_first != 0 else 0
        
        # Проверяем значимость изменения
        if abs(change_pct) > 10:  # >10% изменение
            trend = "upward" if change_pct > 0 else "downward"
            
            return {
                "metric": key,
                "trend": trend,
                "change_pct": change_pct,
                "old_mean": mean_first,
                "new_mean": mean_second,
                "is_significant": abs(change_pct) > 20
            }
        
        return None


# CLI TESTING
if __name__ == "__main__":
    print("🧪 TESTING CORRELATION & ANOMALY DETECTION\n")
    
    detector = CorrelationDetector()
    
    import random
    
    # Генерируем синтетические данные
    for i in range(100):
        btc_price = 50000 + random.gauss(0, 1000)
        eth_price = btc_price * 0.06 + random.gauss(0, 50)
        sol_price = 100 + random.gauss(0, 10)
        
        detector.add_price_data("BTC", btc_price)
        detector.add_price_data("ETH", eth_price)
        detector.add_price_data("SOL", sol_price)
    
    print("📊 Корреляции:")
    corr_btc_eth = detector.calculate_asset_correlation("BTC", "ETH")
    print(f"BTC-ETH correlation: {corr_btc_eth:.2f}")
    
    corr_btc_sol = detector.calculate_asset_correlation("BTC", "SOL")
    print(f"BTC-SOL correlation: {corr_btc_sol:.2f}")
    
    print("\n🔍 Коррелирующие активы для BTC:")
    correlated = detector.find_correlated_assets("BTC")
    for asset, corr in correlated:
        print(f"  {asset}: {corr:.2f}")
    
    # Тестируем координацию кошельков
    print("\n👥 Тестирование координации кошельков:")
    
    # Симулируем координированную покупку
    base_time = datetime.utcnow() - timedelta(minutes=30)
    for i in range(5):
        detector.add_wallet_action(
            f"0xwallet{i}",
            {
                "asset": "ETH",
                "type": "buy",
                "timestamp": base_time + timedelta(minutes=i*2),
                "amount_usd": 100000 + random.randint(-10000, 10000)
            }
        )
    
    coordinated = detector.find_coordinated_wallets()
    if coordinated:
        print(f"Найдено {len(coordinated)} координированных групп")
        for group in coordinated[:3]:
            print(f"  {group['wallet_count']} wallets - {group['asset']} - Score: {group['coordination_score']:.2f}")
    
    # Тестируем anomaly detection
    print("\n🚨 Тестирование anomaly detection:")
    
    anomaly = AnomalyDetector(sensitivity=2.0)
    
    for i in range(50):
        anomaly.add_datapoint("volume", random.gauss(1000000, 100000))
    
    # Добавляем аномалию
    result = anomaly.detect_anomaly("volume", 2000000)
    print(f"Anomaly detected: {result['is_anomaly']}")
    print(f"Severity: {result['severity']:.1%}")
    print(f"Z-score: {result['z_score']:.2f}")
    print(f"Type: {result['anomaly_type']}")
    
    print("\n✅ Testing complete!")