import yfinance as yf
import re
import time

STOCK_CACHE = {}
CACHE_EXPIRY = 600  # 10 minutes in seconds

def get_stock_price(symbol):
    try:
        # Clean input
        symbol = symbol.strip().upper()
        
        # Security sanitization check: only allow alphanumeric, dots, hyphens, and underscores
        if not symbol or not re.match(r"^[A-Z0-9.\-_]+$", symbol):
            return {"error": "Invalid stock symbol format"}

        now = time.time()
        if symbol in STOCK_CACHE:
            cached_res, timestamp = STOCK_CACHE[symbol]
            if now - timestamp < CACHE_EXPIRY:
                return cached_res

        # Try finding as is first (especially for global stocks like AAPL, MSFT)
        stock = yf.Ticker(symbol)
        hist = stock.history(period="30d")

        # If empty and no dot in symbol, try appending .NS for Indian stocks
        if hist.empty and "." not in symbol:
            symbol_ns = symbol + ".NS"
            stock = yf.Ticker(symbol_ns)
            hist = stock.history(period="30d")
            if not hist.empty:
                symbol = symbol_ns

        if hist.empty:
            return {"error": "Invalid stock symbol or no data found"}

        # Current Price
        price = hist["Close"].iloc[-1]

        # Format history for frontend charting
        history_data = []
        for idx, row in hist.iterrows():
            history_data.append({
                "date": idx.strftime("%Y-%m-%d"),
                "close": round(row["Close"], 2)
            })

        # Get metrics with safe fallbacks
        metrics = {
            "high_52w": "N/A",
            "low_52w": "N/A",
            "market_cap": "N/A",
            "pe_ratio": "N/A"
        }

        try:
            info = stock.info
            if info:
                metrics["high_52w"] = info.get("fiftyTwoWeekHigh", "N/A")
                metrics["low_52w"] = info.get("fiftyTwoWeekLow", "N/A")
                metrics["market_cap"] = info.get("marketCap", "N/A")
                metrics["pe_ratio"] = info.get("trailingPE", "N/A")
        except Exception as info_err:
            print(f"Info fetch failed for {symbol}: {info_err}")

        # Get news safely
        news_data = []
        try:
            news = stock.news
            if news:
                news_data = news
        except Exception:
            pass

        ret = {
            "symbol": symbol,
            "price": round(price, 2),
            "history": history_data,
            "metrics": metrics,
            "news": news_data
        }
        STOCK_CACHE[symbol] = (ret, time.time())
        return ret

    except Exception as e:
        return {"error": str(e)}
