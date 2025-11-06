# app/whales/publisher/utils.py
"""
Publisher Utilities
"""

import re


class PublisherUtils:
    """Утилиты publisher"""
    
    @staticmethod
    def strip_html(text: str) -> str:
        """Удаляет HTML теги"""
        
        text = re.sub(r'<[^>]+>', '', text)
        
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        
        return text
    
    @staticmethod
    def truncate_message(message: str, max_length: int) -> str:
        """Сокращает сообщение до заданной длины"""
        
        if len(message) <= max_length:
            return message
        
        truncated = message[:max_length - 50]
        
        last_newline = truncated.rfind('\n')
        if last_newline > 0:
            truncated = truncated[:last_newline]
        
        truncated += "\n\n<i>... (сообщение сокращено)</i>"
        
        return truncated


__all__ = ['PublisherUtils']