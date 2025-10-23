# app/whales/score.py
from typing import List, Tuple
from app.whales.normalize import WhaleEvent
from datetime import datetime, timedelta

class EventScorer:
    """Оценка значимости событий: фазы, direction, confidence, verdict"""
    
    def detect_phase(self, events: List[WhaleEvent]) -> List[WhaleEvent]:
        """Определяет фазу для каждого события на основе кластеризации"""
        
        # Группируем события по активу и временному окну (90 минут)
        clusters = {}
        
        for event in events:
            key = (event.asset, event.chain)
            if key not in clusters:
                clusters[key] = []
            clusters[key].append(event)
        
        # Анализируем каждый кластер
        for key, cluster_events in clusters.items():
            # Сортируем по времени
            cluster_events.sort(key=lambda e: e.tx_time_utc)
            
            for i, event in enumerate(cluster_events):
                # Проверяем, есть ли другие события в окне 90 минут
                window_start = event.tx_time_utc - timedelta(minutes=90)
                window_end = event.tx_time_utc + timedelta(minutes=90)
                
                related_txs = []
                for other in cluster_events:
                    if other.tx_hash != event.tx_hash and window_start <= other.tx_time_utc <= window_end:
                        related_txs.append(other.tx_hash)
                
                # Определяем фазу
                if len(related_txs) >= 1:
                    event.phase = "transfer_cluster"
                    from app.whales.normalize import ClusterInfo
                    event.cluster = ClusterInfo(
                        tx_in_window=len(related_txs) + 1,
                        window_minutes=90,
                        related_txs=related_txs
                    )
                elif event.direction == "inflow_to_exchange":
                    # Проверяем, идёт ли на горячий кошелёк
                    to_labels = event.labels.get("to", [])
                    is_hot_wallet = any(l.name == "exchange" and l.confidence >= 70 for l in to_labels)
                    
                    if is_hot_wallet:
                        event.phase = "deposit_confirmed"
                    else:
                        event.phase = "activation"
                else:
                    event.phase = "activation"
        
        return events
    
    def calculate_verdict_and_confidence(self, event: WhaleEvent) -> Tuple[str, int]:
        """
        Рассчитывает verdict (bullish/neutral/bearish) и confidence (0-100)
        """
        
        # Базовый verdict от направления
        if event.direction == "inflow_to_exchange":
            verdict = "bearish"
        elif event.direction == "outflow_to_cold":
            verdict = "bullish"
        else:
            verdict = "neutral"
        
        # Базовая confidence от size_rel
        size_rel = self._get_size_rel(event)
        
        if size_rel < 0.10:
            base_confidence = 0  # не публикуем
        elif size_rel < 0.50:
            base_confidence = 30  # слабый
        elif size_rel < 1.00:
            base_confidence = 60  # средний
        else:
            base_confidence = 80  # сильный
        
        confidence = base_confidence
        
        # Модификаторы
        # +10 за кластер
        if event.cluster and event.cluster.tx_in_window >= 2:
            confidence += 10
        
        # +10 за хорошие метки (биржа/фонд с confidence ≥70)
        has_good_labels = False
        for label_list in event.labels.values():
            for label in label_list:
                if label.name in ["exchange", "fund", "custodian"] and label.confidence >= 70:
                    has_good_labels = True
                    break
        
        if has_good_labels:
            confidence += 10
        
        # Cap для internal/bridge/unknown
        if event.is_internal or event.is_bridge or event.direction == "unknown":
            confidence = min(confidence, 50)
            verdict = "neutral"
        
        # Финальный cap
        confidence = min(100, max(0, confidence))
        
        return verdict, confidence
    
    def _get_size_rel(self, event: WhaleEvent) -> float:
        """Рассчитывает size_rel в процентах"""
        if not event.market.volume_24h_usd or event.market.volume_24h_usd == 0:
            return 0.0
        
        return (event.amount_usd / event.market.volume_24h_usd) * 100
    
    def should_publish(self, event: WhaleEvent, verdict: str, confidence: int) -> bool:
        """Определяет, нужно ли публиковать событие"""
        
        size_rel = self._get_size_rel(event)
        
        # Отбраковка по size_rel
        if size_rel < 0.10:
            return False
        
        # Отбраковка по отсутствию данных
        if not event.market.price or not event.market.volume_24h_usd:
            return False
        
        # Отбраковка по confidence
        if confidence < 30:
            return False
        
        return True
    
    def calculate_priority(self, event: WhaleEvent, confidence: int) -> float:
        """Рассчитывает приоритет для очереди публикаций"""
        size_rel = self._get_size_rel(event)
        return confidence * size_rel