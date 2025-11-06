# app/config/printer.py
"""
Configuration summary printer
"""

from typing import Dict, List, Any


class ConfigPrinter:
    """Вывод summary конфигурации"""
    
    @staticmethod
    def print_summary(config_data: Dict[str, Any]):
        """Выводит summary конфигурации"""
        print('\n' + '=' * 80)
        print('⚙️  КОНФИГУРАЦИЯ ЗАГРУЖЕНА')
        print('=' * 80)
        
        ConfigPrinter._print_telegram(config_data['telegram'])
        ConfigPrinter._print_production(config_data['production'])
        ConfigPrinter._print_chains(config_data['chains'])
        ConfigPrinter._print_whale(config_data['whale'])
        
        if config_data.get('news_enabled'):
            ConfigPrinter._print_news(config_data['news'])
        
        if config_data.get('trading_enabled'):
            ConfigPrinter._print_trading(config_data['trading'])
        
        if config_data.get('hyperliquid_enabled'):
            ConfigPrinter._print_hyperliquid(config_data['hyperliquid'])
        
        if config_data.get('discovery_enabled'):
            ConfigPrinter._print_discovery(config_data['discovery'])
        
        ConfigPrinter._print_features(config_data['features'])
        ConfigPrinter._print_rate_limiting(config_data['rate_limit'])
        ConfigPrinter._print_storage(config_data['storage'])
        ConfigPrinter._print_api_keys(config_data['api_keys'])
        
        print('\n' + '=' * 80 + '\n')
    
    @staticmethod
    def _print_telegram(telegram: Dict):
        """Выводит Telegram конфигурацию"""
        print(f'\n📱 TELEGRAM:')
        token = telegram['token']
        print(f'   Bot: {token[:10]}...{token[-4:]}')
        print(f'   Channel: {telegram["channel_id"]}')
        print(f'   Admin: {telegram["admin_chat_id"]}')
    
    @staticmethod
    def _print_production(production: Dict):
        """Выводит Production конфигурацию"""
        print(f'\n🌐 PRODUCTION:')
        print(f'   Port: {production["port"]}')
        print(f'   Memory Limit: {production["max_memory_mb"]}MB')
        print(f'   HTTP Timeout: {production["http_timeout"]}s')
        print(f'   GC Interval: {production["gc_interval_seconds"]}s')
    
    @staticmethod
    def _print_chains(chains: Dict):
        """Выводит Chains конфигурацию"""
        enabled = chains['enabled_chains']
        print(f'\n⛓️  CHAINS ({len(enabled)}):')
        print(f'   {", ".join(enabled)}')
    
    @staticmethod
    def _print_whale(whale: Dict):
        """Выводит Whale конфигурацию"""
        print(f'\n🐋 WHALE DETECTION:')
        print(f'   Min USD: ${whale["min_usd_threshold"]:,.0f}')
        print(f'   Min Confidence: {whale["min_confidence_score"]}')
        print(f'   Posts/Hour Cap: {whale["posts_per_hour_cap"]}')
    
    @staticmethod
    def _print_news(news: Dict):
        """Выводит News конфигурацию"""
        print(f'\n📰 NEWS BOT:')
        print(f'   Sources: {news["sources_count"]}')
        print(f'   Fetch Interval: {news["fetch_interval"]}s')
        print(f'   AI Provider: {news["ai_provider"] if news["ai_enabled"] else "disabled"}')
    
    @staticmethod
    def _print_trading(trading: Dict):
        """Выводит Trading конфигурацию"""
        print(f'\n📈 TRADING:')
        print(f'   Assets: {trading["assets_count"]}')
        print(f'   Signal Interval: {trading["signal_interval_hours"]}h')
    
    @staticmethod
    def _print_hyperliquid(hyperliquid: Dict):
        """Выводит Hyperliquid конфигурацию"""
        print(f'\n💹 HYPERLIQUID:')
        print(f'   Min Trade: ${hyperliquid["min_trade_usd"]:,.0f}')
        print(f'   Min Liquidation: ${hyperliquid["min_liquidation_usd"]:,.0f}')
    
    @staticmethod
    def _print_discovery(discovery: Dict):
        """Выводит Discovery конфигурацию"""
        print(f'\n🔍 TOKEN DISCOVERY:')
        print(f'   Tokens per Chain: {discovery["top_n_per_chain"]}')
        print(f'   Min Age: {discovery["min_token_age_days"]} days')
        print(f'   Min Volume: ${discovery["min_volume_usd"]:,.0f}')
        print(f'   Min Market Cap: ${discovery["min_market_cap_usd"]:,.0f}')
        print(f'   Blacklist Size: {discovery["blacklist_size"]}')
    
    @staticmethod
    def _print_features(features: Dict):
        """Выводит Features конфигурацию"""
        print(f'\n✨ FEATURES:')
        enabled = [name for name, status in features.items() if status]
        disabled = [name for name, status in features.items() if not status]
        print(f'   Enabled: {", ".join(enabled)}')
        if disabled:
            print(f'   Disabled: {", ".join(disabled)}')
    
    @staticmethod
    def _print_rate_limiting(rate_limit: Dict):
        """Выводит Rate Limiting конфигурацию"""
        print(f'\n📊 RATE LIMITING:')
        print(f'   General: {rate_limit["calls_per_minute"]}/min')
        print(f'   Solana: {rate_limit["solana_requests"]}/{rate_limit["solana_window_seconds"]}s')
    
    @staticmethod
    def _print_storage(storage: Dict):
        """Выводит Storage конфигурацию"""
        print(f'\n💾 STORAGE:')
        print(f'   Data Dir: {storage["data_dir"]}')
        print(f'   Database: {storage["database_type"]}')
    
    @staticmethod
    def _print_api_keys(api_keys: List[str]):
        """Выводит API Keys конфигурацию"""
        if api_keys:
            print(f'\n🔑 API KEYS:')
            print(f'   {", ".join(api_keys)}')