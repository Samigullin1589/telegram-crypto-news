# app/whales/discovery/storage.py
"""
Persistence layer для watchlist
"""

import json
import os
from typing import Dict, Set
from datetime import datetime
from collections import defaultdict

from app.whales.discovery.models import TokenData, DiscoveryStats


class WatchlistStorage:
    """Управление хранением watchlist"""
    
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self._ensure_storage_directory()
    
    def _ensure_storage_directory(self):
        """Создает директорию для хранения если не существует"""
        directory = os.path.dirname(self.storage_path)
        if directory and not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
                print(f'📁 [STORAGE] Создана директория: {directory}')
            except OSError as e:
                print(f'⚠️  [STORAGE] Не удалось создать директорию: {e}')
    
    def save(
        self,
        watchlist: Dict[str, Set[str]],
        metadata: Dict[str, TokenData],
        stats: DiscoveryStats
    ) -> bool:
        """
        Сохраняет watchlist и метаданные
        
        Returns:
            True если успешно, False если ошибка
        """
        try:
            data = {
                'watchlist': {
                    chain: list(tokens)
                    for chain, tokens in watchlist.items()
                },
                'metadata': {
                    key: token.to_dict()
                    for key, token in metadata.items()
                },
                'stats': stats.to_dict(),
                'version': '3.0',
                'updated_at': datetime.utcnow().isoformat()
            }
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f'💾 [STORAGE] Сохранено ({stats.total_discovered} токенов)')
            return True
        
        except IOError as e:
            print(f'⚠️  [STORAGE] Ошибка записи: {e}')
            return False
        
        except Exception as e:
            print(f'⚠️  [STORAGE] Неожиданная ошибка при сохранении: {e}')
            return False
    
    def load(self) -> tuple[Dict[str, Set[str]], Dict[str, TokenData], DiscoveryStats]:
        """
        Загружает watchlist и метаданные
        
        Returns:
            (watchlist, metadata, stats)
        """
        if not os.path.exists(self.storage_path):
            print(f'📂 [STORAGE] Файл не найден, создается новый watchlist')
            return defaultdict(set), {}, DiscoveryStats()
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            watchlist = self._load_watchlist(data)
            metadata = self._load_metadata(data)
            stats = self._load_stats(data)
            
            print(f'📂 [STORAGE] Загружено ({stats.total_discovered} токенов)')
            return watchlist, metadata, stats
        
        except json.JSONDecodeError as e:
            print(f'⚠️  [STORAGE] Ошибка парсинга JSON: {e}')
            return defaultdict(set), {}, DiscoveryStats()
        
        except Exception as e:
            print(f'⚠️  [STORAGE] Ошибка загрузки: {e}')
            return defaultdict(set), {}, DiscoveryStats()
    
    def _load_watchlist(self, data: Dict) -> Dict[str, Set[str]]:
        """Загружает watchlist из данных"""
        watchlist = defaultdict(set)
        
        for chain, tokens in data.get('watchlist', {}).items():
            watchlist[chain] = set(tokens)
        
        return watchlist
    
    def _load_metadata(self, data: Dict) -> Dict[str, TokenData]:
        """Загружает метаданные токенов"""
        metadata = {}
        
        for key, token_dict in data.get('metadata', {}).items():
            try:
                metadata[key] = TokenData.from_dict(token_dict)
            except Exception as e:
                print(f'⚠️  [STORAGE] Ошибка загрузки метаданных {key}: {e}')
        
        return metadata
    
    def _load_stats(self, data: Dict) -> DiscoveryStats:
        """Загружает статистику"""
        stats_data = data.get('stats', {})
        
        try:
            return DiscoveryStats.from_dict(stats_data)
        except Exception as e:
            print(f'⚠️  [STORAGE] Ошибка загрузки статистики: {e}')
            return DiscoveryStats()