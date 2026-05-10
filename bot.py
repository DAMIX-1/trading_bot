from dotenv import load_dotenv
load_dotenv()
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from tinydb import TinyDB, Query

# ==========================================
# PERSISTENT STORAGE - MONGODB
# ==========================================
import os
from pymongo import MongoClient

MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://botuser:FashinA2@tradingbot.d8jbbyz.mongodb.net/?appName=TRADINGBOT")

client = MongoClient(MONGO_URI)
mongo_db = client['trading_bot']

portfolios_col = mongo_db['portfolios']
watchlists_col = mongo_db['watchlists']
alerts_col = mongo_db['alerts']
admins_col = mongo_db['admins']
users_col = mongo_db['users']

# ---- PORTFOLIO ----
def get_portfolio(user_id):
    result = portfolios_col.find_one({"user_id": user_id})
    if not result:
        default = {
            "user_id": user_id,
            "balance": 10000.00,
            "trades": [],
            "positions": {}
        }
        portfolios_col.insert_one(default)
        return default
    return result

def save_portfolio(user_id, portfolio):
    portfolio.pop('_id', None)
    portfolios_col.update_one(
        {"user_id": user_id},
        {"$set": portfolio},
        upsert=True
    )

# ---- WATCHLIST ----
def get_watchlist(user_id):
    result = watchlists_col.find_one({"user_id": user_id})
    if not result:
        return []
    return result.get("symbols", [])

def save_watchlist(user_id, symbols):
    watchlists_col.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "symbols": symbols}},
        upsert=True
    )

# ---- ALERTS ----
def get_alerts(user_id):
    result = alerts_col.find_one({"user_id": user_id})
    if not result:
        return []
    return result.get("alerts", [])

def save_alerts(user_id, user_alerts):
    alerts_col.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "alerts": user_alerts}},
        upsert=True
    )

# ---- ADMINS ----
def load_admins():
    result = admins_col.find_one({"type": "admins"})
    if not result:
        return []
    return result.get("list", [])

def save_admins(admin_list):
    admins_col.update_one(
        {"type": "admins"},
        {"$set": {"type": "admins", "list": admin_list}},
        upsert=True
    )

# ---- USERS ----
def load_users():
    result = users_col.find_one({"type": "users"})
    if not result:
        return []
    return result.get("list", [])

def save_users(user_list):
    users_col.update_one(
        {"type": "users"},
        {"$set": {"type": "users", "list": user_list}},
        upsert=True
    )
# ==========================================
# CONFIGURATION
# ==========================================
BOT_TOKEN = "8670800784:AAGT7aq4rYoWjGtpQvn0WTp2COM0999bCZY"  # Paste your BotFather token here
# ==========================================
# ACCESS CONTROL
# ==========================================
OWNER_ID = 6738675531  # Replace with your Telegram user ID

# Load from persistent storage on startup
ADMINS = load_admins()
ALLOWED_USERS = load_users()

def is_owner(user_id):
    return user_id == OWNER_ID

def is_admin(user_id):
    return user_id in ADMINS or is_owner(user_id)

def is_allowed(user_id):
    return user_id in ALLOWED_USERS or is_admin(user_id)

def restricted(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not is_allowed(user_id):
            await update.message.reply_text("⛔ Access denied. You are not authorized to use this bot.")
            return
        return await func(update, context)
    return wrapper

def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not is_admin(user_id):
            await update.message.reply_text("⛔ Admin access required.")
            return
        return await func(update, context)
    return wrapper

def owner_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not is_owner(user_id):
            await update.message.reply_text("⛔ Owner access required.")
            return
        return await func(update, context)
    return wrapper

# ==========================================
# ACCESS MANAGEMENT COMMANDS
# ==========================================
@owner_only
async def addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(ADMINS) >= 3:
        await update.message.reply_text(
            "⛔ Admin slots full (3/3).\n"
            "Remove an admin first with /removeadmin [user_id]"
        )
        return
    if not context.args:
        await update.message.reply_text("Usage: /addadmin [user_id]")
        return
    try:
        new_admin = int(context.args[0])
    except:
        await update.message.reply_text("❌ Invalid user ID.")
        return
    if new_admin in ADMINS:
        await update.message.reply_text("⚠️ User is already an admin.")
        return
    ADMINS.append(new_admin)
    save_admins(ADMINS)
    await update.message.reply_text(
        f"✅ Admin added successfully.\n"
        f"Admin slots used: {len(ADMINS)}/3"
    )

@owner_only
async def removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /removeadmin [user_id]")
        return
    try:
        admin_id = int(context.args[0])
    except:
        await update.message.reply_text("❌ Invalid user ID.")
        return
    if admin_id not in ADMINS:
        await update.message.reply_text("❌ User is not an admin.")
        return
    ADMINS.remove(admin_id)
    save_admins(ADMINS)
    await update.message.reply_text("✅ Admin removed successfully.")

@admin_only
async def adduser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /adduser [user_id]")
        return
    try:
        new_user = int(context.args[0])
    except:
        await update.message.reply_text("❌ Invalid user ID.")
        return
    if new_user in ALLOWED_USERS:
        await update.message.reply_text("⚠️ User already has access.")
        return
    if is_admin(new_user):
        await update.message.reply_text("⚠️ User is already an admin.")
        return
    ALLOWED_USERS.append(new_user)
    save_users(ALLOWED_USERS)
    await update.message.reply_text(f"✅ User {new_user} added successfully.")

@admin_only
async def removeuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /removeuser [user_id]")
        return
    try:
        user_id_to_remove = int(context.args[0])
    except:
        await update.message.reply_text("❌ Invalid user ID.")
        return
    if user_id_to_remove not in ALLOWED_USERS:
        await update.message.reply_text("❌ User not found in access list.")
        return
    ALLOWED_USERS.remove(user_id_to_remove)
    save_users(ALLOWED_USERS)
    await update.message.reply_text(f"✅ User {user_id_to_remove} removed successfully.")

@admin_only
async def listusers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = (
        f"👥 Access List\n"
        f"{'='*30}\n"
        f"👑 Owner: {OWNER_ID}\n\n"
        f"🛡 Admins ({len(ADMINS)}/3):\n"
    )
    if ADMINS:
        for a in ADMINS:
            response += f"  • {a}\n"
    else:
        response += "  None\n"

    response += f"\n👤 Users ({len(ALLOWED_USERS)}):\n"
    if ALLOWED_USERS:
        for u in ALLOWED_USERS:
            response += f"  • {u}\n"
    else:
        response += "  None\n"

    await update.message.reply_text(response)

# ==========================================
# COMMANDS
# ==========================================
@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to your Trading Analysis Bot!\n\n"
        "📊 Markets covered:\n"
        "• Crypto\n"
        "• Stocks\n"
        "• Forex\n"
        "• Futures\n"
        "• Indices\n\n"
        "Type /help to see all available commands."
    )

@restricted
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 Available Commands:\n\n"
        "/start - Welcome message\n"
        "/analyze - Analyze any asset\n"
        "/signal - Get buy/sell signal\n"
        "/crypto - Crypto signals\n"
        "/stocks - Stock signals\n"
        "/forex - Forex signals\n"
        "/futures - Futures signals\n"
        "/indices - Indices signals\n"
        "/watchlist - Your watchlist\n"
        "/alert - Set price alert\n"
        "/portfolio - Paper trading portfolio\n"
        "/trade - Simulate a trade\n"
        "/performance - Bot signal performance\n"
        "/screener - Market screener\n"
        "/sentiment - Market sentiment\n"
        "/news - Latest market news\n"
        "/rugcheck - Meme coin rug check\n"
        "/onchain - On-chain analysis\n"
        "/status - Bot status\n"
    )

@restricted
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is online and all systems operational.")
import yfinance as yf
import pandas as pd

