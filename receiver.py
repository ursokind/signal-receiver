import os
import redis
from flask import Flask, request, abort

app = Flask(__name__)

# This is the magic part:
# Railway will automatically find your Redis database in the same project
# and put its connection URL into an environment variable called "REDIS_URL".
REDIS_URL = os.environ.get("REDIS_URL")
if not REDIS_URL:
    print("FATAL: REDIS_URL is not set. Is Redis provisioned in this project?")
    # In a real app, you'd exit, but for deployment this is fine
    
try:
    # Connect to your Redis mailbox
    r = redis.from_url(REDIS_URL, decode_responses=True)
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
        data = request.json
        if not data:
            print("Received empty or non-JSON request")
            abort(400, description="Request must be JSON.")

        ticker = data.get('ticker')
        color = data.get('color')

        if not ticker or not color:
            print(f"Invalid data received: {data}")
            abort(400, description="Missing 'ticker' or 'color' in payload.")

        # This is the core logic:
        # It sets the 'ticker' (e.g., "BUMI") to the 'color' value (e.g., "Red")
        r.set(ticker, color)

        print(f"SUCCESS: Set {ticker} -> {color}")
        return "Signal received successfully", 200

    except Exception as e:
        print(f"An error occurred processing the webhook: {e}")
        abort(500, description="Internal server error.")


if __name__ == '__main__':
    # Railway will provide its own PORT environment variable
    port = int(os.environ.get('PORT', 5000))
    # '0.0.0.0' is required for it to be reachable within Railway's network
    app.run(host='0.0.0.0', port=port)