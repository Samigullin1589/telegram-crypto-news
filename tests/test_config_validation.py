from types import SimpleNamespace

from app.config.validators.api_validator import APIValidator


def test_missing_ai_provider_allows_raw_news_fallback():
    config = SimpleNamespace(
        api=SimpleNamespace(has_ai_provider=lambda: False),
    )
    validator = APIValidator(config)

    validator._validate_ai_providers()

    assert validator.errors == []
    assert len(validator.warnings) == 1
    assert 'Новости будут публиковаться в сыром виде' in validator.warnings[0]