# ==========================================
# MARKET DATA HELPER
# ==========================================
def get_market_data(symbol: str, timeframe: str = "1d", period: str = None):
    try:
        timeframe_map = {
            "1m":  ("1d",  "1m"),
            "5m":  ("60d", "5m"),
            "15m": ("60d", "15m"),
            "30m": ("1mo", "30m"),
            "1h":  ("1mo", "60m"),
            "4h":  ("3mo", "1h"),
            "1d":  ("3mo", "1d"),
            "1w":  ("1y",  "1wk"),
        }
        if timeframe not in timeframe_map:
            timeframe = "1d"

        auto_period, interval = timeframe_map[timeframe]
        fetch_period = period if period else auto_period

        ticker = yf.Ticker(symbol)
        df = ticker.history(period=fetch_period, interval=interval)
        if df.empty:
            return None
        return df
    except:
        return None
def calculate_indicators(df):
    if len(df) < 20:
       return None
    # Current price
    current_price = df['Close'].iloc[-1]
    
    # Moving averages
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA50'] = df['Close'].rolling(window=50).mean()
    ma20 = df['MA20'].iloc[-1]
    ma50 = df['MA50'].iloc[-1]
    
    # RSI
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs.iloc[-1]))
    
    # MACD
    ema12 = df['Close'].ewm(span=12).mean()
    ema26 = df['Close'].ewm(span=26).mean()
    macd = ema12.iloc[-1] - ema26.iloc[-1]
    
    # Bollinger Bands
    df['BB_mid'] = df['Close'].rolling(window=20).mean()
    df['BB_std'] = df['Close'].rolling(window=20).std()
    bb_upper = df['BB_mid'].iloc[-1] + (2 * df['BB_std'].iloc[-1])
    bb_lower = df['BB_mid'].iloc[-1] - (2 * df['BB_std'].iloc[-1])
    
    # Volume
    avg_volume = df['Volume'].mean()
    current_volume = df['Volume'].iloc[-1]
    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
    
    indicators = {
        'price': round(current_price, 4),
        'ma20': round(ma20, 4),
        'ma50': round(ma50, 4) if not pd.isna(ma50) else None,
        'rsi': round(rsi, 2),
        'macd': round(macd, 4),
        'bb_upper': round(bb_upper, 4),
        'bb_lower': round(bb_lower, 4),
        'volume_ratio': round(volume_ratio, 2)
    }
    # Safety check for NaN values
    for key in ['price', 'ma20', 'rsi', 'macd', 'bb_upper', 'bb_lower', 'volume_ratio']:
        if indicators[key] is None or (isinstance(indicators[key], float) and pd.isna(indicators[key])):
            indicators[key] = 0
    return indicators 
def calculate_tp_sl_trigger(df, indicators, signal):
    price = indicators['price']

    high = df['High']
    low = df['Low']
    close = df['Close']
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(window=14).mean().iloc[-1]

    recent = df.tail(20)
    resistance = recent['High'].max()
    support = recent['Low'].min()

    if "BUY" in signal:
        trigger = round(price * 1.001, 5)
        tp1 = round(price + (atr * 1.5), 5)
        tp2 = round(price + (atr * 2.5), 5)
        tp3 = round(price + (atr * 4.0), 5)
        sl = round(price - (atr * 1.2), 5)
    else:
        trigger = round(price * 0.999, 5)
        tp1 = round(price - (atr * 1.5), 5)
        tp2 = round(price - (atr * 2.5), 5)
        tp3 = round(price - (atr * 4.0), 5)
        sl = round(price + (atr * 1.2), 5)

    # Ensure correct TP progression
    if "BUY" in signal:
        tp1, tp2, tp3 = sorted([tp1, tp2, tp3])
    else:
        tp1, tp2, tp3 = sorted([tp1, tp2, tp3], reverse=True)

    risk = abs(price - sl)
    reward = abs(tp2 - price)
    rr = round(reward / risk, 2) if risk > 0 else 0

    return {
        'trigger': trigger,
        'tp1': tp1,
        'tp2': tp2,
        'tp3': tp3,
        'sl': sl,
        'atr': round(atr, 5),
        'rr': rr
    }
# ==========================================
# AI ANALYSIS LAYER - GROQ
# ==========================================
from groq import Groq

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
groq_client = Groq(api_key=GROQ_API_KEY)

async def get_ai_analysis(symbol: str, timeframe: str, indicators: dict, signal: str, confidence: int, levels: dict, news_items: list = []):
    try:
        news_text = ""
        if news_items:
            news_text = "Recent News:\n" + "\n".join([f"• {n}" for n in news_items[:3]])

        prompt = f"""You are a professional trading analyst. Analyze the following market data and provide a concise 4-6 sentence analysis.

Asset: {symbol} | Timeframe: {timeframe}
Current Price: ${indicators['price']} | Signal: {signal} | Confidence: {confidence}%

Technical Indicators:
- RSI: {indicators['rsi']} (above 70 = overbought, below 30 = oversold)
- MACD: {indicators['macd']} (positive = bullish, negative = bearish)
- MA20: ${indicators['ma20']} | MA50: ${indicators.get('ma50', 'N/A')}
- Bollinger Upper: ${indicators['bb_upper']} | Lower: ${indicators['bb_lower']}
- Volume: {indicators['volume_ratio']}x average

Trade Levels:
- Trigger: ${levels['trigger']} | TP1: ${levels['tp1']} | TP2: ${levels['tp2']} | TP3: ${levels['tp3']}
- Stop Loss: ${levels['sl']} | R:R: 1:{levels['rr']}

{news_text}

Focus on: why the signal is {signal}, whether TP/SL levels make sense, key levels to watch, overall trade quality. Be professional and actionable."""

        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"AI analysis unavailable: {str(e)}"


async def get_ai_trade_levels(symbol: str, timeframe: str, indicators: dict, signal: str, df):
    try:
        recent = df.tail(50)
        resistance_levels = sorted(recent['High'].nlargest(3).tolist(), reverse=True)
        support_levels = sorted(recent['Low'].nsmallest(3).tolist())
        price = indicators['price']

        prompt = f"""You are a professional trading analyst. Calculate the BEST stop loss, take profit levels and trigger price.

Asset: {symbol} | Timeframe: {timeframe} | Current Price: ${price} | Signal: {signal}

Technical Data:
- RSI: {indicators['rsi']} | MACD: {indicators['macd']}
- MA20: ${indicators['ma20']} | MA50: ${indicators.get('ma50', 'N/A')}
- BB Upper: ${indicators['bb_upper']} | BB Lower: ${indicators['bb_lower']}
- Volume: {indicators['volume_ratio']}x average
- Recent Resistance: {[round(r, 4) for r in resistance_levels]}
- Recent Support: {[round(s, 4) for s in support_levels]}

Rules:
- For BUY: SL below nearest support, TP1/TP2/TP3 at resistance levels
- For SELL: SL above nearest resistance, TP1/TP2/TP3 at support levels
- Minimum 1:2 risk/reward ratio
- Trigger should be confirmation entry point

Respond ONLY in this exact JSON format, no other text:
{{"trigger": 0.0, "tp1": 0.0, "tp2": 0.0, "tp3": 0.0, "sl": 0.0, "rr": 0.0, "reasoning": "brief explanation"}}"""

        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200
        )
        text = response.choices[0].message.content.strip()
        text = text.replace('```json', '').replace('```', '').strip()

        import json
        ai_levels = json.loads(text)
        return ai_levels

    except Exception as e:
        return None

