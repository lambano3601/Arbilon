"""
Main Telegram bot class with professional, user-friendly interface.
"""
import logging
import json
import aiofiles
import asyncio
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from config import CONFIG_FILE, API_KEYS_FILE

logger = logging.getLogger(__name__)


class ArbitrageBot:
    """Professional Telegram arbitrage bot with interactive UI."""
    
    def __init__(self, token: str, exchange_manager, opportunity_detector):
        self.token = token
        self.exchange_manager = exchange_manager
        self.opportunity_detector = opportunity_detector
        self.app = None
        self.user_states = {}
    
    async def load_config(self) -> dict:
        """Load configuration from file."""
        try:
            async with aiofiles.open(CONFIG_FILE, 'r') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
    
    async def save_config(self, config: dict):
        """Save configuration to file."""
        try:
            async with aiofiles.open(CONFIG_FILE, 'w') as f:
                await f.write(json.dumps(config, indent=2))
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command with main menu."""
        keyboard = [
            [InlineKeyboardButton("🔧 Setup", callback_data="menu_setup")],
            [InlineKeyboardButton("💰 Trading", callback_data="menu_trading")],
            [InlineKeyboardButton("📊 Portfolio", callback_data="menu_portfolio")],
            [InlineKeyboardButton("📈 Monitor", callback_data="menu_monitor")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = (
            "🤖 *Arbitrage Trading Bot*\n\n"
            "Welcome! I help you find and execute profitable arbitrage opportunities.\n\n"
            "Choose an option below to get started:"
        )
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "menu_setup":
            await self.show_setup_menu(query)
        elif data == "menu_trading":
            await self.show_trading_menu(query)
        elif data == "menu_portfolio":
            await self.show_portfolio_menu(query)
        elif data == "menu_monitor":
            await self.show_monitor_menu(query)
        elif data == "help":
            await self.show_help(query)
        elif data == "main_menu":
            await self.show_main_menu(query)
        elif data == "setup_exchanges":
            await self.setup_exchanges_flow(query)
        elif data == "setup_pairs":
            await self.setup_pairs_flow(query)
        elif data == "setup_config":
            await self.setup_config_flow(query)
        elif data.startswith("exch_"):
            exchange_name = data.replace("exch_", "")
            await self.handle_exchange_selection(query, exchange_name)
        elif data == "scan_now":
            await self.scan_opportunities(query)
        elif data == "view_opportunities":
            await self.view_opportunities(query)
        elif data == "view_balances":
            await self.view_balances(query)
        elif data == "view_positions":
            await self.view_positions(query)
        elif data == "check_drift":
            await self.check_drift(query)
        elif data == "start_monitor":
            await self.start_monitoring(query)
        elif data == "stop_monitor":
            await self.stop_monitoring(query)
        elif data == "monitor_status":
            await self.monitor_status(query)
    
    async def show_main_menu(self, query):
        """Show main menu."""
        keyboard = [
            [InlineKeyboardButton("🔧 Setup", callback_data="menu_setup")],
            [InlineKeyboardButton("💰 Trading", callback_data="menu_trading")],
            [InlineKeyboardButton("📊 Portfolio", callback_data="menu_portfolio")],
            [InlineKeyboardButton("📈 Monitor", callback_data="menu_monitor")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "🤖 *Main Menu*\n\nChoose an option:"
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_setup_menu(self, query):
        """Show setup menu."""
        keyboard = [
            [InlineKeyboardButton("➕ Add Exchange", callback_data="setup_exchanges")],
            [InlineKeyboardButton("📝 Configure Pairs", callback_data="setup_pairs")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="setup_config")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        config = await self.load_config()
        num_pairs = len(config.get('trading_pairs', []))
        num_exchanges = len(self.exchange_manager.exchanges)
        
        text = (
            "🔧 *Setup & Configuration*\n\n"
            f"Connected Exchanges: {num_exchanges}\n"
            f"Trading Pairs: {num_pairs}\n\n"
            "What would you like to configure?"
        )
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_trading_menu(self, query):
        """Show trading menu."""
        keyboard = [
            [InlineKeyboardButton("🔍 Scan Now", callback_data="scan_now")],
            [InlineKeyboardButton("📋 View Opportunities", callback_data="view_opportunities")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "💰 *Trading*\n\nFind and execute arbitrage opportunities:"
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_portfolio_menu(self, query):
        """Show portfolio menu."""
        keyboard = [
            [InlineKeyboardButton("💵 View Balances", callback_data="view_balances")],
            [InlineKeyboardButton("📦 Positions", callback_data="view_positions")],
            [InlineKeyboardButton("📊 Check Drift", callback_data="check_drift")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "📊 *Portfolio Management*\n\nView your holdings and drift:"
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_monitor_menu(self, query):
        """Show monitoring menu."""
        is_monitoring = self.opportunity_detector.is_monitoring()
        
        if is_monitoring:
            keyboard = [
                [InlineKeyboardButton("⏸ Stop Monitoring", callback_data="stop_monitor")],
                [InlineKeyboardButton("📊 Status", callback_data="monitor_status")],
                [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
            ]
            status_text = "🟢 *Status: ACTIVE*"
        else:
            keyboard = [
                [InlineKeyboardButton("▶️ Start Monitoring", callback_data="start_monitor")],
                [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
            ]
            status_text = "🔴 *Status: STOPPED*"
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        config = await self.load_config()
        interval = config.get('trading_config', {}).get('monitoring_interval_seconds', 5)
        auto_exec = config.get('trading_config', {}).get('auto_execute', False)
        
        text = (
            f"📈 *Continuous Monitoring*\n\n"
            f"{status_text}\n\n"
            f"Scan Interval: {interval}s\n"
            f"Auto-Execute: {'Yes' if auto_exec else 'No'}\n\n"
            "Start monitoring to automatically scan for opportunities."
        )
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_help(self, query):
        """Show help information."""
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            "ℹ️ *Help & Information*\n\n"
            "*Quick Start:*\n"
            "1️⃣ Add exchanges (Setup → Add Exchange)\n"
            "2️⃣ Configure trading pairs (Setup → Configure Pairs)\n"
            "3️⃣ Set trade amount (Setup → Settings)\n"
            "4️⃣ Scan for opportunities (Trading → Scan Now)\n\n"
            "*Features:*\n"
            "• Real-time opportunity detection\n"
            "• Risk validation before execution\n"
            "• Position drift monitoring\n"
            "• Automated continuous scanning\n\n"
            "*Safety:*\n"
            "• Pre-execution balance checks\n"
            "• Profitability validation\n"
            "• Configurable risk limits"
        )
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def setup_exchanges_flow(self, query):
        """Start exchange setup flow."""
        user_id = query.from_user.id
        self.user_states[user_id] = {'flow': 'add_exchange', 'step': 'select_exchange'}
        
        keyboard = [
            [InlineKeyboardButton("Binance", callback_data="exch_binance")],
            [InlineKeyboardButton("OKX", callback_data="exch_okx")],
            [InlineKeyboardButton("KuCoin", callback_data="exch_kucoin")],
            [InlineKeyboardButton("Bybit", callback_data="exch_bybit")],
            [InlineKeyboardButton("🔙 Cancel", callback_data="menu_setup")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "➕ *Add Exchange*\n\nSelect the exchange you want to add:"
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_exchange_selection(self, query, exchange_name: str):
        """Handle exchange selection and guide through API key setup."""
        user_id = query.from_user.id
        
        self.user_states[user_id] = {
            'flow': 'add_exchange',
            'step': 'api_key',
            'exchange': exchange_name
        }
        
        keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data="menu_setup")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            f"🔑 *Add {exchange_name.upper()} API Keys*\n\n"
            f"Please send your API credentials in this format:\n\n"
            f"```\n"
            f"API Key: your_api_key_here\n"
            f"Secret: your_secret_here\n"
        )
        
        if exchange_name in ['okx', 'kucoin']:
            text += f"Passphrase: your_passphrase_here\n"
        
        text += (
            f"```\n\n"
            f"⚠️ *Security Tips:*\n"
            f"• Use testnet for initial testing\n"
            f"• Enable trading only (no withdrawals)\n"
            f"• Never share these keys"
        )
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def setup_pairs_flow(self, query):
        """Start pairs setup flow."""
        user_id = query.from_user.id
        self.user_states[user_id] = {'flow': 'add_pairs', 'step': 'input'}
        
        keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data="menu_setup")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            "📝 *Configure Trading Pairs*\n\n"
            "Send me the trading pairs you want to monitor.\n\n"
            "*Format:* `BTC/USDT`, `ETH/USDT`, `SOL/USDT`\n"
            "(comma-separated or one per line)\n\n"
            "*Example:*\n"
            "`BTC/USDT, ETH/USDT`"
        )
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def setup_config_flow(self, query):
        """Start config setup flow."""
        config = await self.load_config()
        current_amount = config.get('trading_config', {}).get('trade_amount_usdt', 100)
        
        user_id = query.from_user.id
        self.user_states[user_id] = {'flow': 'set_config', 'step': 'input'}
        
        keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data="menu_setup")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            f"⚙️ *Trade Settings*\n\n"
            f"Current trade amount: `${current_amount}`\n\n"
            "Send me the new trade amount in USD.\n\n"
            "*Example:* `100` for $100 per trade"
        )
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def scan_opportunities(self, query):
        """Scan for opportunities."""
        await query.edit_message_text("🔍 *Scanning for opportunities...*\n\nPlease wait...", parse_mode='Markdown')
        
        opportunities = await self.opportunity_detector.scan_for_opportunities()
        
        if not opportunities:
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_trading")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            text = "🔍 *Scan Complete*\n\nNo profitable opportunities found at this time."
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            return
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_trading")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"💰 *Found {len(opportunities)} Opportunities!*\n\n"
        for i, opp in enumerate(opportunities[:5], 1):
            text += (
                f"*{i}. {opp['pair']}*\n"
                f"   Buy: {opp['buy_exchange']} @ ${opp['buy_price']:.6f}\n"
                f"   Sell: {opp['sell_exchange']} @ ${opp['sell_price']:.6f}\n"
                f"   💵 Profit: `${opp['net_profit']:.2f}` ({opp['roi']:.2f}%)\n"
                f"   💸 Fees: ${opp['total_fees']:.2f}\n\n"
            )
        
        if len(opportunities) > 5:
            text += f"_...and {len(opportunities) - 5} more_"
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def view_opportunities(self, query):
        """View current opportunities."""
        await self.scan_opportunities(query)
    
    async def view_balances(self, query):
        """View exchange balances."""
        if not self.exchange_manager.exchanges:
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_portfolio")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            text = "⚠️ No exchanges connected yet.\n\nPlease add exchanges first."
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            return
        
        text = "💵 *Exchange Balances*\n\n"
        for exchange_name in self.exchange_manager.exchanges.keys():
            try:
                balance = await self.exchange_manager.fetch_balance(exchange_name)
                usdt = balance.get('USDT', {}).get('free', 0)
                text += f"*{exchange_name.upper()}*\n   USDT: `${usdt:.2f}`\n\n"
            except Exception as e:
                text += f"*{exchange_name.upper()}*\n   ❌ Error fetching\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_portfolio")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def view_positions(self, query):
        """View positions (placeholder)."""
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_portfolio")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "📦 *Positions*\n\n_Feature coming soon..._"
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def check_drift(self, query):
        """Check drift (placeholder)."""
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_portfolio")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "📊 *Drift Analysis*\n\n_Feature coming soon..._"
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def start_monitoring(self, query):
        """Start monitoring."""
        success = await self.opportunity_detector.start_monitoring()
        
        if success:
            text = "✅ *Monitoring Started!*\n\nContinuously scanning for opportunities..."
        else:
            text = "⚠️ Monitoring is already active."
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_monitor")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def stop_monitoring(self, query):
        """Stop monitoring."""
        success = await self.opportunity_detector.stop_monitoring()
        
        if success:
            text = "⏸ *Monitoring Stopped*"
        else:
            text = "⚠️ Monitoring was not active."
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_monitor")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def monitor_status(self, query):
        """Show monitor status."""
        await self.show_monitor_menu(query)
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text input based on user state."""
        user_id = update.effective_user.id
        state = self.user_states.get(user_id)
        
        if not state:
            await update.message.reply_text("ℹ️ Use /start to see the main menu.", parse_mode='Markdown')
            return
        
        flow = state.get('flow')
        
        if flow == 'add_exchange':
            await self.process_api_keys(update, state)
        elif flow == 'add_pairs':
            await self.process_pairs_input(update)
        elif flow == 'set_config':
            await self.process_config_input(update)
    
    async def process_api_keys(self, update: Update, state: dict):
        """Process API key input."""
        try:
            text = update.message.text.strip()
            exchange_name = state.get('exchange')
            
            lines = text.split('\n')
            credentials = {}
            
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if 'api' in key or 'key' in key:
                        credentials['api_key'] = value
                    elif 'secret' in key:
                        credentials['secret'] = value
                    elif 'pass' in key:
                        credentials['passphrase'] = value
            
            if 'api_key' not in credentials or 'secret' not in credentials:
                await update.message.reply_text(
                    "❌ Missing API Key or Secret.\n\n"
                    "Please send both:\n"
                    "`API Key: your_key`\n"
                    "`Secret: your_secret`",
                    parse_mode='Markdown'
                )
                return
            
            from utils.security import encrypt_api_key
            
            api_keys = {}
            if API_KEYS_FILE.exists():
                async with aiofiles.open(API_KEYS_FILE, 'r') as f:
                    content = await f.read()
                    api_keys = json.loads(content)
            api_keys['exchanges'] = api_keys.get('exchanges', {})
            api_keys['exchanges'][exchange_name] = {
                'api_key': encrypt_api_key(credentials['api_key']),
                'secret': encrypt_api_key(credentials['secret']),
                'passphrase': encrypt_api_key(credentials.get('passphrase', '')) if 'passphrase' in credentials else None
            }
            
            async with aiofiles.open(API_KEYS_FILE, 'w') as f:
                await f.write(json.dumps(api_keys, indent=2))
            
            await update.message.reply_text(f"⏳ Connecting to {exchange_name.upper()}...", parse_mode='Markdown')
            
            success, error_msg = await self.exchange_manager.add_exchange(
                exchange_name,
                credentials['api_key'],
                credentials['secret'],
                credentials.get('passphrase')
            )
            
            self.user_states.pop(update.effective_user.id, None)
            
            keyboard = [[InlineKeyboardButton("🔙 Back to Setup", callback_data="menu_setup")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if success:
                text = f"✅ *{exchange_name.upper()} Connected!*\n\nYour exchange is now ready to use."
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                text = (
                    f"❌ *Connection Failed*\n\n"
                    f"*Error:* {error_msg}\n\n"
                    f"*Troubleshooting:*\n"
                    f"• Verify API keys are correct\n"
                    f"• Enable Spot Trading permissions\n"
                    f"• Remove IP restrictions (or whitelist your IP)\n"
                    f"• For testing, try testnet first"
                )
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Error processing API keys: {e}")
            await update.message.reply_text("❌ Error processing API keys. Please try again.", parse_mode='Markdown')
                'secret': encrypt_api_key(credentials['secret']),
                'passphrase': encrypt_api_key(credentials.get('passphrase', '')) if 'passphrase' in credentials else None
            }
            
    
    async def process_pairs_input(self, update: Update):
        """Process pairs input."""
        text = update.message.text.strip()
        raw_pairs = re.split(r'[,\n]+', text)
        pairs = [p.strip().upper() for p in raw_pairs if p.strip()]
        
        config = await self.load_config()
        
        valid_pairs = []
        for pair in pairs:
            if re.match(r'^[A-Z0-9]+/USDT$', pair):
                pair_config = {
                    'pair': pair,
                    'enabled': True,
                    'exchanges': list(self.exchange_manager.exchanges.keys()) if self.exchange_manager.exchanges else ['binance', 'okx']
                }
                valid_pairs.append(pair_config)
        
        config['trading_pairs'] = valid_pairs
        await self.save_config(config)
        
        self.user_states.pop(update.effective_user.id, None)
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Setup", callback_data="menu_setup")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"✅ *Configured {len(valid_pairs)} trading pairs:*\n\n"
        for p in valid_pairs:
            text += f"• {p['pair']}\n"
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def process_config_input(self, update: Update):
        """Process config input."""
        try:
            amount = float(update.message.text.strip())
            if amount <= 0:
                raise ValueError()
            
            config = await self.load_config()
            config['trading_config']['trade_amount_usdt'] = amount
            await self.save_config(config)
            
            self.user_states.pop(update.effective_user.id, None)
            
            keyboard = [[InlineKeyboardButton("🔙 Back to Setup", callback_data="menu_setup")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = f"✅ *Trade amount set to:* `${amount:.2f}`"
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        except:
            await update.message.reply_text("❌ Invalid amount. Please send a positive number.", parse_mode='Markdown')
    
    def setup_handlers(self):
        """Set up handlers."""
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
    
    def run(self):
        """Start the bot - Windows compatible."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        self.app = Application.builder().token(self.token).build()
        self.setup_handlers()
        
        logger.info("Bot starting...")
        self.app.run_polling(drop_pending_updates=True)
