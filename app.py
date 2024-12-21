import yfinance as yf
import time
import json
import logging
import signal
import sys
from dotenv import load_dotenv
import os
import ollama

load_dotenv()  # Load environment variables from .env file

def get_stock_price(ticker):
    stock = yf.Ticker(ticker)
    data = stock.history(period="1d")
    if not data.empty:
        return {
            "price": data['Close'].iloc[-1],
            "volume": data['Volume'].iloc[-1],
            "time": data.index[-1].strftime('%Y-%m-%d %H:%M:%S')
        }
    return None

def monitor_stock(ticker, update_interval=60):  # update_interval in seconds
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info(f"Starting real-time monitoring for {ticker}...")
    logging.info("Press Ctrl+C to stop monitoring.")
    
    def signal_handler(sig, frame):
        logging.info('Stopping monitoring...')
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    while True:
        try:
            stock_data = get_stock_price(ticker)
            if stock_data:
                prompt = (
                    f"The current data for {ticker}:\n"
                    f"Price: ${stock_data['price']:.2f}\n"
                    f"Volume: {stock_data['volume']:,.0f}\n"
                    f"Time: {stock_data['time']}"
                )
                
                response = ollama.chat(model="llama3.2:3b-instruct-fp16", 
                                     messages=[{"role": "user", "content": prompt}])
                assistant_response = response.model_dump_json(indent=2)
                assistant_message = json.loads(assistant_response)["message"]["content"]
                
                logging.info("\n" + "="*50)
                logging.info(f"Update Time: {stock_data['time']}")
                logging.info(f"Stock: {ticker}")
                logging.info(f"Price: ${stock_data['price']:.2f}")
                logging.info(f"Volume: {stock_data['volume']:,.0f}")
                logging.info("\nAI Analysis:")
                logging.info(assistant_message)
                logging.info("="*50 + "\n")
                
            time.sleep(update_interval)
        
        except json.JSONDecodeError as e:
            logging.error(f"JSON decoding error: {e}")
        except Exception as e:
            logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    ticker = os.getenv("STOCK_TICKER", "AAPL")
    update_interval = int(os.getenv("UPDATE_INTERVAL", 60))
    monitor_stock(ticker, update_interval)
