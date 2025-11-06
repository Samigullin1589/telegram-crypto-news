# app/scheduler/__init__.py
"""
Integrated Scheduler v4.4
Modular architecture for whale monitoring, trading, and news integration
"""

from app.scheduler.core import IntegratedScheduler

# Create singleton instance
scheduler = IntegratedScheduler()

__all__ = ['IntegratedScheduler', 'scheduler']