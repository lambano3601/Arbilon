"""
Configuration constants and defaults for the arbitrage bot.
"""
import os
from pathlib import Path

# Project paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

# Data files
API_KEYS_FILE = DATA_DIR / "api_keys.json"
POSITIONS_FILE = DATA_DIR / "positions.json"
TRADES_FILE = DATA_DIR / "trades.json"
FEES_CACHE_FILE = DATA_DIR / "fees_cache.json"
CONFIG_FILE = DATA_DIR / "config.json"

# Default configuration
DEFAULT_CONFIG = {
    "trading_config": {
        "trade_amount_usdt": 100.0,
        "enabled": False,
        "auto_execute": False,
        "require_manual_approval": True,
        "monitoring_interval_seconds": 5
    },
    "trading_pairs": [],
    "risk_limits": {
        "min_spread_percent_gross": 0.5,
        "min_spread_percent_net": 0.3,
        "min_profit_usd": 5.0,
        "max_position_size_usd": 500.0,
        "max_inventory_drift_percent": 15.0,
        "max_per_exchange_drift_percent": 20.0,
        "slippage_buffer_percent": 0.2,
        "max_fee_impact_percent": 50.0,
        "max_concurrent_trades": 3,
        "max_opportunity_age_seconds": 10
    }
}


# Supported exchanges
SUPPORTED_EXCHANGES = ["binance", "okx", "kucoin", "bybit", "gate", "mexc"]

# Logging
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
