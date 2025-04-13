import time
import logging
import requests

def fetch_btc_price():
    """Fetches the current Bitcoin price in USD from CoinGecko."""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        return data['bitcoin']['usd']
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching BTC price: {e}")
        return None
    except (KeyError, TypeError) as e:
        logging.error(f"Error parsing BTC price: {e}")
        return None

def calculate_trend(prices, time_window_minutes=1):
    """Calculates a simple trend ('Up', 'Down', 'Flat') based on price history."""
    if len(prices) < 2:
        return 'Flat'  # Not enough data to determine trend

    # Get the most recent price and the price from time_window_minutes ago
    recent_price = prices[-1]
    past_price = prices[0]

    if recent_price > past_price:
        return 'Up'
    elif recent_price < past_price:
        return 'Down'
    else:
        return 'Flat'

class MarketDataHandler:
    def __init__(self, time_window_minutes=1, fetch_interval_seconds=60):
        self.time_window_minutes = time_window_minutes
        self.fetch_interval_seconds = fetch_interval_seconds
        self.price_history = []
        self.last_fetch_time = 0
        self.trend = 'Flat'

    def update_market_data(self):
        """Fetches BTC price and updates price history and trend."""
        current_time = time.time()
        if current_time - self.last_fetch_time >= self.fetch_interval_seconds:
            price = fetch_btc_price()
            if price is not None:
                self.price_history.append(price)
                # Keep only prices within the time window
                self.price_history = self.price_history[-(self.time_window_minutes + 1):]
                self.trend = calculate_trend(self.price_history)
                self.last_fetch_time = current_time
                logging.debug(f"Market data updated: price={price}, trend={self.trend}")
            else:
                logging.warning("Failed to fetch BTC price, keeping previous trend.")
        else:
            logging.debug("Market data update skipped (within fetch interval).")

    def get_trend(self):
        """Returns the current market trend."""
        return self.trend

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    handler = MarketDataHandler()
    for _ in range(5):
        handler.update_market_data()
        print(f"Trend: {handler.get_trend()}")
        time.sleep(10)