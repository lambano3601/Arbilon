"""
Drift Calculator - Calculates inventory drift and rebalancing needs.
"""
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


def calculate_drift(
    current_positions: Dict[str, Dict[str, float]],
    initial_balances: Dict[str, Dict[str, float]]
) -> Dict:
    """
    Calculate how far current positions have drifted from initial state.
    
    Args:
        current_positions: {'exchange': {'asset': amount}}
        initial_balances: {'exchange': {'asset': amount}}
    
    Returns:
        {
            'overall_drift_percent': float,
            'by_exchange': {'exchange': drift_percent},
            'by_asset': {'asset': drift_percent},
            'needs_rebalancing': bool,
            'rebalancing_suggestions': [...]
        }
    """
    # Calculate total value per exchange (in USDT equivalent)
    current_totals = {}
    initial_totals = {}
    
    for exchange in current_positions:
        current_totals[exchange] = _calculate_usdt_value(current_positions[exchange])
        initial_totals[exchange] = _calculate_usdt_value(initial_balances.get(exchange, {}))
    
    # Calculate overall drift
    total_current = sum(current_totals.values())
    total_initial = sum(initial_totals.values())
    
    overall_drift_percent = 0
    if total_initial > 0:
        overall_drift_percent = abs((total_current - total_initial) / total_initial) * 100
    
    # Calculate per-exchange drift
    by_exchange = {}
    for exchange in current_totals:
        initial = initial_totals.get(exchange, 0)
        current = current_totals[exchange]
        
        if initial > 0:
            drift = abs((current - initial) / initial) * 100
            by_exchange[exchange] = round(drift, 2)
        else:
            by_exchange[exchange] = 0.0
    
    # Calculate per-asset drift across all exchanges
    by_asset = _calculate_asset_drift(current_positions, initial_balances)
    
    # Determine if rebalancing is needed
    needs_rebalancing = overall_drift_percent > 15.0 or any(d > 20.0 for d in by_exchange.values())
    
    # Generate rebalancing suggestions
    suggestions = []
    if needs_rebalancing:
        suggestions = _generate_rebalancing_suggestions(
            current_positions,
            initial_balances,
            by_exchange
        )
    
    return {
        'overall_drift_percent': round(overall_drift_percent, 2),
        'by_exchange': by_exchange,
        'by_asset': by_asset,
        'needs_rebalancing': needs_rebalancing,
        'rebalancing_suggestions': suggestions,
        'total_value_current': total_current,
        'total_value_initial': total_initial
    }


def _calculate_usdt_value(positions: Dict[str, float]) -> float:
    """
    Calculate total USDT value of positions.
    For now, just sum USDT. In production, would need price conversion.
    """
    # Simple version: just return USDT balance
    # TODO: Add price conversion for other assets
    return positions.get('USDT', 0)


def _calculate_asset_drift(
    current: Dict[str, Dict[str, float]],
    initial: Dict[str, Dict[str, float]]
) -> Dict[str, float]:
    """Calculate drift per asset across all exchanges."""
    by_asset = {}
    
    # Get all unique assets
    all_assets = set()
    for positions in current.values():
        all_assets.update(positions.keys())
    for positions in initial.values():
        all_assets.update(positions.keys())
    
    for asset in all_assets:
        # Sum current holdings across exchanges
        current_total = sum(
            positions.get(asset, 0) for positions in current.values()
        )
        
        # Sum initial holdings across exchanges
        initial_total = sum(
            positions.get(asset, 0) for positions in initial.values()
        )
        
        if initial_total > 0:
            drift = abs((current_total - initial_total) / initial_total) * 100
            by_asset[asset] = round(drift, 2)
        else:
            by_asset[asset] = 0.0
    
    return by_asset


def _generate_rebalancing_suggestions(
    current: Dict[str, Dict[str, float]],
    initial: Dict[str, Dict[str, float]],
    drift_by_exchange: Dict[str, float]
) -> List[str]:
    """Generate human-readable rebalancing suggestions."""
    suggestions = []
    
    # Find exchanges with highest drift
    sorted_drifts = sorted(
        drift_by_exchange.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    for exchange, drift in sorted_drifts:
        if drift > 20.0:
            current_val = _calculate_usdt_value(current.get(exchange, {}))
            initial_val = _calculate_usdt_value(initial.get(exchange, {}))
            
            if current_val > initial_val:
                suggestions.append(
                    f"🔴 {exchange}: Excess +${current_val - initial_val:.2f} ({drift:.1f}% drift) - Consider withdrawing"
                )
            else:
                suggestions.append(
                    f"🔵 {exchange}: Deficit -${initial_val - current_val:.2f} ({drift:.1f}% drift) - Consider depositing"
                )
    
    if not suggestions:
        suggestions.append("✅ All exchanges within acceptable drift limits")
    
    return suggestions
