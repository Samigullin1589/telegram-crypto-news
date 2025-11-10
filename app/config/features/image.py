"""
Image configuration module
Настройки обработки изображений
"""

import logging
from typing import Dict, Any
from .base import BaseFeatureConfig

logger = logging.getLogger(__name__)


class ImageConfig(BaseFeatureConfig):
    """
    Конфигурация обработки изображений
    
    Управляет:
    - Размерами изображений
    - Качеством и сжатием
    - Проверками валидности
    - Форматами и конвертацией
    """
    
    def __init__(self):
        """Инициализация конфигурации изображений"""
        
        # Минимальные размеры
        self.min_image_width = self.get_int_env('MIN_IMAGE_WIDTH', 400)
        self.min_image_height = self.get_int_env('MIN_IMAGE_HEIGHT', 200)
        
        # Максимальные размеры
        self.max_image_width = self.get_int_env('MAX_IMAGE_WIDTH', 2000)
        self.max_image_height = self.get_int_env('MAX_IMAGE_HEIGHT', 2000)
        self.max_image_size_mb = self.get_int_env('MAX_IMAGE_SIZE_MB', 10)
        self.max_image_size_bytes = self.max_image_size_mb * 1024 * 1024
        
        # Качество и сжатие
        self.image_quality = self.get_int_env('IMAGE_QUALITY', 85)
        self.image_compression_enabled = self.get_bool_env('IMAGE_COMPRESSION_ENABLED', True)
        self.image_optimization_level = self.get_int_env('IMAGE_OPTIMIZATION_LEVEL', 2)
        self.preserve_aspect_ratio = self.get_bool_env('PRESERVE_ASPECT_RATIO', True)
        
        # Форматы
        self.allowed_formats = self._parse_allowed_formats()
        self.default_format = self.get_str_env('IMAGE_DEFAULT_FORMAT', 'JPEG')
        self.convert_to_rgb = self.get_bool_env('CONVERT_TO_RGB', True)
        
        # Проверки
        self.image_validation_enabled = self.get_bool_env('IMAGE_VALIDATION_ENABLED', True)
        self.check_image_corruption = self.get_bool_env('CHECK_IMAGE_CORRUPTION', True)
        self.image_check_timeout = self.get_int_env('IMAGE_CHECK_TIMEOUT', 10)
        self.image_partial_read_bytes = self.get_int_env('IMAGE_PARTIAL_READ_BYTES', 8192)
        
        # Кэширование
        self.cache_images = self.get_bool_env('CACHE_IMAGES', True)
        self.cache_ttl_seconds = self.get_int_env('CACHE_TTL_SECONDS', 3600)
        self.max_cached_images = self.get_int_env('MAX_CACHED_IMAGES', 100)
        
        # Watermark (если нужен)
        self.add_watermark = self.get_bool_env('ADD_WATERMARK', False)
        self.watermark_text = self.get_str_env('WATERMARK_TEXT', '')
        self.watermark_opacity = self.get_int_env('WATERMARK_OPACITY', 30)
        
        # Логирование
        self._log_configuration()
    
    def _parse_allowed_formats(self) -> list:
        """Парсинг разрешенных форматов изображений"""
        formats_str = self.get_str_env('ALLOWED_IMAGE_FORMATS', 'JPEG,PNG,WEBP,GIF')
        return [fmt.strip().upper() for fmt in formats_str.split(',')]
    
    def _log_configuration(self):
        """Логирование конфигурации"""
        logger.debug(f"[IMAGE] Size limits: min={self.min_image_width}x{self.min_image_height}, "
                    f"max={self.max_image_width}x{self.max_image_height}, "
                    f"max_size={self.max_image_size_mb}MB")
        logger.debug(f"[IMAGE] Quality: {self.image_quality}, compression={'enabled' if self.image_compression_enabled else 'disabled'}")
        logger.debug(f"[IMAGE] Allowed formats: {', '.join(self.allowed_formats)}")
    
    def validate_size(self, width: int, height: int) -> bool:
        """
        Проверка размеров изображения
        
        Args:
            width: Ширина
            height: Высота
            
        Returns:
            bool: True если размеры валидны
        """
        return (self.min_image_width <= width <= self.max_image_width and
                self.min_image_height <= height <= self.max_image_height)
    
    def validate_file_size(self, size_bytes: int) -> bool:
        """
        Проверка размера файла
        
        Args:
            size_bytes: Размер в байтах
            
        Returns:
            bool: True если размер валиден
        """
        return 0 < size_bytes <= self.max_image_size_bytes
    
    def validate_format(self, format_name: str) -> bool:
        """
        Проверка формата изображения
        
        Args:
            format_name: Название формата
            
        Returns:
            bool: True если формат разрешен
        """
        return format_name.upper() in self.allowed_formats
    
    def get_compression_settings(self) -> Dict[str, Any]:
        """
        Получение настроек сжатия
        
        Returns:
            Dict: Настройки сжатия для PIL/Pillow
        """
        return {
            'quality': self.image_quality,
            'optimize': self.image_compression_enabled,
            'progressive': True,
            'subsampling': 0 if self.image_quality >= 90 else 2
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Конвертация в словарь
        
        Returns:
            Dict: Конфигурация изображений
        """
        return {
            'min_width': self.min_image_width,
            'min_height': self.min_image_height,
            'max_width': self.max_image_width,
            'max_height': self.max_image_height,
            'max_size_mb': self.max_image_size_mb,
            'quality': self.image_quality,
            'compression_enabled': self.image_compression_enabled,
            'optimization_level': self.image_optimization_level,
            'allowed_formats': self.allowed_formats,
            'default_format': self.default_format,
            'validation_enabled': self.image_validation_enabled,
            'check_timeout': self.image_check_timeout,
            'cache_enabled': self.cache_images,
            'cache_ttl': self.cache_ttl_seconds
        }


__all__ = ['ImageConfig']