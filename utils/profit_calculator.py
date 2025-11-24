"""
Profit calculator for equal trade amounts.
"""
import logging

logger = logging.getLogger(__name__)


async def calculate_profit(
    pair: str,
    buy_exchange: str,
    sell_exchange: str,
    trade_amount_usd: float,
    exchanges: dict,
    get_taker_fee,
    get_maker_fee,
    get_price
) -> dict:
    """
    Calculate profit with EQUAL trade amounts
    Buy $X worth of crypto, sell $X worth of crypto
    
    Args:
        pair: Trading pair (e.g., 'BTC/USDT')
        buy_exchange: Exchange to buy from
        sell_exchange: Exchange to sell on
        trade_amount_usd: USD amount to trade
        exchanges: Dict of exchange objects
        get_taker_fee: Function to get taker fee
        get_maker_fee: Function to get maker fee
        get_price: Function to get current price
    
    Returns:
        Dict with profit calculations
    """
    # Fetch current prices
    buy_price = await get_price(buy_exchange, pair)
    sell_price = await get_price(sell_exchange, pair)
    
    # Calculate quantity based on TRADE AMOUNT
    # If trade_amount_usd = $100 and BTC price = $40,000
    # Then quantity = 100 / 40000 = 0.0025 BTC
    quantity = trade_amount_usd / buy_price
    
    # Buy side calculation
    buy_cost = trade_amount_usd
    buy_fee_rate = await get_taker_fee(buy_exchange, pair) / 100
    buy_fee_usd = buy_cost * buy_fee_rate
    total_buy_cost = buy_cost + buy_fee_usd
    
    # Sell side calculation
    sell_revenue = quantity * sell_price
    sell_fee_rate = await get_maker_fee(sell_exchange, pair) / 100
    sell_fee_usd = sell_revenue * sell_fee_rate
    total_sell_revenue = sell_revenue - sell_fee_usd
    
    # Net profit
    gross_profit = sell_revenue - buy_cost
   total_fees = buy_fee_usd + sell_fee_usd
    net_profit = total_sell_revenue - total_buy_cost
    
    return {
        'quantity': quantity,
        'buy_price': buy_price,
        'sell_price': sell_price,
        'buy_cost': buy_cost,
        'sell_revenue': sell_revenue,
        'gross_profit': gross_profit,
        'total_fees': total_fees,
        'net_profit': net_profit,
        'roi': (net_profit / total_buy_cost) * 100 if total_buy_cost > 0 else 0
    }
