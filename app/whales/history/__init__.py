# app/whales/history/__init__.py
"""
History Management System v2.0
Tracks whale events and calculates price deltas
"""

from app.whales.history.manager import HistoryManager

__all__ = ['HistoryManager']