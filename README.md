# Telegram Arbitrage Trading Bot

A Telegram-based cryptocurrency arbitrage bot that monitors multiple exchanges for price differences and executes profitable trades with equal USD amounts.

## ✨ Key Features

- **Manual Pair Entry**: Type trading pairs directly (BTC/USDT, SOL/USDT format)
- **Equal Trade Amounts**: Set USD amount → buys $X worth of crypto, sells $X worth
- **Live Fee Tracking**: Fetches current fees from exchange APIs in real-time
- **Pre-Execution Validation**: ✅ **MANDATORY balance and profitability checks before EVERY trade**
- **Detailed Error Messages**: Clear alerts for insufficient funds or unprofitable trades
- **Full Telegram Control**: All configuration and monitoring via Telegram commands

## 🛡️ Pre-Execution Validation

**CRITICAL**: Before executing ANY trade, the bot performs:

1. **Profitability Check**: Trade MUST have net profit > $0
2. **USDT Balance Check**: Verifies sufficient USDT on buy exchange
3. **Token Balance Check**: Verifies sufficient tokens on sell exchange
4. **Price Re-verification**: Rechecks prices haven't moved unfavorably

**All validation failures generate detailed error messages sent via Telegram.**

## 📋 Prerequisites

- Python 3.9+
- Telegram Bot Token (get from @BotFather)
- Exchange API keys (with trading permissions)

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or navigate to project directory
cd arbitrage_bot

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
copy .env.example .env

# Edit .env and set:
# - TELEGRAM_BOT_TOKEN (from @BotFather)
# - ENCRYPTION_KEY (generate with command below)
```

Generate encryption key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3. Run the Bot

```bash
python main.py
```

### 4. Telegram Setup

1. Open Telegram and start a chat with your bot
2. Send `/start` to see available commands
3. Use `/addexchange` to add exchange accounts
4. Use `/setpairs` to configure trading pairs (e.g., BTC/USDT, SOL/USDT)
5. Use `/setconfig` to set trade amount
6. Use `/scan` to find opportunities

## 📱 Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Show welcome message and command list |
| `/addexchange` | Add exchange account (API keys) |
| `/setpairs` | Set trading pairs (BTC/USDT, SOL/USDT, etc.) |
| `/setconfig` | Configure trade amount in USD |
| `/balance` | Check balances on all exchanges |
| `/scan` | Scan for current arbitrage opportunities |
| `/monitor` | Start/stop continuous monitoring (TODO) |
| `/help` | Show all commands |

## 🔧 Configuration

Edit `data/config.json` to adjust:

- **trade_amount_usdt**: USD amount per trade (default: $100)
- **min_profit_usd**: Minimum profit threshold (default: $5)
- **min_spread_percent_gross**: Minimum price spread (default: 0.5%)

## 🎯 Supported Exchanges

- Binance
- OKX
- KuCoin
- Bybit
- Gate.io
- MEXC

## ⚠️ Important Notes

- **VPS Deployment**: You handle VPS setup yourself (not included)
- **Start with testnet**: Test with testnet/demo accounts first
- **Small amounts**: Start with small trade amounts ($10-50)
- **Balance requirements**: Ensure you have:
  - USDT on buy exchanges
  - Tokens (BTC, SOL, etc.) on sell exchanges
- **API permissions**: Trading permission required (NO withdrawal permission needed)

## 📊 How It Works

1. Bot monitors configured trading pairs across exchanges
2. Calculates profit with equal USD amounts (e.g., buy $100, sell $100)
3. When opportunity found:
   - ✅ Verifies trade is profitable (net profit > $0)
   - ✅ Checks USDT balance on buy exchange
   - ✅ Checks token balance on sell exchange
   - ✅ Re-verifies prices haven't moved
4. If ALL checks pass, executes trade
5. If ANY check fails, cancels with detailed error message

## 🔐 Security

- API keys encrypted with Fernet encryption
- Keys stored in `data/api_keys.json` (encrypted)
- Never share your `.env` file or encryption key

## 📂 Project Structure

```
arbitrage_bot/
├── main.py                     # Entry point
├── config.py                   # Configuration constants
├── requirements.txt            # Dependencies
├── .env                        # Environment variables (create from .env.example)
│
├── bot/
│   └── telegram_bot.py         # Main bot class with handlers
│
├── engine/
│   ├── exchange_manager.py     # CCXT exchange connections
│   ├── fee_manager.py          # Live fee fetching
│   ├── opportunity_detector.py # Spread detection
│   └── trade_executor.py       # Order placement with validation
│
├── utils/
│   ├── security.py             # API key encryption
│   ├── profit_calculator.py    # Profit calculations
│   └── logger.py               # Logging setup
│
└── data/
    ├── config.json             # Bot configuration
    ├── api_keys.json           # Encrypted exchange credentials
    ├── trades.json             # Trade history
    └── fees_cache.json         # Cached trading fees
```

## 🧪 Testing

Before live trading:

1. **Test with small amounts**: Start with $10-20 trades
2. **Verify balances**: Use `/balance` to check your exchange balances
3. **Test validation**: Try trading without sufficient funds to see error messages
4. **Check profitability**: Use `/scan` to see if opportunities are actually profitable

## 📝 License

MIT License - Use at your own risk. Cryptocurrency trading involves substantial risk of loss.

## ⚠️ Disclaimer

This software is for educational purposes. Cryptocurrency trading is risky. Always test thoroughly before using real funds. The authors are not responsible for any financial losses.
