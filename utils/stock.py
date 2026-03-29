import yfinance as yf

def get_stock_price(symbol):
    try:
        # Clean input
        symbol = symbol.strip().upper()

        # Add .NS for Indian stocks if not present
        if "." not in symbol:
            symbol = symbol + ".NS"

        stock = yf.Ticker(symbol)
        hist = stock.history(period="5d")

        # Check if data exists
        if hist.empty:
            return {"error": "Invalid stock symbol or no data found"}

        price = hist["Close"].iloc[-1]

        return round(price, 2)

    except Exception as e:
        return {"error": str(e)}