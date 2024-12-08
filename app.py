import yfinance as yf
import ollama

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

if __name__ == "__main__":
    ticker = input("Enter the stock ticker symbol (e.g., 'AAPL' for Apple Inc.): ")
    model_name = "stock-price-model"  # Replace with the actual model name
    response = ollama.chat(model_name, f"Get the current stock price for {ticker}")
    price = response.get('price', None)
    if price is not None:
        print(f"The current stock price of {ticker} is: {price}")
    else:
        print(f"Could not retrieve the stock price for {ticker}.")
