from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import requests
import json
import time
from datetime import datetime, timezone

API_KEY = "b7489c69-013c-4885-8dbe-58c175357521"
API_URL = "https://api.helius.xyz/v0/addresses/{wallet}/transactions?api-key=" + API_KEY
DEXSCREENER_URL = "https://api.dexscreener.com/latest/dex/search?q="
STABLECOINS = {
    'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v': 'USDC',
    'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB': 'USDT',
    'So11111111111111111111111111111111111111112': 'SOL'
}

app = Flask(__name__)
CORS(app)

log_buffer = []
global_wallets = []
global_filters = {}
running_flag = False

TOKEN_CACHE = {}

def log_entry(entry):
    if len(log_buffer) >= 100:
        log_buffer.pop(0)
    log_buffer.append(entry)

def fetch_token_info(token_address):
    if token_address in TOKEN_CACHE:
        return TOKEN_CACHE[token_address]

    try:
        r = requests.get(DEXSCREENER_URL + token_address, timeout=10)
        data = r.json()
        pairs = data.get("pairs", [])
        if pairs:
            best = max(pairs, key=lambda p: p.get("liquidity", {}).get("usd", 0) or 0)
            name = best.get("baseToken", {}).get("name", "Unknown")
            symbol = best.get("baseToken", {}).get("symbol", "")
            market_cap = best.get("marketCap", 0) or 0
            liquidity = best.get("liquidity", {}).get("usd", 0) or 0
            volume = best.get("volume", {}).get("h24", 0) or 0
            price_usd = float(best.get("priceUsd", 0) or 0)
            ts = best.get("pairCreatedAt")
            age_minutes = 999999
            age_str = "?"
            if ts:
                created_at = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                now = datetime.now(timezone.utc)
                age = now - created_at
                age_minutes = age.total_seconds() / 60
                age_str = f"{int(age_minutes)} minutes"
            TOKEN_CACHE[token_address] = (f"{name} ({symbol})", age_str, market_cap, liquidity, volume, age_minutes, price_usd)
            return TOKEN_CACHE[token_address]
    except:
        pass

    TOKEN_CACHE[token_address] = ("Unknown Token", "?", 0, 0, 0, 999999, 0)
    return TOKEN_CACHE[token_address]

def calculate_value(token_address, token_amount):
    if token_address in STABLECOINS:
        return token_amount / 1e6
    _, _, _, _, _, _, price = fetch_token_info(token_address)
    return token_amount * price

def should_show(tx_data):
    try:
        filters = global_filters
        return (
            tx_data['amount'] >= filters.get('amount', 0) and
            tx_data['market_cap'] >= filters.get('mcap', 0) and
            tx_data['liquidity'] >= filters.get('liquidity', 0) and
            tx_data['volume'] >= filters.get('volume', 0)
        )
    except:
        return True

def monitor_wallets():
    last_seen = {}
    while running_flag:
        for wallet in global_wallets:
            try:
                r = requests.get(API_URL.format(wallet=wallet), timeout=10)
                txs = r.json()
                for tx in txs[:5]:
                    sig = tx["signature"]
                    if last_seen.get(wallet) == sig:
                        continue
                    last_seen[wallet] = sig

                    for transfer in tx.get("tokenTransfers", []):
                        mint = transfer.get("mint")
                        amount = transfer.get("tokenAmount", 0)
                        direction = "BUY" if transfer.get("toUserAccount") == wallet else "SELL"
                        value = calculate_value(mint, amount)
                        name, age_str, mcap, liq, vol, age_min, price = fetch_token_info(mint)

                        entry = {
                            "timestamp": datetime.utcfromtimestamp(tx['timestamp']).strftime('%Y-%m-%d %H:%M:%S'),
                            "type": direction,
                            "amount": round(value, 4),
                            "token": name,
                            "market_cap": mcap,
                            "volume": vol,
                            "liquidity": liq,
                            "age": age_str,
                            "wallet": wallet,
                            "token_address": mint
                        }

                        if should_show(entry):
                            log_entry(entry)
            except Exception as e:
                log_entry({"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "type": "error", "text": str(e)})
        time.sleep(15)

@app.route("/api/start", methods=["POST"])
def start_monitoring():
    global global_wallets, global_filters, running_flag
    data = request.json
    global_wallets = data.get("wallets", [])
    global_filters = data.get("filters", {})
    running_flag = True
    threading.Thread(target=monitor_wallets, daemon=True).start()
    return jsonify({ "status": "started", "wallets": global_wallets })

@app.route("/api/stop", methods=["POST"])
def stop_monitoring():
    global running_flag
    running_flag = False
    return jsonify({ "status": "stopped" })

@app.route("/api/logs", methods=["GET"])
def get_logs():
    return jsonify(log_buffer)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
