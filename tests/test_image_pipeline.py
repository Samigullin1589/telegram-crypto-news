import asyncio
import io
import os
from unittest.mock import AsyncMock

os.environ.setdefault(
    'TELEGRAM_BOT_TOKEN',
    '123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi',
)
os.environ.setdefault('TELEGRAM_CHANNEL_ID', '-1001234567890')

from bs4 import BeautifulSoup
from PIL import Image

from bot.content_parser import ContentParser, ImageExtractor, ImageURLProcessor
from bot.telegram_poster import MessageSanitizer, PostingMetrics, TelegramPoster


def test_rss_images_are_extracted_from_normalized_dict_entries():
    extractor = ImageExtractor()
    entry = {
        'media_content': [
            {'url': 'https://cdn.example.com/article.jpg'},
        ],
        'enclosures': [
            {
                'type': 'image/webp',
                'href': 'https://cdn.example.com/article.webp',
            }
        ],
    }

    candidates = extractor._extract_from_rss(entry, 'https://example.com/news')

    assert candidates == [
        'https://cdn.example.com/article.jpg',
        'https://cdn.example.com/article.webp',
    ]


def test_largest_srcset_candidate_is_preferred():
    extractor = ImageExtractor()
    soup = BeautifulSoup(
        '<article><img src="fallback.jpg" '
        'srcset="small.jpg 320w, large.jpg 1280w"></article>',
        'html.parser',
    )

    candidates = extractor.extract_candidates(
        soup,
        {},
        'https://example.com/news',
    )

    assert candidates[0][0] == 'https://example.com/large.jpg'


def test_unknown_cdn_signed_query_is_not_removed():
    url = 'https://media.example.com/image.jpg?w=1200&token=signature'

    assert ImageURLProcessor.extract_full_size_url(url) == url


def test_known_cdn_signed_query_is_not_rewritten():
    url = 'https://images.unsplash.com/photo.jpg?w=640&token=signature'

    assert ImageURLProcessor.extract_full_size_url(url) == url


def test_image_is_normalized_to_telegram_compatible_jpeg():
    from bot.telegram_poster import ImageDownloader

    source = io.BytesIO()
    Image.new('RGBA', (600, 400), (255, 0, 0, 128)).save(
        source,
        format='PNG',
    )
    downloader = ImageDownloader()

    prepared, width, height = downloader._prepare_for_telegram(source.getvalue())

    with Image.open(io.BytesIO(prepared)) as result:
        assert result.format == 'JPEG'
        assert result.mode == 'RGB'
        assert result.size == (width, height) == (600, 400)


def test_image_validation_reads_all_short_network_chunks():
    class Content:
        async def iter_chunked(self, size):
            del size
            for chunk in (b'first-', b'second-', b'third'):
                yield chunk

    response = type('Response', (), {'content': Content()})()

    result = asyncio.run(
        ContentParser._read_limited_response(response, max_bytes=100)
    )

    assert result == b'first-second-third'


def test_image_validation_rejects_body_over_limit():
    class Content:
        async def iter_chunked(self, size):
            del size
            yield b'12345'
            yield b'67890'

    response = type('Response', (), {'content': Content()})()

    result = asyncio.run(
        ContentParser._read_limited_response(response, max_bytes=9)
    )

    assert result is None


def test_photo_plain_fallback_runs_before_text_only():
    poster = TelegramPoster.__new__(TelegramPoster)
    poster._initialized = True
    poster.channel_id = '-1001234567890'
    poster.metrics = PostingMetrics()
    poster.sanitizer = MessageSanitizer()
    poster._rate_limit = AsyncMock()
    poster._post_with_markdown_and_image = AsyncMock(return_value=False)
    poster._post_plain_with_image = AsyncMock(return_value=True)
    poster._post_with_markdown_text_only = AsyncMock(return_value=True)
    poster._post_plain_text_only = AsyncMock(return_value=True)

    result = asyncio.run(
        poster.post(
            message='📰 **Тестовая новость**\n\nПодробный русский текст.',
            link='https://example.com/news',
            image_data=b'image-bytes',
        )
    )

    assert result is True
    poster._post_with_markdown_and_image.assert_awaited_once()
    poster._post_plain_with_image.assert_awaited_once()
    poster._post_with_markdown_text_only.assert_not_awaited()
    assert poster.metrics.strategies_used['plain_with_image'] == 1
    assert poster.metrics.posts_with_images == 1
    assert poster.metrics.posts_without_images == 0


def test_required_image_never_falls_back_to_text_only():
    poster = TelegramPoster.__new__(TelegramPoster)
    poster._initialized = True
    poster.channel_id = '-1001234567890'
    poster.metrics = PostingMetrics()
    poster.sanitizer = MessageSanitizer()
    poster._rate_limit = AsyncMock()
    poster._post_with_markdown_and_image = AsyncMock(return_value=False)
    poster._post_plain_with_image = AsyncMock(return_value=False)
    poster._post_with_markdown_text_only = AsyncMock(return_value=True)
    poster._post_plain_text_only = AsyncMock(return_value=True)

    result = asyncio.run(
        poster.post(
            message='📰 **Тестовая новость**\n\nПодробный русский текст.',
            link='https://example.com/news',
            image_data=b'image-bytes',
            require_image=True,
        )
    )

    assert result is False
    poster._post_with_markdown_and_image.assert_awaited_once()
    poster._post_plain_with_image.assert_awaited_once()
    poster._post_with_markdown_text_only.assert_not_awaited()
    poster._post_plain_text_only.assert_not_awaited()
    assert poster.metrics.failed_posts == 1


def test_required_missing_image_cancels_publication():
    poster = TelegramPoster.__new__(TelegramPoster)
    poster._initialized = True
    poster.channel_id = '-1001234567890'
    poster.metrics = PostingMetrics()
    poster.sanitizer = MessageSanitizer()
    poster._rate_limit = AsyncMock()
    poster._post_with_markdown_text_only = AsyncMock(return_value=True)
    poster._post_plain_text_only = AsyncMock(return_value=True)

    result = asyncio.run(
        poster.post(
            message='📰 **Тестовая новость**\n\nПодробный русский текст.',
            link='https://example.com/news',
            require_image=True,
        )
    )

    assert result is False
    poster._post_with_markdown_text_only.assert_not_awaited()
    poster._post_plain_text_only.assert_not_awaited()
    assert poster.metrics.failed_posts == 1