"""
Risk Manager - Validates all risk limits before trade execution.
"""
import logging
from datetime import datetime
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class RiskManager:
    """Manages risk validation for arbitrage opportunities."""
    
    def __init__(self):
        self.active_trades = []  # Track concurrent trades
    
    async def validate_opportunity(
        self,
        opportunity: Dict,
        config: Dict,
        position_tracker=None
    ) -> Tuple[bool, List[str]]:
        """
        Validate opportunity against all risk limits.
        
        Args:
            opportunity: Opportunity data with prices, profit, etc.
            config: Configuration with risk limits
            position_tracker: Optional position tracker for drift checks
        
        Returns:
            (is_valid, errors): Tuple of validation result and error messages
        """
        errors = []
        risk_limits = config.get('risk_limits', {})
        
        # 1. SPREAD VALIDATION
        spread_errors = await self._validate_spread(opportunity, risk_limits)
        errors.extend(spread_errors)
        
        # 2. PROFIT VALIDATION
        profit_errors = await self._validate_profit(opportunity, risk_limits)
        errors.extend(profit_errors)
        
        # 3. POSITION LIMITS
        position_errors = await self._validate_position_limits(opportunity, risk_limits)
        errors.extend(position_errors)
        
        # 4. INVENTORY DRIFT (if position tracker available)
        if position_tracker:
            drift_errors = await self._validate_drift(position_tracker, risk_limits)
            errors.extend(drift_errors)
        
        # 5. PRICE MOVEMENT CHECK
        price_errors = await self._validate_price_stability(opportunity, risk_limits)
        errors.extend(price_errors)
        
        is_valid = len(errors) == 0
        
        if not is_valid:
            logger.warning(f"Risk validation failed for {opportunity.get('pair')}: {errors}")
        else:
            logger.info(f"Risk validation passed for {opportunity.get('pair')}")
        
        return is_valid, errors
    
    async def _validate_spread(self, opportunity: Dict, limits: Dict) -> List[str]:
        """Validate spread requirements."""
        errors = []
        
        buy_price = opportunity.get('buy_price', 0)
        sell_price = opportunity.get('sell_price', 0)
        
        if buy_price <= 0 or sell_price <= 0:
            errors.append("Invalid prices")
            return errors
        
        # Calculate gross spread
        gross_spread = ((sell_price - buy_price) / buy_price) * 100
        
        min_gross = limits.get('min_spread_percent_gross', 0.5)
        if gross_spread < min_gross:
            errors.append(
                f"Gross spread {gross_spread:.3f}% below minimum {min_gross}%"
            )
        
        # Calculate net spread (after fees)
        total_fees_pct = (opportunity.get('total_fees', 0) / opportunity.get('trade_amount', 1)) * 100
        net_spread = gross_spread - total_fees_pct
        
        min_net = limits.get('min_spread_percent_net', 0.3)
        if net_spread < min_net:
            errors.append(
                f"Net spread {net_spread:.3f}% below minimum {min_net}%"
            )
        
        return errors
    
    async def _validate_profit(self, opportunity: Dict, limits: Dict) -> List[str]:
        """Validate profit requirements."""
        errors = []
        
        net_profit = opportunity.get('net_profit', 0)
        total_fees = opportunity.get('total_fees', 0)
        gross_profit = opportunity.get('gross_profit', 0)
        
        # Check minimum profit
        min_profit = limits.get('min_profit_usd', 5.0)
        if net_profit < min_profit:
            errors.append(
                f"Net profit ${net_profit:.2f} below minimum ${min_profit:.2f}"
            )
        
        # Check fees don't eat >50% of gross profit
        if gross_profit > 0:
            fee_impact_pct = (total_fees / gross_profit) * 100
            max_fee_impact = limits.get('max_fee_impact_percent', 50.0)
            
            if fee_impact_pct > max_fee_impact:
                errors.append(
                    f"Fees consume {fee_impact_pct:.1f}% of gross profit (max {max_fee_impact}%)"
                )
        
        return errors
    
    async def _validate_position_limits(self, opportunity: Dict, limits: Dict) -> List[str]:
        """Validate position size and concurrent trade limits."""
        errors = []
        
        trade_amount = opportunity.get('trade_amount', 0)
        
        # Check max trade size
        max_trade = limits.get('max_position_size_usd', 500.0)
        if trade_amount > max_trade:
            errors.append(
                f"Trade amount ${trade_amount:.2f} exceeds maximum ${max_trade:.2f}"
            )
        
        # Check concurrent trades
        max_concurrent = limits.get('max_concurrent_trades', 3)
        if len(self.active_trades) >= max_concurrent:
            errors.append(
                f"Already have {len(self.active_trades)} active trades (max {max_concurrent})"
            )
        
        return errors
    
    async def _validate_drift(self, position_tracker, limits: Dict) -> List[str]:
        """Validate inventory drift is within limits."""
        errors = []
        
        try:
            drift_data = await position_tracker.calculate_drift()
            
            overall_drift = drift_data.get('overall_drift_percent', 0)
            max_overall = limits.get('max_inventory_drift_percent', 15.0)
            
            if overall_drift > max_overall:
                errors.append(
                    f"Overall inventory drift {overall_drift:.1f}% exceeds {max_overall}% (REBALANCE NEEDED)"
                )
            
            # Check per-exchange drift
            max_per_exchange = limits.get('max_per_exchange_drift_percent', 20.0)
            by_exchange = drift_data.get('by_exchange', {})
            
            for exchange, drift in by_exchange.items():
                if drift > max_per_exchange:
                    errors.append(
                        f"{exchange} drift {drift:.1f}% exceeds {max_per_exchange}%"
                    )
        
        except Exception as e:
            logger.error(f"Error checking drift: {e}")
            # Don't block trade on drift check error
        
        return errors
    
    async def _validate_price_stability(self, opportunity: Dict, limits: Dict) -> List[str]:
        """Check price hasn't moved significantly since detection."""
        errors = []
        
        # This would require storing initial detection time and price
        # For now, we can add a timestamp check
        timestamp = opportunity.get('timestamp')
        if timestamp:
            # If opportunity is older than X seconds, flag it
            age_seconds = (datetime.now() - timestamp).total_seconds()
            max_age = limits.get('max_opportunity_age_seconds', 10)
            
            if age_seconds > max_age:
                errors.append(
                    f"Opportunity is {age_seconds:.1f}s old (stale, max {max_age}s)"
                )
        
        return errors
    
    def register_trade(self, trade_id: str):
        """Register a trade as active."""
        self.active_trades.append({
            'id': trade_id,
            'timestamp': datetime.now()
        })
        logger.info(f"Registered active trade: {trade_id}")
    
    def complete_trade(self, trade_id: str):
        """Mark a trade as completed."""
        self.active_trades = [
            t for t in self.active_trades if t['id'] != trade_id
        ]
        logger.info(f"Completed trade: {trade_id}")
    
    def get_active_trade_count(self) -> int:
        """Get number of currently active trades."""
        return len(self.active_trades)
