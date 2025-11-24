"""
Fee manager for fetching and caching trading fees.
"""
import logging
import json
import aiofiles
from pathlib import Path
from datetime import datetime, timedelta
from config import FEES_CACHE_FILE

logger = logging.getLogger(__name__)


class FeeManager:
    """Manages trading fee fetching and caching."""
    
    def __init__(self, exchange_manager):
        self.exchange_manager = exchange_manager
        self.cache = {}
        self.cache_duration = timedelta(hours=24)
    
    async def load_cache(self):
        """Load fee cache from file."""
        if FEES_CACHE_FILE.exists():
            try:
                async with aiofiles.open(FEES_CACHE_FILE, 'r') as f:
                    content = await f.read()
                    self.cache = json.loads(content)
                logger.info("Fee cache loaded")
            except Exception as e:
                logger.error(f"Error loading fee cache: {e}")
    
    async def save_cache(self):
        """Save fee cache to file."""
        try:
            async with aiofiles.open(FEES_CACHE_FILE, 'w') as f:
                await f.write(json.dumps(self.cache, indent=2))
        except Exception as e:
            logger.error(f"Error saving fee cache: {e}")
    
    async def get_trading_fees(self, exchange_name: str, symbol: str) -> dict:
        """
        Get trading fees for a symbol on an exchange.
        
        Returns:
            dict: {'maker': 0.1, 'taker': 0.1} (in percentage)
        """
        cache_key = f"{exchange_name}:{symbol}"
        
        # Check cache
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            cache_time = datetime.fromisoformat(cached['timestamp'])
            if datetime.now() - cache_time < self.cache_duration:
                return cached['fees']
        
        # Fetch from exchange
        try:
            exchange = self.exchange_manager.get_exchange(exchange_name)
            if not exchange:
                raise ValueError(f"Exchange {exchange_name} not initialized")
            
            # Load markets if not loaded
            if not exchange.markets:
                await exchange.load_markets()
             
            # Get fee structure
            if symbol in exchange.markets:
                market = exchange.markets[symbol]
                maker_fee = market.get('maker', 0.001) * 100  # Convert to percentage
                taker_fee = market.get('taker', 0.001) * 100
            else:
                # Default fees if market not found
                maker_fee = 0.1
                taker_fee = 0.1
            
            fees = {'maker': maker_fee, 'taker': taker_fee}
            
            # Cache result
            self.cache[cache_key] = {
                'fees': fees,
                'timestamp': datetime.now().isoformat()
            }
            await self.save_cache()
            
            return fees
            
        except Exception as e:
            logger.error(f"Error fetching fees for {exchange_name} {symbol}: {e}")
            # Return default fees
            return {'maker': 0.1, 'taker': 0.1}
    
    async def get_maker_fee(self, exchange_name: str, symbol: str = "BTC/USDT") -> float:
        """Get maker fee percentage."""
        fees = await self.get_trading_fees(exchange_name, symbol)
        return fees['maker']
    
    async def get_taker_fee(self, exchange_name: str, symbol: str = "BTC/USDT") -> float:
        """Get taker fee percentage."""
        fees = await self.get_trading_fees(exchange_name, symbol)
        return fees['taker']
