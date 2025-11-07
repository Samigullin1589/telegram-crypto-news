# app/whales/history/storage.py
"""
Event Storage System
"""

import json
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime, timedelta


class EventStorage:
    """Файловое хранилище событий"""
    
    def __init__(self, history_dir: Path):
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)
    
    def save_event(
        self,
        asset: str,
        event_data: Dict
    ) -> bool:
        """
        Сохраняет событие в файл
        
        Args:
            asset: Символ актива (BTC, ETH, etc)
            event_data: Данные события
        
        Returns:
            True если успешно сохранено
        """
        try:
            history_file = self.history_dir / f"{asset}.jsonl"
            
            with open(history_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event_data) + "\n")
            
            return True
        
        except Exception as e:
            print(f"⚠️  [STORAGE] Не удалось сохранить {asset}: {e}")
            return False
    
    def load_recent_events(
        self,
        asset: str,
        days: int = 30
    ) -> List[Dict]:
        """
        Загружает недавние события для актива
        
        Args:
            asset: Символ актива
            days: Сколько дней назад искать
        
        Returns:
            List событий
        """
        try:
            history_file = self.history_dir / f"{asset}.jsonl"
            
            if not history_file.exists():
                return []
            
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            events = []
            
            with open(history_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        entry_ts = datetime.fromisoformat(entry["ts"])
                        
                        if entry_ts >= cutoff:
                            events.append(entry)
                    
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
            
            return events
        
        except FileNotFoundError:
            return []
        
        except Exception as e:
            print(f"⚠️  [STORAGE] Ошибка загрузки {asset}: {e}")
            return []
    
    def find_similar_events(
        self,
        events: List[Dict],
        direction: str,
        size_bucket: str,
        phase: str
    ) -> List[Dict]:
        """
        Находит похожие события
        
        Args:
            events: List всех событий
            direction: Направление перевода
            size_bucket: Размерная категория
            phase: Фаза события
        
        Returns:
            List похожих событий
        """
        candidates = []
        
        for entry in events:
            try:
                if (entry.get("direction") == direction and
                    entry.get("size_bucket") == size_bucket and
                    entry.get("phase") in [phase, "activation"]):
                    
                    candidates.append(entry)
            
            except KeyError:
                continue
        
        candidates.sort(key=lambda x: x["ts"], reverse=True)
        
        return candidates