def generate_signal(indicators):
    if indicators is None:
        return "⚪ NEUTRAL", 50, ["Not enough data"]
    
    score = 0
    reasons = []

    # RSI
    if indicators['rsi'] is None or pd.isna(indicators['rsi']):
        reasons.append("RSI unavailable")
    elif indicators['rsi'] < 30:
        score += 2
        reasons.append("RSI oversold 📉")
    elif indicators['rsi'] > 70:
        score -= 2
        reasons.append("RSI overbought 📈")
    else:
        reasons.append(f"RSI neutral ({indicators['rsi']})")

    # MACD
    if indicators['macd'] is None or pd.isna(indicators['macd']):
        reasons.append("MACD unavailable")
    elif indicators['macd'] > 0:
        score += 1
        reasons.append("MACD bullish ✅")
    else:
        score -= 1
        reasons.append("MACD bearish ❌")

    # Moving averages
    if indicators['ma50'] and not pd.isna(indicators['ma50']):
        if indicators['price'] > indicators['ma20'] > indicators['ma50']:
            score += 2
            reasons.append("Price above MA20 & MA50 ✅")
        elif indicators['price'] < indicators['ma20'] < indicators['ma50']:
            score -= 2
            reasons.append("Price below MA20 & MA50 ❌")

    # Bollinger Bands
    if indicators['bb_lower'] and not pd.isna(indicators['bb_lower']):
        if indicators['price'] <= indicators['bb_lower']:
            score += 1
            reasons.append("Price at lower Bollinger Band 📉")
        elif indicators['price'] >= indicators['bb_upper']:
            score -= 1
            reasons.append("Price at upper Bollinger Band 📈")

    # Volume
    if indicators['volume_ratio'] and not pd.isna(indicators['volume_ratio']):
        if indicators['volume_ratio'] > 1.5:
            reasons.append(f"High volume ({indicators['volume_ratio']}x avg) 🔥")

    # RSI overbought add-on
    if indicators['rsi'] and not pd.isna(indicators['rsi']):
        if indicators['rsi'] > 80:
            score -= 1
            reasons.append("RSI extremely overbought ⚠️")

    # Final signal
    if score >= 3:
        signal = "🟢 STRONG BUY"
        confidence = min(50 + (score * 10), 95)
    elif score >= 1:
        signal = "🟡 BUY"
        confidence = min(50 + (score * 8), 80)
    elif score <= -3:
        signal = "🔴 STRONG SELL"
        confidence = min(50 + (abs(score) * 10), 95)
    elif score <= -1:
        signal = "🟠 SELL"
        confidence = min(50 + (abs(score) * 8), 80)
    else:
        signal = "⚪ NEUTRAL"
        confidence = 50

    return signal, confidence, reasons
# ==========================================
# COINGECKO - REAL TIME CRYPTO DATA
# ==========================================

COINGECKO_IDS = {
    "BTC-USD": "bitcoin",
    "ETH-USD": "ethereum",
    "BNB-USD": "binancecoin",
    "SOL-USD": "solana",
    "XRP-USD": "ripple",
    "ADA-USD": "cardano",
    "DOGE-USD": "dogecoin",
    "DOT-USD": "polkadot",
    "MATIC-USD": "matic-network",
    "LTC-USD": "litecoin"
}

async def get_coingecko_price(symbol: str):
    """Get real time crypto price from CoinGecko"""
    try:
        coin_id = COINGECKO_IDS.get(symbol)
        if not coin_id:
            return None
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                return float(data[coin_id]['usd'])
    except:
        return None

async def get_coingecko_klines(symbol: str, timeframe: str = "1h", limit: int = 100):
    """Get crypto OHLCV data from CoinGecko"""
    try:
        coin_id = COINGECKO_IDS.get(symbol)
        if not coin_id:
            # Fall back to yfinance for unknown symbols
            return get_market_data(symbol, timeframe)

        # Map timeframe to CoinGecko days parameter
        days_map = {
            "1m": 1, "5m": 1, "15m": 1, "30m": 1,
            "1h": 7, "4h": 30, "1d": 90, "1w": 365
        }
        days = days_map.get(timeframe, 7)

        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc?vs_currency=usd&days={days}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                if not data or isinstance(data, dict):
                    return None

                df = pd.DataFrame(data, columns=['timestamp', 'Open', 'High', 'Low', 'Close'])
                df['Open'] = df['Open'].astype(float)
                df['High'] = df['High'].astype(float)
                df['Low'] = df['Low'].astype(float)
                df['Close'] = df['Close'].astype(float)
                df['Volume'] = 0.0  # CoinGecko OHLC doesn't include volume

                # Get real time price and patch last candle
                live_price = await get_coingecko_price(symbol)
                if live_price:
                    df.iloc[-1, df.columns.get_loc('Close')] = live_price

                return df
    except:
        return None
# ==========================================
# TWELVE DATA - REAL TIME FOREX
# ==========================================
TWELVE_DATA_API_KEY = "1d1882b4fc4e43bf801a3565473d1dbc"

async def get_twelvedata_forex(symbol: str, timeframe: str = "1h", limit: int = 100):
    """Get real time forex candles from Twelve Data"""
    try:
        # Convert yfinance forex symbol to Twelve Data format
        # EURUSD=X -> EUR/USD
        pair = symbol.replace("=X", "")
        if len(pair) == 6:
            formatted = f"{pair[:3]}/{pair[3:]}"
        else:
            return None

        interval_map = {
            "1m": "1min", "5m": "5min", "15m": "15min",
            "30m": "30min", "1h": "1h", "4h": "4h",
            "1d": "1day", "1w": "1week"
        }
        interval = interval_map.get(timeframe, "1h")

        url = (
            f"https://api.twelvedata.com/time_series?"
            f"symbol={formatted}&interval={interval}"
            f"&outputsize={limit}&apikey={TWELVE_DATA_API_KEY}"
        )

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()

                if data.get('status') == 'error':
                    return None

                values = data.get('values', [])
                if not values:
                    return None

                # Convert to DataFrame
                df = pd.DataFrame(values)
                df = df.rename(columns={
                    'open': 'Open',
                    'high': 'High',
                    'low': 'Low',
                    'close': 'Close',
                    'volume': 'Volume'
                })
                df['Open'] = df['Open'].astype(float)
                df['High'] = df['High'].astype(float)
                df['Low'] = df['Low'].astype(float)
                df['Close'] = df['Close'].astype(float)
                df['Volume'] = df.get('Volume', pd.Series([0]*len(df))).astype(float)

                # Reverse so oldest is first
                df = df.iloc[::-1].reset_index(drop=True)
                return df

    except:
        return None

async def get_forex_price(base: str, quote: str = "USD"):
    """Get real time forex price"""
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{base}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                rates = data.get('rates', {})
                return rates.get(quote)
    except:
        return None

CRYPTO_SYMBOLS = [
    "BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "XRP-USD",
    "ADA-USD", "DOGE-USD", "DOT-USD", "MATIC-USD", "LTC-USD"
]

FOREX_PAIRS = [
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X",
    "USDCAD=X", "USDCHF=X", "NZDUSD=X"
]

def is_crypto(symbol: str):
    return symbol in CRYPTO_SYMBOLS or symbol.endswith("-USD") and not symbol.startswith("^")

def is_forex(symbol: str):
    return "=X" in symbol

async def get_smart_market_data(symbol: str, timeframe: str = "1h"):
    """Smart data fetcher — uses best source per asset type"""
    if is_crypto(symbol):
        df = await get_coingecko_klines(symbol, timeframe, limit=100)
        if df is not None and not df.empty:
            return df, "coingecko"
    
    if is_forex(symbol):
       # Try Twelve Data first for real time candles
       df = await get_twelvedata_forex(symbol, timeframe, limit=100)
       if df is not None and not df.empty:
           return df, "twelvedata"
       # Fallback to yfinance with live price patch
       df = get_market_data(symbol, timeframe)
       if df is not None:
           pair = symbol.replace("=X", "")
           if len(pair) == 6:
              base = pair[:3]
              quote = pair[3:]
              live_price = await get_forex_price(base, quote)
              if live_price:
                  df.iloc[-1, df.columns.get_loc('Close')] = live_price
       return df, "forex"
    
    # Default to yfinance for stocks, indices, futures
    df = get_market_data(symbol, timeframe)
    return df, "yfinance"
# ==========================================
# ANALYZE COMMAND
# ==========================================
@restricted
async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Please provide a symbol and optional timeframe.\n\n"
            "Usage: /analyze [SYMBOL] [TIMEFRAME]\n\n"
            "Timeframes: 1m 5m 15m 30m 1h 4h 1d 1w\n\n"
            "Examples:\n"
            "• /analyze BTC-USD 1h\n"
            "• /analyze EURUSD=X 15m\n"
            "• /analyze AAPL 4h\n"
            "• /analyze GC=F 1d"
        )
        return

    symbol = context.args[0].upper()
    timeframe = context.args[1].lower() if len(context.args) > 1 else "1d"

    valid_timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"]
    if timeframe not in valid_timeframes:
        await update.message.reply_text(
            f"❌ Invalid timeframe: {timeframe}\n"
            f"Valid options: {', '.join(valid_timeframes)}"
        )
        return

    await update.message.reply_text(f"🔍 Analyzing {symbol} on {timeframe} timeframe... please wait.")

    df, source = await get_smart_market_data(symbol, timeframe)
    if df is None or df.empty:
       await update.message.reply_text(f"❌ Could not fetch data for {symbol}. Check the symbol and try again.")
       return

    indicators = calculate_indicators(df)
    if indicators is None:
        await update.message.reply_text("❌ Not enough data for this timeframe. Try a higher timeframe like 1h or 1d.")
        return
    indicators['symbol'] = symbol
    signal_result, confidence, reasons = generate_signal(indicators)

