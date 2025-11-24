"""
Position Tracker - Tracks holdings across all exchanges.
"""
import logging
import json
import aiofiles
from pathlib import Path
from typing import Dict
from config import POSITIONS_FILE
from utils.drift_calculator import calculate_drift

logger = logging.getLogger(__name__)


class PositionTracker:
    """Tracks positions and inventory across exchanges."""
    
    def __init__(self, exchange_manager):
        self.exchange_manager = exchange_manager
        self.initial_balances = {}
        self.current_positions = {}
    
    async def initialize(self):
        """Initialize by fetching current balances as baseline."""
        try:
            # Fetch balances from all exchanges
            for exchange_name in self.exchange_manager.exchanges.keys():
                balance = await self.exchange_manager.fetch_balance(exchange_name)
                
                # Extract free balances
                positions = {}
                for currency, data in balance.items():
                    if isinstance(data, dict) and 'free' in data:
                        free_amount = data['free']
                        if free_amount > 0:
                            positions[currency] = free_amount
                
                self.initial_balances[exchange_name] = positions
                self.current_positions[exchange_name] = positions.copy()
            
            # Save initial state
            await self.save_positions()
            logger.info(f"Position tracker initialized with {len(self.initial_balances)} exchanges")
            
        except Exception as e:
            logger.error(f"Error initializing position tracker: {e}")
    
    async def load_positions(self):
        """Load positions from file."""
        if POSITIONS_FILE.exists():
            try:
                async with aiofiles.open(POSITIONS_FILE, 'r') as f:
                    content = await f.read()
                    data = json.loads(content)
                    
                    self.initial_balances = data.get('initial_balances', {})
                    self.current_positions = data.get('current_positions', {})
                    
                logger.info("Positions loaded from file")
            except Exception as e:
                logger.error(f"Error loading positions: {e}")
    
    async def save_positions(self):
        """Save positions to file."""
        try:
            data = {
                'initial_balances': self.initial_balances,
                'current_positions': self.current_positions,
                'last_updated': None  # TODO: Add timestamp
            }
            
            async with aiofiles.open(POSITIONS_FILE, 'w') as f:
                await f.write(json.dumps(data, indent=2))
                
        except Exception as e:
            logger.error(f"Error saving positions: {e}")
    
    async def refresh_positions(self):
        """Fetch latest balances from all exchanges."""
        try:
            for exchange_name in self.exchange_manager.exchanges.keys():
                balance = await self.exchange_manager.fetch_balance(exchange_name)
                
                positions = {}
                for currency, data in balance.items():
                    if isinstance(data, dict) and 'free' in data:
                        free_amount = data['free']
                        if free_amount > 0:
                            positions[currency] = free_amount
                
                self.current_positions[exchange_name] = positions
            
            await self.save_positions()
            logger.info("Positions refreshed")
            
        except Exception as e:
            logger.error(f"Error refreshing positions: {e}")
    
    async def update_after_trade(self, trade_record: Dict):
        """Update positions after a trade execution."""
        try:
            buy_exchange = trade_record['buy']['exchange']
            sell_exchange = trade_record['sell']['exchange']
            
            pair = trade_record['pair']
            base_currency = pair.split('/')[0]
            quote_currency = pair.split('/')[1]
            
            quantity = trade_record['quantity']
            buy_cost = trade_record['buy'].get('cost', trade_record['trade_amount_usd'])
            sell_revenue = trade_record['sell'].get('cost', 0)
            
            # Update buy exchange (spent USDT, received crypto)
            if buy_exchange in self.current_positions:
                self.current_positions[buy_exchange][quote_currency] = \
                    self.current_positions[buy_exchange].get(quote_currency, 0) - buy_cost
                self.current_positions[buy_exchange][base_currency] = \
                    self.current_positions[buy_exchange].get(base_currency, 0) + quantity
            
            # Update sell exchange (spent crypto, received USDT)
            if sell_exchange in self.current_positions:
                self.current_positions[sell_exchange][base_currency] = \
                    self.current_positions[sell_exchange].get(base_currency, 0) - quantity
                self.current_positions[sell_exchange][quote_currency] = \
                    self.current_positions[sell_exchange].get(quote_currency, 0) + sell_revenue
            
            await self.save_positions()
            logger.info(f"Positions updated after trade {trade_record.get('trade_id')}")
            
        except Exception as e:
            logger.error(f"Error updating positions after trade: {e}")
    
    async def get_positions(self) -> Dict:
        """Get current positions across all exchanges."""
        return {
            'current': self.current_positions,
            'initial': self.initial_balances
        }
    
    async def calculate_drift(self) -> Dict:
        """Calculate current inventory drift."""
        return calculate_drift(
            self.current_positions,
            self.initial_balances
        )
    
    async def get_rebalance_suggestions(self) -> list:
        """Get rebalancing suggestions."""
        drift_data = await self.calculate_drift()
        return drift_data.get('rebalancing_suggestions', [])
    
    async def reset_baseline(self):
        """Reset initial balances to current state (after manual rebalancing)."""
        self.initial_balances = {
            exchange: positions.copy()
            for exchange, positions in self.current_positions.items()
        }
        await self.save_positions()
        logger.info("Baseline reset to current positions")
