
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import threading
import time

app = Flask(__name__)
CORS(app)

wallets = []
filters = {}
monitoring = False
log_data = []

@app.route("/api/start", methods=["POST"])
def start_monitoring():
    global monitoring, wallets, filters
    data = request.json
    wallets = data.get("wallets", [])
    filters = data.get("filters", {})
    monitoring = True
    threading.Thread(target=monitor_wallets, daemon=True).start()
    return jsonify({"status": "started", "wallets": wallets})

@app.route("/api/stop", methods=["POST"])
def stop_monitoring():
    global monitoring
    monitoring = False
    return jsonify({"status": "stopped"})

@app.route("/api/logs", methods=["GET"])
def get_logs():
    return jsonify(log_data[-100:])  # Return last 100 logs

def monitor_wallets():
    global monitoring, log_data
    while monitoring:
        for wallet in wallets:
            # Simulate tracking
            log_entry = {
                "wallet": wallet,
                "type": "BUY",
                "amount": "$123.45",
                "token": "TokenXYZ",
                "market_cap": "$1,000,000",
                "volume": "$50,000",
                "liquidity": "$30,000",
                "age": "5 mins",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            log_data.append(log_entry)
        time.sleep(10)

if __name__ == "__main__":
    app.run(debug=True)