# Try AI-powered trade levels first
    ai_levels = await get_ai_trade_levels(symbol, timeframe, indicators, signal_result, df)
    if ai_levels:
        levels = {
            'trigger': ai_levels.get('trigger', 0),
            'tp1': ai_levels.get('tp1', 0),
            'tp2': ai_levels.get('tp2', 0),
            'tp3': ai_levels.get('tp3', 0),
            'sl': ai_levels.get('sl', 0),
            'rr': ai_levels.get('rr', 0),
            'atr': calculate_tp_sl_trigger(df, indicators, signal_result)['atr']
        }
        ai_reasoning = ai_levels.get('reasoning', '')
    else:
        levels = calculate_tp_sl_trigger(df, indicators, signal_result)
        ai_reasoning = ''

    # Trend strength
    if indicators['price'] > indicators['ma20']:
        trend = "📈 Bullish"
    elif indicators['price'] < indicators['ma20']:
        trend = "📉 Bearish"
    else:
        trend = "➡️ Neutral"

        # Weighted confidence score
    def get_signal_strength(confidence):
        if confidence >= 80:
            return "🔥 Very High"
        elif confidence >= 65:
            return "💪 High"
        elif confidence >= 55:
            return "👍 Medium"
        else:
            return "⚠️ Low"

    def get_momentum_score(indicators):
        score = 0
        if not pd.isna(indicators['rsi']):
            if 40 <= indicators['rsi'] <= 60:
                score += 5
            elif 30 <= indicators['rsi'] <= 70:
                score += 8
            else:
                score += 3
        if indicators['macd'] and not pd.isna(indicators['macd']):
            if indicators['macd'] > 0:
                score += 25
        if indicators['ma50'] and not pd.isna(indicators['ma50']):
            if indicators['price'] > indicators['ma20'] > indicators['ma50']:
                score += 20
            elif indicators['price'] < indicators['ma20'] < indicators['ma50']:
                score += 20
        if indicators['volume_ratio'] and indicators['volume_ratio'] > 1.5:
            score += 15
        return min(score, 100)

    momentum = get_momentum_score(indicators)
    strength = get_signal_strength(confidence)

    # Market condition
    bb_width = indicators['bb_upper'] - indicators['bb_lower']
    bb_mid = (indicators['bb_upper'] + indicators['bb_lower']) / 2
    bb_squeeze = bb_width / bb_mid < 0.02
    market_condition = "↔️ Range-bound ⚠️" if bb_squeeze else "📈 Trending"

    response = (
        f"{'='*30}\n"
        f"📌 {symbol} • {timeframe.upper()}\n"
        f"🔌 {('🟢 CoinGecko' if source == 'coingecko' else '🟢 Twelve Data' if source == 'twelvedata' else '🟠 Yahoo Finance')}\n"
        f"{'='*30}\n"
        f"{signal_result}\n"
        f"Signal Strength: {strength}\n"
        f"Momentum Score: {momentum}/100\n"
        f"Market: {market_condition}\n"
        f"{'='*30}\n"
        f"💰 Price:    ${indicators['price']}\n"
        f"🎯 Entry:    ${levels['trigger']}\n"
        f"❌ SL:       ${levels['sl']}\n"
        f"{'='*30}\n"
        f"✅ TP1:      ${levels['tp1']}\n"
        f"✅ TP2:      ${levels['tp2']}\n"
        f"✅ TP3:      ${levels['tp3']}\n"
        f"⚖️ R:R =    1:{levels['rr']}\n"
        f"{'='*30}\n"
        f"📊 Indicators:\n"
        f"  RSI: {indicators['rsi']} | MACD: {'↑' if indicators['macd'] > 0 else '↓'}\n"
        f"  MA20: ${indicators['ma20']} | MA50: ${indicators['ma50'] or 'N/A'}\n"
        f"  ATR: ${levels['atr']} | Vol: {indicators['volume_ratio']}x\n"
        f"{'='*30}\n"
        f"📝 Reasons:\n"
        + "\n".join(f"  • {r}" for r in reasons) +
        f"\n{'='*30}"
    )

    await update.message.reply_text(response)

    # Get AI interpretation
    await update.message.reply_text("🤖 Getting AI analysis... please wait.")

    # Fetch recent news for context
    try:
        ticker_news = yf.Ticker(symbol).news[:3]
        news_items = [item.get('content', {}).get('title', '') for item in ticker_news]
    except:
        news_items = []

    ai_analysis = await get_ai_analysis(
        symbol, timeframe, indicators,
        signal_result, confidence, levels, news_items
    )

    if ai_reasoning:
        await update.message.reply_text(
            f"📐 AI Trade Level Reasoning:\n"
            f"{ai_reasoning}\n\n"
            f"🤖 AI Market Analysis:\n"
            f"{ai_analysis}"
        )
    else:
        await update.message.reply_text(
            f"🤖 AI Market Analysis:\n"
            f"{ai_analysis}"
        )
# ==========================================
# SIGNAL COMMAND (Quick signal)
# ==========================================
@restricted
async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: /signal [SYMBOL] [TIMEFRAME]\n\n"
            "Examples:\n"
            "• /signal BTC-USD 1h\n"
            "• /signal EURUSD=X 15m"
        )
        return

    symbol = context.args[0].upper()
    timeframe = context.args[1].lower() if len(context.args) > 1 else "1d"

    await update.message.reply_text(f"⚡ Getting {timeframe.upper()} signal for {symbol}...")

    df, source = await get_smart_market_data(symbol, timeframe)
    if df is None:
        await update.message.reply_text(f"❌ Could not fetch data for {symbol}.")
        return

    indicators = calculate_indicators(df)
    if indicators is None:
       await update.message.reply_text("❌ Not enough data for this timeframe. Try a higher timeframe like 1h or 1d.")
       return
    indicators['symbol'] = symbol
    signal_result, confidence, _ = generate_signal(indicators)
    levels = calculate_tp_sl_trigger(df, indicators, signal_result)

    await update.message.reply_text(
        f"⚡ {symbol} — {timeframe.upper()} Signal\n"
        f"{'='*30}\n"
        f"💰 Price: ${indicators['price']}\n"
        f"Signal: {signal_result}\n"
        f"Confidence: {confidence}%\n"
        f"{'='*30}\n"
        f"🎯 Trigger: ${levels['trigger']}\n"
        f"✅ TP1: ${levels['tp1']}\n"
        f"✅ TP2: ${levels['tp2']}\n"
        f"✅ TP3: ${levels['tp3']}\n"
        f"❌ SL: ${levels['sl']}\n"
        f"⚖️ Risk/Reward: 1:{levels['rr']}"
    )

