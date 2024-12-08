import yfinance as yf

def get_stock_price(ticker):
    """
    Get the current stock price for a given ticker using yfinance.
    
    Args:
        ticker (str): The stock ticker symbol (e.g., 'AAPL' for Apple Inc.).
    
    Returns:
        float: The current stock price.
    """
    stock = yf.Ticker(ticker)
    stock_info = stock.history(period="1d")
    if not stock_info.empty:
        return stock_info['Close'].iloc[-1]
    else:
        return None
