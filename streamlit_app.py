import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import yfinance as yf
import ollama
import time
import logging
import psutil
import threading
import queue
from datetime import datetime, timedelta
from functools import lru_cache

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stock_monitor.log'),
        logging.StreamHandler()
    ]
)

# Page config
st.set_page_config(
    page_title="Stock Monitor",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Functions
@lru_cache(maxsize=32)
def cached_stock_data(ticker, period='1d', interval='1m'):
    return yf.Ticker(ticker).history(period=period, interval=interval)

def get_stock_data(ticker, period='1d', interval='1m'):
    start_time = time.time()
    try:
        # Use cache with 5-minute expiry
        if 'last_fetch_time' not in st.session_state or \
           time.time() - st.session_state.last_fetch_time > 300:
            df = cached_stock_data(ticker, period, interval)
            st.session_state.last_fetch_time = time.time()
        else:
            df = st.session_state.get('last_data')
            
        logging.info(f"Fetched data for {ticker}: {len(df)} rows")
        if st.session_state.get('debug_mode'):
            st.sidebar.text(f"API Response Time: {time.time() - start_time:.2f}s")
        
        st.session_state.last_data = df
        return df
    except Exception as e:
        logging.error(f"Error fetching stock data: {e}")
        return None

def create_price_chart(df):
    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close']
        )
    )
    fig.update_layout(
        title='Stock Price Chart',
        yaxis_title='Price',
        xaxis_title='Time',
        template='plotly_dark'
    )
    return fig

def get_ai_analysis(ticker, price, volume, change):
    # Check cache first
    cache_key = f"{ticker}_{price}_{volume}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    result_queue = queue.Queue()
    
    def ai_call():
        try:
            prompt = f"""Analyze this stock data:
            Symbol: {ticker}
            Current Price: ${price:.2f}
            Volume: {volume:,}
            Price Change: {change:.2%}
            Provide a brief market analysis."""
            
            response = ollama.chat(
                model="llama3.2:3b-instruct-fp16",
                messages=[{"role": "user", "content": prompt}]
            )
            result_queue.put(response['message']['content'])
        except Exception as e:
            result_queue.put(f"AI Analysis error: {str(e)}")
    
    # Show progress
    progress_text = st.empty()
    progress_text.text("Getting AI Analysis...")
    
    # Start AI thread
    thread = threading.Thread(target=ai_call)
    thread.start()
    
    try:
        result = result_queue.get(timeout=30)
        # Cache successful response
        st.session_state[cache_key] = result
        progress_text.empty()
        return result
    except queue.Empty:
        progress_text.empty()
        return "AI Analysis timed out (30s). Using previous analysis if available."
    finally:
        thread.join(timeout=1)

def get_system_metrics():
    memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
    cpu = psutil.cpu_percent()
    return memory, cpu

def main():
    # Debug Mode Toggle
    with st.sidebar:
        st.title("⚙️ Controls")
        st.session_state.debug_mode = st.checkbox("Debug Mode", False)
        
        if st.session_state.debug_mode:
            st.subheader("Debug Information")
            memory, cpu = get_system_metrics()
            st.text(f"Memory Usage: {memory:.1f} MB")
            st.text(f"CPU Usage: {cpu}%")
            st.text(f"Last Update: {datetime.now().strftime('%H:%M:%S')}")

        ticker = st.text_input("Stock Symbol", "AAPL")
        update_interval = st.slider("Update Interval (sec)", 30, 300, 60)
        start_stop = st.toggle("Start Monitoring")

    # Main content
    st.title("📈 Stock Monitor with AI Analysis")
    
    if start_stop:
        placeholder = st.empty()
        
        while True:
            try:
                with placeholder.container():
                    # Get data
                    df = get_stock_data(ticker)
                    if df is not None:
                        # Layout
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            # Chart
                            st.plotly_chart(create_price_chart(df), use_container_width=True)
                        
                        with col2:
                            # Metrics
                            current_price = df['Close'].iloc[-1]
                            previous_price = df['Close'].iloc[-2]
                            price_change = (current_price - previous_price) / previous_price
                            
                            st.metric("Price", f"${current_price:.2f}", 
                                     f"{price_change:.2%}")
                            st.metric("Volume", f"{df['Volume'].iloc[-1]:,}")
                            
                            # AI Analysis
                            st.subheader("🤖 AI Analysis")
                            if st.button("Refresh Analysis"):
                                st.session_state.pop(f"{ticker}_{current_price}_{df['Volume'].iloc[-1]}", None)
                            analysis = get_ai_analysis(ticker, current_price, df['Volume'].iloc[-1], price_change)
                            st.write(analysis)
                
                time.sleep(update_interval)
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
                time.sleep(5)

if __name__ == "__main__":
    main()