# ==========================================
# CRYPTO COMMAND
# ==========================================
@restricted
async def crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbols = ["BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "XRP-USD"]
    await update.message.reply_text("🔍 Scanning top crypto markets... please wait.")

    response = "🪙 Crypto Signals\n" + "="*30 + "\n"
    for symbol in symbols:
        df = await get_coingecko_klines(symbol, "1h", limit=100)
        if df is None:
            response += f"❌ {symbol} — data unavailable\n\n"
            continue
        indicators = calculate_indicators(df)
        if indicators is None:
            response += f"❌ {symbol} — not enough data\n\n"
            continue
        indicators['symbol'] = symbol
        signal_result, confidence, _ = generate_signal(indicators)
        response += (
            f"📌 {symbol}\n"
            f"💰 ${indicators['price']}\n"
            f"Signal: {signal_result}\n"
            f"Confidence: {confidence}%\n\n"
        )

    await update.message.reply_text(response)

# ==========================================
# STOCKS COMMAND
# ==========================================
@restricted
async def stocks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
    await update.message.reply_text("🔍 Scanning top stocks... please wait.")

    response = "📈 Stock Signals\n" + "="*30 + "\n"
    for symbol in symbols:
        df = get_market_data(symbol)
        if df is None:
            response += f"❌ {symbol} — data unavailable\n\n"
            continue
        indicators = calculate_indicators(df)
        signal_result, confidence, _ = generate_signal(indicators)
        response += (
            f"📌 {symbol}\n"
            f"💰 ${indicators['price']}\n"
            f"Signal: {signal_result}\n"
            f"Confidence: {confidence}%\n\n"
        )

    await update.message.reply_text(response)

# ==========================================
# FOREX COMMAND
# ==========================================
@restricted
async def forex(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbols = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X"]
    await update.message.reply_text("🔍 Scanning forex pairs... please wait.")

    response = "💱 Forex Signals\n" + "="*30 + "\n"
    for symbol in symbols:
        df, _ = await get_smart_market_data(symbol, "1h")
        if df is None:
            response += f"❌ {symbol} — data unavailable\n\n"
            continue
        indicators = calculate_indicators(df)
        signal_result, confidence, _ = generate_signal(indicators)
        response += (
            f"📌 {symbol}\n"
            f"💰 ${indicators['price']}\n"
            f"Signal: {signal_result}\n"
            f"Confidence: {confidence}%\n\n"
        )

    await update.message.reply_text(response)

# ==========================================
# FUTURES COMMAND
# ==========================================
@restricted
async def futures(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbols = ["GC=F", "SI=F", "CL=F", "NG=F", "ZW=F"]
    await update.message.reply_text("🔍 Scanning futures markets... please wait.")

    response = "📦 Futures Signals\n" + "="*30 + "\n"
    for symbol in symbols:
        df = get_market_data(symbol)
        if df is None:
            response += f"❌ {symbol} — data unavailable\n\n"
            continue
        indicators = calculate_indicators(df)
        signal_result, confidence, _ = generate_signal(indicators)
        response += (
            f"📌 {symbol}\n"
            f"💰 ${indicators['price']}\n"
            f"Signal: {signal_result}\n"
            f"Confidence: {confidence}%\n\n"
        )

    await update.message.reply_text(response)

# ==========================================
# INDICES COMMAND
# ==========================================
@restricted
async def indices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbols = ["^GSPC", "^DJI", "^IXIC", "^FTSE", "^N225"]
    await update.message.reply_text("🔍 Scanning indices... please wait.")

    response = "📊 Indices Signals\n" + "="*30 + "\n"
    for symbol in symbols:
        df = get_market_data(symbol)
        if df is None:
            response += f"❌ {symbol} — data unavailable\n\n"
            continue
        indicators = calculate_indicators(df)
        signal_result, confidence, _ = generate_signal(indicators)
        response += (
            f"📌 {symbol}\n"
            f"💰 ${indicators['price']}\n"
            f"Signal: {signal_result}\n"
            f"Confidence: {confidence}%\n\n"
        )

    await update.message.reply_text(response)

# ==========================================
# PAPER TRADING ENGINE
# ==========================================
paper_portfolios = {}

def get_portfolio(user_id):
    if user_id not in paper_portfolios:
        paper_portfolios[user_id] = {
            "balance": 10000.00,
            "trades": [],
            "positions": {}
        }
    return paper_portfolios[user_id]

@restricted
async def trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text(
            "Usage: /trade [BUY/SELL] [SYMBOL] [AMOUNT]\n\n"
            "Examples:\n"
            "• /trade BUY BTC-USD 500\n"
            "• /trade SELL BTC-USD 500"
        )
        return

    action = context.args[0].upper()
    symbol = context.args[1].upper()
    try:
        amount = float(context.args[2])
    except:
        await update.message.reply_text("❌ Invalid amount.")
        return

    if action not in ["BUY", "SELL"]:
        await update.message.reply_text("❌ Action must be BUY or SELL.")
        return

    df = get_market_data(symbol)
    if df is None:
        await update.message.reply_text(f"❌ Could not fetch data for {symbol}.")
        return

    price = df['Close'].iloc[-1]
    user_id = update.effective_user.id
    portfolio = get_portfolio(user_id)

    if action == "BUY":
        if portfolio["balance"] < amount:
            await update.message.reply_text(
                f"❌ Insufficient balance.\n"
                f"Available: ${portfolio['balance']:.2f}"
            )
            return
        units = amount / price
        portfolio["balance"] -= amount
        if symbol in portfolio["positions"]:
            portfolio["positions"][symbol]["units"] += units
            portfolio["positions"][symbol]["avg_price"] = price
        else:
            portfolio["positions"][symbol] = {"units": units, "avg_price": price}
        portfolio["trades"].append({
            "action": "BUY", "symbol": symbol,
            "amount": amount, "price": price, "units": units
        })
        portfolio["balance"] -= amount
        ...
        save_portfolio(user_id, portfolio)
        await update.message.reply_text(
            f"✅ BUY executed!\n"
            f"📌 {symbol}\n"
            f"💰 Price: ${price:.4f}\n"
            f"📦 Units: {units:.6f}\n"
            f"💵 Spent: ${amount:.2f}\n"
            f"🏦 Remaining Balance: ${portfolio['balance']:.2f}"
        )

    elif action == "SELL":
        if symbol not in portfolio["positions"]:
            await update.message.reply_text(f"❌ You have no position in {symbol}.")
            return
        position = portfolio["positions"][symbol]
        sell_value = position["units"] * price
        pnl = sell_value - (position["units"] * position["avg_price"])
        portfolio["balance"] += sell_value
        del portfolio["positions"][symbol]
        portfolio["trades"].append({
            "action": "SELL", "symbol": symbol,
            "sell_value": sell_value, "price": price, "pnl": pnl
        })
        portfolio["balance"] += sell_value
        ...
        save_portfolio(user_id, portfolio)
        await update.message.reply_text(
            f"✅ SELL executed!\n"
            f"📌 {symbol}\n"
            f"💰 Price: ${price:.4f}\n"
            f"💵 Received: ${sell_value:.2f}\n"
            f"📊 P&L: ${pnl:.2f} {'🟢' if pnl >= 0 else '🔴'}\n"
            f"🏦 New Balance: ${portfolio['balance']:.2f}"
        )

@restricted
async def portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    p = get_portfolio(user_id)

    response = "💼 Your Paper Portfolio\n" + "="*30 + "\n"
    response += f"💵 Cash Balance: ${p['balance']:.2f}\n\n"

    if not p["positions"]:
        response += "📭 No open positions.\n"
    else:
        response += "📂 Open Positions:\n"
        total_value = p["balance"]
        for symbol, pos in p["positions"].items():
            df = get_market_data(symbol)
            if df is not None:
                current_price = df['Close'].iloc[-1]
                current_value = pos["units"] * current_price
                pnl = current_value - (pos["units"] * pos["avg_price"])
                total_value += current_value
                response += (
                    f"📌 {symbol}\n"
                    f"   Units: {pos['units']:.6f}\n"
                    f"   Avg Price: ${pos['avg_price']:.4f}\n"
                    f"   Current: ${current_price:.4f}\n"
                    f"   Value: ${current_value:.2f}\n"
                    f"   P&L: ${pnl:.2f} {'🟢' if pnl >= 0 else '🔴'}\n\n"
                )
        response += f"💰 Total Portfolio Value: ${total_value:.2f}"

    await update.message.reply_text(response)

@restricted
async def performance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    p = get_portfolio(user_id)

    trades = [t for t in p["trades"] if t["action"] == "SELL"]
    if not trades:
        await update.message.reply_text("📭 No completed trades yet.")
        return

    total_pnl = sum(t["pnl"] for t in trades)
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    win_rate = (len(wins) / len(trades)) * 100

    await update.message.reply_text(
        f"📊 Trading Performance\n"
        f"{'='*30}\n"
        f"Total Trades: {len(trades)}\n"
        f"Wins: {len(wins)} 🟢\n"
        f"Losses: {len(losses)} 🔴\n"
        f"Win Rate: {win_rate:.1f}%\n"
        f"Total P&L: ${total_pnl:.2f} {'🟢' if total_pnl >= 0 else '🔴'}\n"
        f"Starting Balance: $10,000.00\n"
        f"Current Balance: ${p['balance']:.2f}"
    )
    # ==========================================
# WATCHLIST
# ==========================================
watchlists = {}

def get_watchlist(user_id):
    if user_id not in watchlists:
        watchlists[user_id] = []
    return watchlists[user_id]

@restricted
async def watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    wl = get_watchlist(user_id)

    if context.args:
        action = context.args[0].upper()
        if action == "ADD" and len(context.args) > 1:
           symbol = context.args[1].upper()
           wl = get_watchlist(user_id)
           if symbol in wl:
              await update.message.reply_text(f"⚠️ {symbol} is already in your watchlist.")
              return
           wl.append(symbol)
           save_watchlist(user_id, wl)
           await update.message.reply_text(f"✅ {symbol} added to watchlist.")
           return
        elif action == "REMOVE" and len(context.args) > 1:
            symbol = context.args[1].upper()
            wl = get_watchlist(user_id)
            if symbol not in wl:
               await update.message.reply_text(f"❌ {symbol} not found in watchlist.")
               return
            wl.remove(symbol)
            save_watchlist(user_id, wl)
            await update.message.reply_text(f"✅ {symbol} removed from watchlist.")
            return

    if not wl:
        await update.message.reply_text(
            "📭 Your watchlist is empty.\n\n"
            "Add assets with:\n"
            "• /watchlist ADD BTC-USD\n"
            "• /watchlist ADD AAPL\n"
            "• /watchlist REMOVE BTC-USD"
        )
        return

    await update.message.reply_text("🔍 Fetching watchlist signals... please wait.")
    response = "👁 Your Watchlist\n" + "="*30 + "\n"
    for symbol in wl:
        df = get_market_data(symbol)
        if df is None:
            response += f"❌ {symbol} — data unavailable\n\n"
            continue
        indicators = calculate_indicators(df)
        signal_result, confidence, _ = generate_signal(indicators)
        response += (
            f"📌 {symbol}\n"
            f"💰 ${indicators['price']}\n"
            f"Signal: {signal_result}\n"
            f"Confidence: {confidence}%\n\n"
        )
    await update.message.reply_text(response)

# ==========================================
# PRICE ALERTS
# ==========================================
alerts = {}

def get_alerts(user_id):
    if user_id not in alerts:
        alerts[user_id] = []
    return alerts[user_id]

@restricted
async def alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text(
            "Usage: /alert [SYMBOL] [ABOVE/BELOW] [PRICE]\n\n"
            "Examples:\n"
            "• /alert BTC-USD ABOVE 90000\n"
            "• /alert AAPL BELOW 200"
        )
        return

    symbol = context.args[0].upper()
    direction = context.args[1].upper()
    try:
        target_price = float(context.args[2])
    except:
        await update.message.reply_text("❌ Invalid price.")
        return

    if direction not in ["ABOVE", "BELOW"]:
        await update.message.reply_text("❌ Direction must be ABOVE or BELOW.")
        return

    user_id = update.effective_user.id
    user_alerts = get_alerts(user_id)
    user_alerts.append({
        "symbol": symbol,
        "direction": direction,
        "target": target_price,
        "user_id": user_id
    })
    save_alerts(user_id, user_alerts)

    await update.message.reply_text(
        f"✅ Alert set!\n"
        f"📌 {symbol}\n"
        f"📊 Notify when price goes {direction} ${target_price}"
    )

async def check_alerts(context):
    all_alert_records = alerts_col.all()
    for record in all_alert_records:
        user_id = record.get("user_id")
        user_alerts = record.get("alerts", [])
        if not user_alerts:
            continue
        triggered = []
        for a in user_alerts:
            df = get_market_data(a["symbol"])
            if df is None:
                continue
            current_price = df['Close'].iloc[-1]
            if a["direction"] == "ABOVE" and current_price >= a["target"]:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"🔔 ALERT TRIGGERED!\n"
                        f"📌 {a['symbol']} is now ABOVE ${a['target']}\n"
                        f"💰 Current Price: ${round(current_price, 4)}"
                    )
                )
                triggered.append(a)
            elif a["direction"] == "BELOW" and current_price <= a["target"]:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"🔔 ALERT TRIGGERED!\n"
                        f"📌 {a['symbol']} is now BELOW ${a['target']}\n"
                        f"💰 Current Price: ${round(current_price, 4)}"
                    )
                )
                triggered.append(a)
        for t in triggered:
            user_alerts.remove(t)
        save_alerts(user_id, user_alerts)
