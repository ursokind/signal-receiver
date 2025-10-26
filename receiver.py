import os
import redis
import json
from flask import Flask, request, abort

app = Flask(__name__)

# This will get the REDIS_URL you set in your Railway variables
REDIS_URL = os.environ.get("REDIS_URL")
if not REDIS_URL:
    print("FATAL: REDIS_URL is not set. Check your Railway variables.")
    
try:
    # Connect to your Redis mailbox
    r = redis.from_url(REDIS_URL, decode_responses=True)
    r.ping() # Test the connection
    print("Successfully connected to Redis.")
except Exception as e:
    print(f"Error connecting to Redis: {e}")
    r = None

@app.route('/')
def health_check():
    # A simple page to check if the server is running
    return "Signal receiver is alive.", 200

@app.route('/webhook', methods=['POST'])
def webhook_listener():
    if not r:
        print("Error: No Redis connection.")
        abort(500, description="Redis connection is not available.")
        
    try:
        # 1. Get the raw text from the alert
        # (TradingView's alert() function sends raw text, not JSON)
        raw_data = request.get_data(as_text=True)
        if not raw_data:
            print("Received empty request")
            abort(400, "Request is empty.")
        
        try:
            # 2. Parse the raw text string into a Python dictionary
            data = json.loads(raw_data)
        except json.JSONDecodeError:
            print(f"Invalid JSON received: {raw_data}")
            abort(400, "Request is not valid JSON.")

        # 'data' is now: {"IDX:BUMI": "Red", "IDX:DEWA": "Green", ...}
        
        # Use a Redis pipeline for super-fast, efficient updates
        pipeline = r.pipeline()
        for ticker_with_prefix, color_from_tv in data.items():
            
            # 3. Strip "IDX:" prefix to get the simple ticker (e.g., "BUMI")
            simple_ticker = ticker_with_prefix.split(":")[-1] 
            
            # 4. Clean up the color (e.g., "green" -> "Green")
            final_color = color_from_tv.lower().capitalize()
            
            # 5. Save all 3 colors ("Green", "Red", "Yellow") to Redis
            pipeline.set(simple_ticker, final_color)
            print(f"Queueing update: {simple_ticker} -> {final_color}")
        
        # 6. Execute all updates at once
        pipeline.execute()
        
        print(f"SUCCESS: Updated {len(data)} tickers from one alert.")
        return "Signals received successfully", 200

    except Exception as e:
        print(f"An error occurred processing the webhook: {e}")
        abort(500, description="Internal server error.")


if __name__ == '__main__':
    # Railway will provide its own PORT environment variable
    port = int(os.environ.get('PORT', 5000))
    # '0.0.0.0' is required for it to be reachable within Railway's network
    app.run(host='0.0.0.0', port=port)