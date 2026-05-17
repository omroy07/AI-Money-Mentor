import yfinance as yf

def get_stock_price(symbol):
    symbol = symbol.strip().upper()
    if "." not in symbol:
        symbol = symbol + ".NS"

    stock = yf.Ticker(symbol)
    hist = stock.history(period="5d")

    if hist.empty:
        return None

    return round(float(hist["Close"].iloc[-1]), 2)