@restricted
async def viewalerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_alerts = get_alerts(user_id)

    if not user_alerts:
        await update.message.reply_text("📭 You have no active alerts.")
        return

    response = "🔔 Your Active Alerts\n" + "="*30 + "\n"
    for i, a in enumerate(user_alerts, 1):
        response += (
            f"{i}. {a['symbol']}\n"
            f"   Direction: {a['direction']}\n"
            f"   Target: ${a['target']}\n\n"
        )

    await update.message.reply_text(response)       

# ==========================================
# SCREENER
# ==========================================
@restricted
async def screener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_symbols = [
        "BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "BNB-USD",
        "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN",
        "EURUSD=X", "GBPUSD=X", "AUDUSD=X",
        "GC=F", "CL=F",
        "^GSPC", "^DJI"
    ]
    await update.message.reply_text("🔍 Scanning all markets for best opportunities... please wait.")

    strong_buys = []
    strong_sells = []

    for symbol in all_symbols:
        df = get_market_data(symbol)
        if df is None:
            continue
        indicators = calculate_indicators(df)
        signal_result, confidence, _ = generate_signal(indicators)
        if "STRONG BUY" in signal_result:
            strong_buys.append((symbol, indicators['price'], confidence))
        elif "STRONG SELL" in signal_result:
            strong_sells.append((symbol, indicators['price'], confidence))

    strong_buys.sort(key=lambda x: x[2], reverse=True)
    strong_sells.sort(key=lambda x: x[2], reverse=True)

    response = "🔭 Market Screener\n" + "="*30 + "\n"

    if strong_buys:
        response += "🟢 Top Buy Opportunities:\n"
        for symbol, price, conf in strong_buys[:5]:
            response += f"  • {symbol} @ ${price} — {conf}% confidence\n"
    else:
        response += "🟢 No strong buy signals right now.\n"

    response += "\n"

    if strong_sells:
        response += "🔴 Top Sell Signals:\n"
        for symbol, price, conf in strong_sells[:5]:
            response += f"  • {symbol} @ ${price} — {conf}% confidence\n"
    else:
        response += "🔴 No strong sell signals right now.\n"

    await update.message.reply_text(response)

# ==========================================
# SENTIMENT
# ==========================================
@restricted
async def sentiment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: /sentiment [SYMBOL]\n\n"
            "Example: /sentiment BTC-USD"
        )
        return

    symbol = context.args[0].upper()
    df = get_market_data(symbol)
    if df is None:
        await update.message.reply_text(f"❌ Could not fetch data for {symbol}.")
        return

    indicators = calculate_indicators(df)
    signal_result, confidence, reasons = generate_signal(indicators)

    # Sentiment scoring
    if confidence >= 75:
        if "BUY" in signal_result:
            sentiment_label = "🟢 Very Bullish"
        else:
            sentiment_label = "🔴 Very Bearish"
    elif confidence >= 60:
        if "BUY" in signal_result:
            sentiment_label = "🟡 Bullish"
        else:
            sentiment_label = "🟠 Bearish"
    else:
        sentiment_label = "⚪ Neutral"

    # Trend
    if indicators['price'] > indicators['ma20'] > (indicators['ma50'] or 0):
        trend = "📈 Uptrend"
    elif indicators['price'] < indicators['ma20']:
        trend = "📉 Downtrend"
    else:
        trend = "➡️ Sideways"

    # Momentum
    if indicators['rsi'] > 60:
        momentum = "⚡ Strong"
    elif indicators['rsi'] > 40:
        momentum = "😐 Moderate"
    else:
        momentum = "🐢 Weak"

    await update.message.reply_text(
        f"🧠 Market Sentiment: {symbol}\n"
        f"{'='*30}\n"
        f"Overall: {sentiment_label}\n"
        f"Trend: {trend}\n"
        f"Momentum: {momentum}\n"
        f"RSI: {indicators['rsi']}\n"
        f"Volume: {indicators['volume_ratio']}x average\n"
        f"{'='*30}\n"
        f"Signal: {signal_result}\n"
        f"Confidence: {confidence}%"
    )

