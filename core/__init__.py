"""
Core module for Integrated Crypto Monitor v4.5

Production-grade core components:
- ChainRateLimiter: Adaptive rate limiting for blockchain RPC endpoints
- ResourceMonitor: System resource monitoring and management
- SystemHealthMonitor: Health tracking for all subsystems
- HTTPServer: Health check and webhook HTTP server
"""

__version__ = '4.5.0'
__author__ = 'Crypto Compass Team'

from .rate_limiter import ChainRateLimiter
from .resource_monitor import ResourceMonitor
from .health_monitor import SystemHealthMonitor
from .http_server import HTTPServer

__all__ = [
    'ChainRateLimiter',
    'ResourceMonitor',
    'SystemHealthMonitor',
    'HTTPServer',
]