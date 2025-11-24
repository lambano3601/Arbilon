"""
Main entry point for the Telegram Arbitrage Bot.
"""
import os
import asyncio
from dotenv import load_dotenv
from utils.logger import setup_logger
from engine.exchange_manager import ExchangeManager
from engine.fee_manager import FeeManager
from engine.opportunity_detector import OpportunityDetector
from bot.telegram_bot import ArbitrageBot
import json
from config import CONFIG_FILE, DATA_DIR

# Load environment variables
load_dotenv()

# Setup logging
logger = setup_logger()


async def initialize():
    """Initialize data directory and config files."""
    # Create data directory
    DATA_DIR.mkdir(exist_ok=True)
    
    # Check environment variables
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    encryption_key = os.getenv("ENCRYPTION_KEY")
    
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not set in .env file")
        return None, None, None, None, None
    
    if not encryption_key:
        logger.error("ENCRYPTION_KEY not set in .env file")
        logger.info("Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
        return None, None, None, None, None
    
    # Load config
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
    else:
        logger.warning("Config file not found, using defaults")
        from config import DEFAULT_CONFIG
        config = DEFAULT_CONFIG
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    
    logger.info("Configuration loaded")
    
    # Initialize managers
    exchange_manager = ExchangeManager()
    fee_manager = FeeManager(exchange_manager)
    await fee_manager.load_cache()
    
    # Initialize risk manager
    from engine.risk_manager import RiskManager
    risk_manager = RiskManager()
    logger.info("Risk manager initialized")
    
    # Initialize position tracker
    from engine.position_tracker import PositionTracker
    position_tracker = PositionTracker(exchange_manager)
    
    # Load existing positions or initialize
    await position_tracker.load_positions()
    if not position_tracker.initial_balances:
        logger.info("No existing positions found, will initialize on first exchange connection")
    else:
        logger.info("Position tracker loaded")
    
    opportunity_detector = OpportunityDetector(exchange_manager, fee_manager, config)
    
    # Initialize bot
    bot = ArbitrageBot(bot_token, exchange_manager, opportunity_detector)
    
    logger.info("Bot initialized")
    
    return bot, exchange_manager, config, risk_manager, position_tracker


def main():
    """Main function."""
    logger.info("=" * 60)
    logger.info("Telegram Arbitrage Trading Bot")
    logger.info("=" * 60)
    
    try:
        # Initialize
        result = asyncio.run(initialize())
        
        if not result or result[0] is None:
            logger.error("Failed to initialize bot")
            return
        
        bot, exchange_manager, config, risk_manager, position_tracker = result
        
        logger.info("")
        logger.info("Quick Start:")
        logger.info("   1. Send /start to your bot on Telegram")
        logger.info("   2. Use /addexchange to add your exchange accounts")
        logger.info("   3. Use /setpairs to configure trading pairs")
        logger.info("   4. Use /setconfig to set trade amount")
        logger.info("   5. Use /scan to find opportunities")
        logger.info("")
        
        logger.info("Configuration:")
        logger.info(f"   Trade Amount: ${config.get('trading_config', {}).get('trade_amount_usdt', 100):.2f}")
        logger.info(f"   Trading Pairs: {len(config.get('trading_pairs', []))}")
        logger.info(f"   Min Profit: ${config.get('risk_limits', {}).get('min_profit_usd', 5):.2f}")
        logger.info(f"   Max Trade: ${config.get('risk_limits', {}).get('max_position_size_usd', 500):.2f}")
        logger.info("")
        
        logger.info("Starting bot... (Press Ctrl+C to stop)")
        logger.info("=" * 60)
        logger.info("")
        
        # Run bot
        bot.run()
        
    except KeyboardInterrupt:
        print("\n")  # New line
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        # Cleanup
        if 'exchange_manager' in locals() and exchange_manager:
            try:
                asyncio.run(exchange_manager.close_all())
            except:
                pass
        logger.info("Goodbye!")


if __name__ == "__main__":
    main()