# ==========================================
# NEWS
# ==========================================
@restricted
async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = context.args[0].upper() if context.args else None
    await update.message.reply_text("📰 Fetching latest market news...")

    try:
        if symbol:
            ticker = yf.Ticker(symbol)
            news_items = ticker.news[:5]
            response = f"📰 Latest News: {symbol}\n" + "="*30 + "\n"
        else:
            ticker = yf.Ticker("BTC-USD")
            news_items = ticker.news[:5]
            response = "📰 Latest Market News\n" + "="*30 + "\n"

        if not news_items:
            await update.message.reply_text("❌ No news available right now.")
            return

        for item in news_items:
            title = item.get('content', {}).get('title', 'No title')
            response += f"• {title}\n\n"

        await update.message.reply_text(response)
    except Exception as e:
        await update.message.reply_text("❌ Could not fetch news right now. Try again later.")

# ==========================================
# RUG CHECK VIA CONTRACT ADDRESS
# ==========================================
import aiohttp
import re

def detect_chain(address: str):
    if re.match(r'^0x[a-fA-F0-9]{40}$', address):
        return "eth_bsc"
    elif len(address) >= 32 and len(address) <= 44 and not address.startswith('0x'):
        return "solana"
    else:
        return None

async def check_goplus_evm(address: str, chain_id: str):
    url = f"https://api.gopluslabs.io/api/v1/token_security/{chain_id}?contract_addresses={address}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            return data.get('result', {}).get(address.lower(), {})

async def check_goplus_solana(address: str):
    url = f"https://api.gopluslabs.io/api/v1/solana/token_security?contract_addresses={address}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            return data.get('result', {}).get(address, {})

async def check_dexscreener(address: str):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            pairs = data.get('pairs', [])
            return pairs[0] if pairs else None

@restricted
async def rugcheck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: /rugcheck [CONTRACT ADDRESS]\n\n"
            "Examples:\n"
            "• /rugcheck 0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984 (ETH/BSC)\n"
            "• /rugcheck DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB25 (Solana)"
        )
        return

    address = context.args[0].strip()
    chain_type = detect_chain(address)

    if not chain_type:
        await update.message.reply_text("❌ Invalid contract address format.")
        return

    await update.message.reply_text(f"🔍 Analyzing contract {address[:8]}...{address[-6:]} please wait.")

    warnings = []
    info = []
    score = 0

    try:
        # ---- DEX SCREENER DATA ----
        pair = await check_dexscreener(address)
        if pair:
            token_name = pair.get('baseToken', {}).get('name', 'Unknown')
            token_symbol = pair.get('baseToken', {}).get('symbol', 'Unknown')
            price = pair.get('priceUsd', 'N/A')
            liquidity = pair.get('liquidity', {}).get('usd', 0)
            volume_24h = pair.get('volume', {}).get('h24', 0)
            price_change_24h = pair.get('priceChange', {}).get('h24', 0)
            chain = pair.get('chainId', 'Unknown')
            dex = pair.get('dexId', 'Unknown')

            info.append(f"🏷 Name: {token_name} (${token_symbol})")
            info.append(f"⛓ Chain: {chain.upper()} | DEX: {dex.upper()}")
            info.append(f"💰 Price: ${price}")
            info.append(f"💧 Liquidity: ${liquidity:,.0f}")
            info.append(f"📊 24h Volume: ${volume_24h:,.0f}")
            info.append(f"📉 24h Change: {price_change_24h}%")

            if liquidity < 10000:
                warnings.append("⚠️ Very low liquidity (< $10,000) — easy to manipulate")
                score += 3
            elif liquidity < 50000:
                warnings.append("⚠️ Low liquidity (< $50,000) — risky")
                score += 1

            if price_change_24h < -30:
                warnings.append(f"⚠️ Price dumped {price_change_24h}% in 24h")
                score += 2

        # ---- GOPLUS SECURITY DATA ----
        if chain_type == "eth_bsc":
            # Try ETH first then BSC
            security = await check_goplus_evm(address, "1")
            if not security:
                security = await check_goplus_evm(address, "56")
        else:
            security = await check_goplus_solana(address)

        if security:
            # Honeypot
            if security.get('is_honeypot') == '1':
                warnings.append("🚨 HONEYPOT DETECTED — You cannot sell this token")
                score += 10

            # Mint function
            if security.get('is_mintable') == '1':
                warnings.append("⚠️ Mint function exists — dev can print unlimited tokens")
                score += 3

            # Ownership renounced
            if security.get('owner_address') and security.get('owner_address') != '0x0000000000000000000000000000000000000000':
                warnings.append("⚠️ Ownership NOT renounced — dev still controls contract")
                score += 2
            else:
                info.append("✅ Ownership renounced")

            # Buy/sell tax
            buy_tax = security.get('buy_tax', '0')
            sell_tax = security.get('sell_tax', '0')
            try:
                if float(buy_tax) > 10:
                    warnings.append(f"⚠️ High buy tax: {buy_tax}%")
                    score += 2
                if float(sell_tax) > 10:
                    warnings.append(f"⚠️ High sell tax: {sell_tax}%")
                    score += 2
                info.append(f"💸 Buy Tax: {buy_tax}% | Sell Tax: {sell_tax}%")
            except:
                pass

            # Blacklist
            if security.get('is_blacklisted') == '1':
                warnings.append("⚠️ Blacklist function — dev can block wallets from selling")
                score += 2

            # Contract verified
            if security.get('is_open_source') == '0':
                warnings.append("⚠️ Contract NOT verified/open source — code is hidden")
                score += 2
            else:
                info.append("✅ Contract verified & open source")

            # Holder concentration
            holders = security.get('holders', [])
            if holders:
                top_holder_pct = float(holders[0].get('percent', 0)) * 100
                if top_holder_pct > 50:
                    warnings.append(f"⚠️ Top holder owns {top_holder_pct:.1f}% of supply")
                    score += 3
                elif top_holder_pct > 20:
                    warnings.append(f"⚠️ Top holder owns {top_holder_pct:.1f}% — concentrated")
                    score += 1
                info.append(f"👤 Top holder: {top_holder_pct:.1f}% of supply")

            # Liquidity locked
            lp_holders = security.get('lp_holders', [])
            locked = any(h.get('is_locked') == 1 for h in lp_holders)
            if not locked and lp_holders:
                warnings.append("⚠️ Liquidity NOT locked — dev can pull liquidity anytime")
                score += 3
            elif locked:
                info.append("✅ Liquidity locked")

    except Exception as e:
        await update.message.reply_text(f"❌ Error during analysis: {str(e)}")
        return

    # ---- FINAL VERDICT ----
    if score >= 8:
        verdict = "🚨 EXTREME RUG RISK — DO NOT BUY"
    elif score >= 5:
        verdict = "🔴 HIGH RUG RISK — Avoid"
    elif score >= 3:
        verdict = "🟠 MEDIUM RISK — Extreme caution"
    elif score >= 1:
        verdict = "🟡 LOW-MEDIUM RISK — Some red flags"
    else:
        verdict = "🟢 LOW RISK — No major red flags"

    response = (
        f"🔍 Contract Analysis\n"
        f"{'='*30}\n"
        f"📋 Contract: {address[:8]}...{address[-6:]}\n"
    )

    if info:
        response += "\n".join(info) + "\n"

    response += f"{'='*30}\n"

    if warnings:
        response += "\n⚠️ Red Flags:\n"
        for w in warnings:
            response += f"  {w}\n"
    else:
        response += "\n✅ No major red flags detected\n"

    response += f"\n{'='*30}\n🏁 Verdict: {verdict}\n"
    response += f"Risk Score: {score}/10+"

    await update.message.reply_text(response)
