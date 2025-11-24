"""
CCXT Exchange Manager - handles exchange connections and operations.
"""
import ccxt.async_support as ccxt
import logging
from typing import Dict, Optional
from utils.security import decrypt_api_key

logger = logging.getLogger(__name__)


class ExchangeManager:
    """Manages multiple exchange connections."""
    
    def __init__(self):
        self.exchanges: Dict[str, ccxt.Exchange] = {}
    
    async def add_exchange(
        self,
        exchange_name: str,
        api_key_encrypted: str,
        secret_encrypted: str,
        passphrase_encrypted: Optional[str] = None,
        testnet: bool = False
    ) -> tuple[bool, str]:
        """
        Add and initialize an exchange connection.
        
        Args:
            exchange_name: Exchange name (e.g., 'binance', 'okx')
            api_key_encrypted: Encrypted API key
            secret_encrypted: Encrypted API secret
            passphrase_encrypted: Encrypted API passphrase (for some exchanges)
            testnet: Use testnet mode
        
        Returns:
            tuple: (success: bool, error_message: str)
        """
        try:
            # Decrypt credentials
            api_key = decrypt_api_key(api_key_encrypted)
            secret = decrypt_api_key(secret_encrypted)
            passphrase = decrypt_api_key(passphrase_encrypted) if passphrase_encrypted else None
            
            # Initialize exchange
            exchange_class = getattr(ccxt, exchange_name.lower())
            config = {
                'apiKey': api_key,
                'secret': secret,
                'enableRateLimit': True,
            }
            
            if passphrase:
                config['password'] = passphrase
            
            if testnet:
                config['options'] = {'defaultType': 'spot', 'sandbox': True}
            
            exchange = exchange_class(config)
           
            # Test connection
            await exchange.load_markets()
            
            self.exchanges[exchange_name] = exchange
            logger.info(f"✅ {exchange_name} connected successfully")
            return True, ""
            
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            logger.error(f"❌ Failed to connect to {exchange_name}: [{error_type}] {error_msg}")
            
            # Provide user-friendly error messages
            if not error_msg:
                return False, f"Connection failed: {error_type} (check server logs for details)"
            elif "Invalid API" in error_msg or "invalid signature" in error_msg.lower():
                return False, f"Invalid API Key or Secret - {error_msg}"
            elif "IP" in error_msg or "not in whitelist" in error_msg.lower():
                return False, f"IP not whitelisted - {error_msg}"
            elif "permission" in error_msg.lower() or "not authorized" in error_msg.lower():
                return False, f"Insufficient permissions - {error_msg}"
            elif "Invalid passphrase" in error_msg or "passphrase" in error_msg.lower():
                return False, f"Invalid passphrase - {error_msg}"
            elif "400" in error_msg or "401" in error_msg or "403" in error_msg:
                return False, f"Authentication failed ({error_type}) - Check your API credentials"
            else:
                return False, f"{error_type}: {error_msg}"
    
    def get_exchange(self, exchange_name: str) -> Optional[ccxt.Exchange]:
        """Get exchange instance by name."""
        return self.exchanges.get(exchange_name)
    
    async def fetch_balance(self, exchange_name: str) -> dict:
        """Fetch balance from exchange. Always returns a dict, never None."""
        try:
            exchange = self.get_exchange(exchange_name)
            if not exchange:
                raise ValueError(f"Exchange {exchange_name} not initialized")
            
            balance = await exchange.fetch_balance()
            
            # Ensure balance is always a dict, never None or other types
            if not isinstance(balance, dict):
                logger.warning(f"Invalid balance type for {exchange_name}: {type(balance)}")
                return {}
            
            return balance
        
        except Exception as e:
            logger.error(f"Balance fetch error for {exchange_name}: {e}")
            return {}
    
    async def fetch_ticker(self, exchange_name: str, symbol: str) -> dict:
        """Fetch ticker for symbol."""
        exchange = self.get_exchange(exchange_name)
        if not exchange:
            raise ValueError(f"Exchange {exchange_name} not initialized")
        return await exchange.fetch_ticker(symbol)
    
    async def close_all(self):
        """Close all exchange connections."""
        for name, exchange in self.exchanges.items():
            try:
                await exchange.close()
                logger.info(f"Closed connection to {name}")
            except Exception as e:
                logger.error(f"Error closing {name}: {e}")
