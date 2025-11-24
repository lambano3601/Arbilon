"""
Opportunity detector - scans for arbitrage opportunities.
"""
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Callable

logger = logging.getLogger(__name__)


class OpportunityDetector:
    """Detects arbitrage opportunities across exchanges."""
    
    def __init__(self, exchange_manager, fee_manager, config):
        self.exchange_manager = exchange_manager
        self.fee_manager = fee_manager
        self.config = config
        self.monitoring_active = False
        self.monitoring_task = None
        self.risk_manager = None
        self.position_tracker = None
        self.trade_executor = None
        self.alert_callback = None  # Telegram alert function
    
    def set_risk_manager(self, risk_manager):
        """Set risk manager for validation."""
        self.risk_manager = risk_manager
    
    def set_position_tracker(self, position_tracker):
        """Set position tracker for drift checks."""
        self.position_tracker = position_tracker
    
    def set_trade_executor(self, executor):
        """Set trade executor for auto-execution."""
        self.trade_executor = executor
    
    def set_alert_callback(self, callback: Callable):
        """Set callback function for sending Telegram alerts."""
        self.alert_callback = callback
    
    async def get_price(self, exchange_name: str, pair: str) -> float:
        """Fetch current price for a pair."""
        try:
            ticker = await self.exchange_manager.fetch_ticker(exchange_name, pair)
            return ticker['last']
        except Exception as e:
            logger.error(f"Error fetching price for {pair} on {exchange_name}: {e}")
            return 0
    
    async def scan_for_opportunities(self) -> List[Dict]:
        """
        Scan all configured pairs for arbitrage opportunities.
        
        Returns:
            List of opportunity dicts
        """
        opportunities = []
        
        trade_amount = self.config['trading_config']['trade_amount_usdt']
        pairs = self.config['trading_pairs']
        risk_limits = self.config['risk_limits']
        
        for pair_config in pairs:
            if not pair_config.get('enabled', True):
                continue
            
            pair = pair_config['pair']
            exchanges = pair_config['exchanges']
            
            if len(exchanges) < 2:
                continue
            
            # Fetch prices from all exchanges
            prices = {}
            for exchange in exchanges:
                price = await self.get_price(exchange, pair)
                if price > 0:
                    prices[exchange] = price
            
            if len(prices) < 2:
                continue
            
            # Find cheapest and most expensive
            cheapest_ex = min(prices, key=prices.get)
            expensive_ex = max(prices, key=prices.get)
            
            buy_price = prices[cheapest_ex]
            sell_price = prices[expensive_ex]
            
            # Calculate gross spread
            gross_spread = ((sell_price - buy_price) / buy_price) * 100
            
            if gross_spread < risk_limits['min_spread_percent_gross']:
                continue
            
            # Calculate quantity
            quantity = trade_amount / buy_price
            
            # Fetch fees
            buy_fee_pct = await self.fee_manager.get_taker_fee(cheapest_ex, pair)
            sell_fee_pct = await self.fee_manager.get_maker_fee(expensive_ex, pair)
            
            # Calculate profit
            buy_cost = trade_amount
            buy_fee_usd = buy_cost * (buy_fee_pct / 100)
            total_buy_cost = buy_cost + buy_fee_usd
            
            sell_revenue = quantity * sell_price
            sell_fee_usd = sell_revenue * (sell_fee_pct / 100)
            total_sell_revenue = sell_revenue - sell_fee_usd
            
            net_profit = total_sell_revenue - total_buy_cost
            roi = (net_profit / total_buy_cost) * 100 if total_buy_cost > 0 else 0
            
            # Check profitability
            if net_profit < risk_limits['min_profit_usd']:
                continue
            
            # Opportunity found!
            opportunity = {
                'pair': pair,
                'buy_exchange': cheapest_ex,
                'sell_exchange': expensive_ex,
                'buy_price': buy_price,
                'sell_price': sell_price,
                'quantity': quantity,
                'trade_amount': trade_amount,
                'gross_spread': gross_spread,
                'gross_profit': sell_revenue - buy_cost,
                'buy_fee': buy_fee_usd,
                'sell_fee': sell_fee_usd,
                'total_fees': buy_fee_usd + sell_fee_usd,
                'net_profit': net_profit,
                'roi': roi,
                'timestamp': datetime.now()
            }
            
            # Risk validation if risk manager available
            if self.risk_manager:
                is_valid, errors = await self.risk_manager.validate_opportunity(
                    opportunity,
                    self.config,
                    self.position_tracker
                )
                
                if not is_valid:
                    logger.warning(f"Risk validation failed for {pair}: {errors}")
                    continue
            
            opportunities.append(opportunity)
            logger.info(f"💰 Opportunity found: {pair} - ${net_profit:.2f} profit ({roi:.2f}%)")
        
        return opportunities
    
    async def start_monitoring(self):
        """Start continuous monitoring loop."""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return False
        
        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Monitoring started")
        return True
    
    async def stop_monitoring(self):
        """Stop monitoring loop."""
        if not self.monitoring_active:
            return False
        
        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Monitoring stopped")
        return True
    
    async def _monitoring_loop(self):
        """Main monitoring loop - runs every N seconds."""
        interval = self.config['trading_config'].get('monitoring_interval_seconds', 5)
        auto_execute = self.config['trading_config'].get('auto_execute', False)
        require_approval = self.config['trading_config'].get('require_manual_approval', True)
        
        logger.info(f"Monitoring loop started (interval: {interval}s, auto_execute: {auto_execute})")
        
        while self.monitoring_active:
            try:
                # Scan for opportunities
                opportunities = await self.scan_for_opportunities()
                
                for opp in opportunities:
                    if auto_execute and not require_approval:
                        # Auto-execute
                        if self.trade_executor:
                            logger.info(f"Auto-executing trade for {opp['pair']}")
                            success, result = await self.trade_executor.execute_arbitrage(opp)
                            
                            if success:
                                await self._send_alert(f"✅ Trade executed: {opp['pair']} - Profit: ${result['profit']['net']:.2f}")
                            else:
                                await self._send_alert(f"❌ Trade failed: {opp['pair']} - {result}")
                    else:
                        # Send alert for manual approval
                        await self._send_opportunity_alert(opp)
                
                # Wait before next scan
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(interval)
    
    async def _send_opportunity_alert(self, opp: Dict):
        """Send opportunity alert via Telegram."""
        if not self.alert_callback:
            return
        
        alert_text = (
            f"💰 *Opportunity Detected*\n\n"
            f"Pair: {opp['pair']}\n"
            f"Buy: {opp['buy_exchange']} @ ${opp['buy_price']:.6f}\n"
            f"Sell: {opp['sell_exchange']} @ ${opp['sell_price']:.6f}\n\n"
            f"Net Profit: ${opp['net_profit']:.2f} ({opp['roi']:.2f}%)\n"
            f"Fees: ${opp['total_fees']:.2f}\n\n"
            f"Use /execute to trade"
        )
        
        await self.alert_callback(alert_text)
    
    async def _send_alert(self, text: str):
        """Send generic alert."""
        if self.alert_callback:
            await self.alert_callback(text)
    
    def is_monitoring(self) -> bool:
        """Check if monitoring is active."""
        return self.monitoring_active