@restricted
async def resetportfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    fresh = {
        "user_id": user_id,
        "balance": 10000.00,
        "trades": [],
        "positions": {}
    }
    save_portfolio(user_id, fresh)
    paper_portfolios[user_id] = fresh
    await update.message.reply_text(
        "✅ Portfolio reset!\n"
        "💵 Balance restored to $10,000.00"
    )
# ==========================================
# AUTO SIGNAL BROADCASTER
# ==========================================
broadcast_active = False
broadcast_interval = 30  # default minutes
broadcast_chat_ids = set()

BROADCAST_SYMBOLS = {
    "crypto": ["BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "XRP-USD"],
    "forex": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X"],
    "stocks": ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN"],
    "indices": ["^GSPC", "^DJI", "^FTSE"],
    "futures": ["GC=F", "CL=F"]
}

async def run_broadcast(context):
    global broadcast_active
    if not broadcast_active:
        return

    signals_found = []

    for category, symbols in BROADCAST_SYMBOLS.items():
        for symbol in symbols:
            try:
                df = get_market_data(symbol, "1h")
                if df is None:
                    continue
                indicators = calculate_indicators(df)
                if indicators is None:
                    continue
                indicators['symbol'] = symbol
                signal_result, confidence, _ = generate_signal(indicators)

                # Only broadcast strong signals
                if confidence >= 75 and "NEUTRAL" not in signal_result:
                    levels = calculate_tp_sl_trigger(df, indicators, signal_result)
                    signals_found.append({
                        "symbol": symbol,
                        "category": category.upper(),
                        "price": indicators['price'],
                        "signal": signal_result,
                        "confidence": confidence,
                        "levels": levels
                    })
            except:
                continue

    if not signals_found:
        return

    for chat_id in broadcast_chat_ids:
        try:
            message = "📡 AUTO SIGNAL ALERT\n" + "="*30 + "\n"
            for s in signals_found[:5]:  # Max 5 signals per broadcast
                message += (
                    f"📌 {s['symbol']} [{s['category']}]\n"
                    f"💰 Price: ${s['price']}\n"
                    f"Signal: {s['signal']}\n"
                    f"Confidence: {s['confidence']}%\n"
                    f"🎯 Trigger: ${s['levels']['trigger']}\n"
                    f"✅ TP1: ${s['levels']['tp1']}\n"
                    f"✅ TP2: ${s['levels']['tp2']}\n"
                    f"✅ TP3: ${s['levels']['tp3']}\n"
                    f"❌ SL: ${s['levels']['sl']}\n"
                    f"⚖️ R:R 1:{s['levels']['rr']}\n\n"
                )
            await context.bot.send_message(chat_id=chat_id, text=message)
        except:
            continue

@admin_only
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global broadcast_active, broadcast_chat_ids

    if not context.args:
        status = "🟢 ON" if broadcast_active else "🔴 OFF"
        await update.message.reply_text(
            f"📡 Broadcast Status: {status}\n"
            f"⏱ Interval: every {broadcast_interval} minutes\n\n"
            "Usage:\n"
            "/broadcast on — start broadcasting\n"
            "/broadcast off — stop broadcasting\n"
            "/broadcast status — check status"
        )
        return

    action = context.args[0].lower()

    if action == "on":
        broadcast_active = True
        broadcast_chat_ids.add(update.effective_chat.id)
        await update.message.reply_text(
            f"✅ Auto broadcaster started!\n"
            f"⏱ Scanning every {broadcast_interval} minutes\n"
            f"📊 Only signals with 75%+ confidence will be sent\n"
            f"Markets: Crypto, Forex, Stocks, Indices, Futures"
        )

    elif action == "off":
        broadcast_active = False
        await update.message.reply_text("🔴 Auto broadcaster stopped.")

    elif action == "status":
        status = "🟢 ON" if broadcast_active else "🔴 OFF"
        chats = len(broadcast_chat_ids)
        await update.message.reply_text(
            f"📡 Broadcast: {status}\n"
            f"⏱ Interval: every {broadcast_interval} minutes\n"
            f"👥 Active chats: {chats}"
        )
    else:
        await update.message.reply_text("❌ Invalid option. Use: on, off, or status")

@admin_only
async def setinterval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global broadcast_interval
    if not context.args:
        await update.message.reply_text(
            f"Current interval: {broadcast_interval} minutes\n\n"
            "Usage: /setinterval [minutes]\n"
            "Example: /setinterval 15\n"
            "Min: 5 minutes | Max: 1440 minutes (24h)"
        )
        return

    try:
        minutes = int(context.args[0])
    except:
        await update.message.reply_text("❌ Invalid number.")
        return

    if minutes < 5:
        await update.message.reply_text("❌ Minimum interval is 5 minutes.")
        return
    if minutes > 1440:
        await update.message.reply_text("❌ Maximum interval is 1440 minutes (24 hours).")
        return

    broadcast_interval = minutes
    await update.message.reply_text(
        f"✅ Broadcast interval updated to {broadcast_interval} minutes."
    )
    # ==========================================
# ERROR HANDLER
# ==========================================
async def error_handler(update, context):
    error = context.error
    if "TimedOut" in str(type(error)) or "NetworkError" in str(type(error)):
        return  # Silently ignore network errors
    print(f"Error: {error}")
    # ==========================================
# STARTUP DATA LOADER
# ==========================================
def initialize_data():
    global paper_portfolios, watchlists, alerts

    # Load portfolios
    for record in portfolios_col.find():
        user_id = record.get("user_id")
        paper_portfolios[user_id] = {
            "balance": record.get("balance", 10000.0),
            "trades": record.get("trades", []),
            "positions": record.get("positions", {})
        }

    # Load watchlists
    for record in watchlists_col.find():
        user_id = record.get("user_id")
        watchlists[user_id] = record.get("symbols", [])

    # Load alerts
    for record in alerts_col.find():
        user_id = record.get("user_id")
        alerts[user_id] = record.get("alerts", [])

    print(f"✅ Data loaded — {len(paper_portfolios)} portfolios, {len(watchlists)} watchlists, {len(alerts)} alert sets")
# ==========================================
# MAIN
# ==========================================
if __name__ == "__main__":
    print("Bot is starting...")
    initialize_data()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    "👑 Admin Commands:\n"
    "/adduser - Add a user\n"
    "/removeuser - Remove a user\n"
    "/listusers - View all users\n\n"
    "/addadmin - Add an admin (owner only)\n"
    "/removeadmin - Remove an admin (owner only)\n"
    "/broadcast - Start/stop auto signals\n"
    "/setinterval - Set broadcast interval\n"
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("analyze", analyze))
    app.add_handler(CommandHandler("signal", signal))
    app.add_handler(CommandHandler("crypto", crypto))
    app.add_handler(CommandHandler("stocks", stocks))
    app.add_handler(CommandHandler("forex", forex))
    app.add_handler(CommandHandler("futures", futures))
    app.add_handler(CommandHandler("indices", indices))
    app.add_handler(CommandHandler("trade", trade))
    app.add_handler(CommandHandler("portfolio", portfolio))
    app.add_handler(CommandHandler("performance", performance))
    app.add_handler(CommandHandler("watchlist", watchlist))
    app.add_handler(CommandHandler("alert", alert))
    app.add_handler(CommandHandler("screener", screener))
    app.add_handler(CommandHandler("sentiment", sentiment))
    app.add_handler(CommandHandler("news", news))
    app.add_handler(CommandHandler("rugcheck", rugcheck))
    app.add_handler(CommandHandler("addadmin", addadmin))
    app.add_handler(CommandHandler("removeadmin", removeadmin))
    app.add_handler(CommandHandler("adduser", adduser))
    app.add_handler(CommandHandler("removeuser", removeuser))
    app.add_handler(CommandHandler("listusers", listusers))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("setinterval", setinterval))
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("viewalerts", viewalerts))
    app.add_handler(CommandHandler("resetportfolio", resetportfolio))
    print("Bot is running! Press Ctrl+C to stop.")
    app.job_queue.run_repeating(check_alerts, interval=60, first=10)
    app.job_queue.run_repeating(run_broadcast, interval=broadcast_interval * 60, first=30)
    app.run_polling()