"""
Trade executor with mandatory pre-execution validation.
CRITICAL: Checks balance and profitability before EVERY trade.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)


async def execute_arbitrage(
    opportunity: Dict,
    exchanges: Dict,
    send_telegram_alert,
    calculate_profit,
    get_price
) -> Tuple[bool, str]:
    """
    Execute trade with equal USD amounts - WITH PRE-EXECUTION VALIDATION
    
    Args:
        opportunity: Validated opportunity dict containing:
            - pair, buy_exchange, sell_exchange
            - trade_amount, quantity
            - buy_price, sell_price, net_profit
        exchanges: Dict of initialized CCXT exchange objects
        send_telegram_alert: Function to send Telegram messages
        calculate_profit: Function to recalculate profit
        get_price: Function to fetch current price
    
    Returns:
        Tuple[bool, str]: (success, message/error)
    """
    pair = opportunity['pair']
    buy_exchange = opportunity['buy_exchange']
    sell_exchange = opportunity['sell_exchange']
    trade_amount = opportunity['trade_amount']
    quantity = opportunity['quantity']
    base_currency = pair.split('/')[0]  # e.g., 'BTC' from 'BTC/USDT'
    quote_currency = pair.split('/')[1]  # e.g., 'USDT' from 'BTC/USDT'
    
    try:
        # ═══════════════════════════════════════════════════════════
        # PRE-EXECUTION VALIDATION (CRITICAL - DO NOT SKIP)
        # ═══════════════════════════════════════════════════════════
        
        logger.info(f"🔍 Starting pre-execution validation for {pair}")
        
        # 1. VERIFY TRADE PROFITABILITY (MANDATORY)
        if opportunity['net_profit'] <= 0:
            error_msg = f"❌ TRADE REJECTED: Not profitable! Net profit = ${opportunity['net_profit']:.2f}"
            logger.error(error_msg)
            await send_telegram_alert(error_msg)
            return False, error_msg
        
        logger.info(f"✅ Profitability check passed: Net profit = ${opportunity['net_profit']:.2f}")
        
        # 2. CHECK USDT BALANCE ON BUY EXCHANGE
        buy_balance = await exchanges[buy_exchange].fetch_balance()
        usdt_available = buy_balance.get(quote_currency, {}).get('free', 0)
        
        if usdt_available < trade_amount:
            error_msg = (
                f"❌ INSUFFICIENT {quote_currency} on {buy_exchange}\\n"
                f"   Required: ${trade_amount:.2f}\\n"
                f"   Available: ${usdt_available:.2f}\\n"
                f"   Shortfall: ${trade_amount - usdt_available:.2f}"
            )
            logger.error(error_msg)
            await send_telegram_alert(error_msg)
            return False, error_msg
        
        logger.info(f"✅ {quote_currency} balance check passed on {buy_exchange}: ${usdt_available:.2f}")
        
        # 3. CHECK TOKEN BALANCE ON SELL EXCHANGE
        sell_balance = await exchanges[sell_exchange].fetch_balance()
        token_available = sell_balance.get(base_currency, {}).get('free', 0)
        
        if token_available < quantity:
            error_msg = (
                f"❌ INSUFFICIENT {base_currency} on {sell_exchange}\\n"
                f"   Required: {quantity:.8f} {base_currency}\\n"
                f"   Available: {token_available:.8f} {base_currency}\\n"
                f"   Shortfall: {quantity - token_available:.8f} {base_currency}"
            )
            logger.error(error_msg)
            await send_telegram_alert(error_msg)
            return False, error_msg
        
        logger.info(f"✅ {base_currency} balance check passed on {sell_exchange}: {token_available:.8f}")
        
        # 4. RE-VERIFY PRICES HAVEN'T MOVED UNFAVORABLY
        current_buy_price = await get_price(buy_exchange, pair)
        current_sell_price = await get_price(sell_exchange, pair)
        
        # Recalculate profit with current prices
        current_profit = await calculate_profit(
            pair, buy_exchange, sell_exchange, trade_amount
        )
        
        if current_profit['net_profit'] <= 0:
            error_msg = (
                f"❌ PRICE MOVED - Trade no longer profitable!\\n"
                f"   Original profit: ${opportunity['net_profit']:.2f}\\n"
                f"   Current profit: ${current_profit['net_profit']:.2f}\\n"
                f"   Buy price: ${opportunity['buy_price']:.2f} → ${current_buy_price:.2f}\\n"
                f"   Sell price: ${opportunity['sell_price']:.2f} → ${current_sell_price:.2f}"
            )
            logger.error(error_msg)
            await send_telegram_alert(error_msg)
            return False, error_msg
        
        logger.info(f"✅ Price re-verification passed: Still profitable at ${current_profit['net_profit']:.2f}")
        
        # All validation passed - proceed with execution
        logger.info(f"🚀 ALL PRE-CHECKS PASSED - Executing trade for {pair}")
        await send_telegram_alert(
            f"🚀 Executing trade:\\n"
            f"   Pair: {pair}\\n"
            f"   Buy: {quantity:.8f} on {buy_exchange} @ ${current_buy_price:.2f}\\n"
            f"   Sell: {quantity:.8f} on {sell_exchange} @ ${current_sell_price:.2f}\\n"
            f"   Expected profit: ${current_profit['net_profit']:.2f}"
        )
        
        # STEP 1: Place BUY order
        logger.info(f"📥 Placing BUY order on {buy_exchange}")
        buy_order = await exchanges[buy_exchange].create_market_buy_order(
            symbol=pair,
            amount=quantity
        )
        
        await asyncio.sleep(1)
        
        # Verify buy filled
        buy_status = await exchanges[buy_exchange].fetch_order(
            buy_order['id'], pair
        )
        
        if buy_status['status'] != 'closed':
            raise Exception(f"Buy order not filled: {buy_status['status']}")
        
        logger.info(f"✅ Buy order filled: {buy_status['filled']} @ {buy_status.get('average', 'N/A')}")
        
        # STEP 2: Place SELL order
        logger.info(f"📤 Placing SELL order on {sell_exchange}")
        sell_order = await exchanges[sell_exchange].create_market_sell_order(
            symbol=pair,
            amount=quantity
        )
        
        await asyncio.sleep(1)
        
        # Verify sell filled
        sell_status = await exchanges[sell_exchange].fetch_order(
            sell_order['id'], pair
        )
        
        if sell_status['status'] != 'closed':
            raise Exception(f"Sell order not filled: {sell_status['status']}")
        
        logger.info(f"✅ Sell order filled: {sell_status['filled']} @ {sell_status.get('average', 'N/A')}")
        
        # Calculate actual profit
        actual_buy_cost = buy_status['cost'] + buy_status.get('fee', {}).get('cost', 0)
        actual_sell_revenue = sell_status['cost'] - sell_status.get('fee', {}).get('cost', 0)
        actual_profit = actual_sell_revenue - actual_buy_cost
        
        # Record trade
        trade_record = {
            'trade_id': f"trade_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'timestamp': datetime.now().isoformat(),
            'pair': pair,
            'quantity': quantity,
            'trade_amount_usd': trade_amount,
            'buy': {
                'exchange': buy_exchange,
                'price': buy_status.get('average', buy_status.get('price', 0)),
                'fee': buy_status.get('fee', {}).get('cost', 0),
                'order_id': buy_order['id']
            },
            'sell': {
                'exchange': sell_exchange,
                'price': sell_status.get('average', sell_status.get('price', 0)),
                'fee': sell_status.get('fee', {}).get('cost', 0),
                'order_id': sell_order['id']
            },
            'profit': {
                'gross': sell_status['cost'] - buy_status['cost'],
                'net': actual_profit,
                'roi': (actual_profit / actual_buy_cost) * 100 if actual_buy_cost > 0 else 0
            },
            'status': 'completed'
        }
        
        success_msg = (
            f"✅ TRADE COMPLETED!\\n"
            f"   Pair: {pair}\\n"
            f"   Quantity: {quantity:.8f}\\n"
            f"   Actual Profit: ${actual_profit:.2f} ({trade_record['profit']['roi']:.2f}%)\\n"
            f"   Buy: ${actual_buy_cost:.2f} on {buy_exchange}\\n"
            f"   Sell: ${actual_sell_revenue:.2f} on {sell_exchange}"
        )
        
        logger.info(success_msg)
        await send_telegram_alert(success_msg)
        
        return True, trade_record
        
    except Exception as e:
        error_msg = f"❌ Trade execution failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await send_telegram_alert(error_msg)
        return False, str(e)
