from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import json
import time

# Insert original logic (minus GUI launch)
import customtkinter as ctk
import tkinter as tk
from tkinter import scrolledtext
import json
import requests
import threading
import time
from datetime import datetime, timezone
import webbrowser
import winsound

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

API_KEY = "b7489c69-013c-4885-8dbe-58c175357521"
API_URL = "https://api.helius.xyz/v0/addresses/{wallet}/transactions?api-key=" + API_KEY
DEXSCREENER_URL = "https://api.dexscreener.com/latest/dex/search?q="
WALLETS_FILE = "wallets.json"
LAST_TX_FILE = "last_transactions.json"  # New file to store last transaction signatures
TOKEN_CACHE = {}

# Known stablecoin addresses for USD value calculation
STABLECOINS = {
    'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v': 'USDC',  # USDC
    'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB': 'USDT',   # USDT
    'So11111111111111111111111111111111111111112': 'SOL'       # Wrapped SOL
}

class WalletTrackerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("EYE.SEE.v1.1 Solana Wallet Tracker")
        self.geometry("1000x800")
        self.wallets = self.load_wallets()
        self.running = False
        self.last_tx = self.load_last_transactions()  # Load last transaction signatures
        self.muted_wallets = []  # Track muted wallets

        # --- Begin scrollable main area setup ---
        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)
        self.main_canvas = tk.Canvas(self.container, borderwidth=0, background="#222222", highlightthickness=0)
        self.v_scrollbar = tk.Scrollbar(self.container, orient="vertical", command=self.main_canvas.yview)
        self.main_canvas.configure(yscrollcommand=self.v_scrollbar.set)
        self.main_canvas.pack(side="left", fill="both", expand=True)
        self.v_scrollbar.pack(side="left", fill="y")

        # Create a frame inside the canvas to hold all widgets
        self.content_frame = ctk.CTkFrame(self.main_canvas)
        self.content_frame.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        )
        self.content_window = self.main_canvas.create_window((0, 0), window=self.content_frame, anchor="nw")

        # Mousewheel scrolling
        def _on_mousewheel(event):
            self.main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.main_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # --- Place all widgets inside content_frame instead of self ---
        self.sidebar = ctk.CTkFrame(self.content_frame, width=250)
        self.sidebar.pack(side="left", fill="y")

        # Single wallet input
        self.wallet_entry = ctk.CTkEntry(self.sidebar, placeholder_text="Enter wallet address")
        self.wallet_entry.pack(pady=10, padx=10)

        self.add_btn = ctk.CTkButton(self.sidebar, text="Add Wallet", command=self.add_wallet)
        self.add_btn.pack(pady=2)

        # Bulk wallet input section
        bulk_label = ctk.CTkLabel(self.sidebar, text="Bulk Add Wallets:")
        bulk_label.pack(pady=(15, 5), padx=10)
        bulk_help = ctk.CTkLabel(self.sidebar, text="(Paste addresses separated by commas)", font=("Arial", 9))
        bulk_help.pack(pady=(0, 5), padx=10)
        self.bulk_entry = ctk.CTkTextbox(self.sidebar, height=60)
        self.bulk_entry.pack(pady=5, padx=10, fill="x")
        self.bulk_add_btn = ctk.CTkButton(self.sidebar, text="Add Bulk Wallets", command=self.add_bulk_wallets)
        self.bulk_add_btn.pack(pady=2)
        self.wallet_listbox = tk.Listbox(self.sidebar, height=8)
        self.wallet_listbox.pack(padx=10, pady=10, fill="both", expand=True)
        self.refresh_wallet_list()
        self.remove_btn = ctk.CTkButton(self.sidebar, text="Remove Selected", command=self.remove_wallet)
        self.remove_btn.pack(pady=2)
        self.mute_btn = ctk.CTkButton(self.sidebar, text="Mute/Unmute Selected", command=self.toggle_mute_wallet)
        self.mute_btn.pack(pady=2)
        self.clear_all_btn = ctk.CTkButton(self.sidebar, text="Clear All Wallets", command=self.clear_all_wallets)
        self.clear_all_btn.pack(pady=2)
        self.clear_cache_btn = ctk.CTkButton(self.sidebar, text="Clear Token Cache", command=self.clear_token_cache)
        self.clear_cache_btn.pack(pady=2)
        filter_label = ctk.CTkLabel(self.sidebar, text="--- FILTERS ---", font=("Arial", 12, "bold"))
        filter_label.pack(pady=(15, 5))
        self.enable_filters = ctk.CTkCheckBox(self.sidebar, text="Enable Filters")
        self.enable_filters.pack(pady=5)
        self.sol_filter = ctk.CTkEntry(self.sidebar, placeholder_text="Min USD amount (e.g., 20)")
        self.sol_filter.pack(pady=2, padx=10)
        self.marketcap_filter = ctk.CTkEntry(self.sidebar, placeholder_text="Min Market Cap (e.g., 100000)")
        self.marketcap_filter.pack(pady=2, padx=10)
        self.volume_filter = ctk.CTkEntry(self.sidebar, placeholder_text="Min Volume (e.g., 10000)")
        self.volume_filter.pack(pady=2, padx=10)
        self.liquidity_filter = ctk.CTkEntry(self.sidebar, placeholder_text="Min Liquidity (e.g., 10000)")
        self.liquidity_filter.pack(pady=2, padx=10)
        self.age_min_filter = ctk.CTkEntry(self.sidebar, placeholder_text="Min Age (minutes)")
        self.age_min_filter.pack(pady=2, padx=10)
        self.age_max_filter = ctk.CTkEntry(self.sidebar, placeholder_text="Max Age (minutes)")
        self.age_max_filter.pack(pady=2, padx=10)
        self.tx_filter = ctk.CTkComboBox(self.sidebar, values=["All", "Buys", "Sells"])
        self.tx_filter.set("All")
        self.tx_filter.pack(pady=2, padx=10)
        self.sound_alert = ctk.CTkCheckBox(self.sidebar, text="🔔 Sound Alert")
        self.sound_alert.pack(pady=10)
        self.start_btn = ctk.CTkButton(self.sidebar, text="Start Monitoring", command=self.toggle_monitoring)
        self.start_btn.pack(pady=10)

        self.log_box = scrolledtext.ScrolledText(self.content_frame, wrap=tk.WORD, font=("Consolas", 13), bg="black", fg="white")
        self.log_box.pack(fill="both", expand=True, padx=10, pady=10)
        self.log_box.tag_config("green", foreground="lime")
        self.log_box.tag_config("red", foreground="red")
        self.log_box.tag_config("white", foreground="white")
        self.log_box.tag_config("link", foreground="cyan", underline=True)

        self.footer = ctk.CTkLabel(self.content_frame, text="Made by Melosh | Fixed Version - Shows ALL transactions unless filters enabled", font=("Arial", 10))
        self.footer.pack(side="bottom", pady=5)

        # Make content_frame expand horizontally with the canvas
        def _resize_content(event):
            canvas_width = event.width
            self.main_canvas.itemconfig(self.content_window, width=canvas_width)
        self.main_canvas.bind("<Configure>", _resize_content)

    def load_wallets(self):
        try:
            with open(WALLETS_FILE, "r") as f:
                return json.load(f)
        except:
            return []

    def save_wallets(self):
        with open(WALLETS_FILE, "w") as f:
            json.dump(self.wallets, f)

    def load_last_transactions(self):
        """Load the last transaction signatures from file"""
        try:
            with open(LAST_TX_FILE, "r") as f:
                return json.load(f)
        except:
            return {}

    def save_last_transactions(self):
        """Save the last transaction signatures to file"""
        with open(LAST_TX_FILE, "w") as f:
            json.dump(self.last_tx, f)

    def refresh_wallet_list(self):
        self.wallet_listbox.delete(0, tk.END)
        for w in self.wallets:
            # Show shortened wallet address for better display
            display_wallet = f"{w[:8]}...{w[-8:]}" if len(w) > 20 else w
            # Add mute indicator
            if w in self.muted_wallets:
                display_wallet = f"🔇 {display_wallet}"
            self.wallet_listbox.insert(tk.END, display_wallet)

    def add_wallet(self):
        wallet = self.wallet_entry.get().strip()
        if wallet and wallet not in self.wallets:
            self.wallets.append(wallet)
            self.save_wallets()
            self.refresh_wallet_list()
            self.wallet_entry.delete(0, tk.END)
            self.log(f"Added wallet: {wallet[:8]}...{wallet[-8:]}")

    def add_bulk_wallets(self):
        bulk_text = self.bulk_entry.get("1.0", tk.END).strip()
        if not bulk_text:
            return
        
        # Split by commas and clean up
        wallet_addresses = [addr.strip() for addr in bulk_text.replace('\n', ',').split(',') if addr.strip()]
        
        added_count = 0
        for wallet in wallet_addresses:
            if wallet and len(wallet) > 20 and wallet not in self.wallets:  # Basic validation
                self.wallets.append(wallet)
                added_count += 1
        
        if added_count > 0:
            self.save_wallets()
            self.refresh_wallet_list()
            self.bulk_entry.delete("1.0", tk.END)
            self.log(f"Bulk added {added_count} wallets")
        else:
            self.log("No valid new wallets found in bulk input")

    def remove_wallet(self):
        selected = self.wallet_listbox.curselection()
        if selected:
            wallet_index = selected[0]
            removed_wallet = self.wallets[wallet_index]
            self.wallets.remove(removed_wallet)
            self.save_wallets()
            self.refresh_wallet_list()
            self.log(f"Removed wallet: {removed_wallet[:8]}...{removed_wallet[-8:]}")

    def clear_token_cache(self):
        global TOKEN_CACHE
        cache_size = len(TOKEN_CACHE)
        TOKEN_CACHE.clear()
        self.log(f"Cleared token cache ({cache_size} tokens)")

    def clear_all_wallets(self):
        if self.wallets:
            count = len(self.wallets)
            self.wallets.clear()
            self.save_wallets()
            self.refresh_wallet_list()
            self.log(f"Cleared all {count} wallets")

    def toggle_monitoring(self):
        if not self.running:
            if not self.wallets:
                self.log("No wallets to monitor! Please add some wallets first.")
                return
            self.running = True
            self.start_btn.configure(text="Stop Monitoring")
            self.log(f"Started monitoring {len(self.wallets)} wallets...")
            threading.Thread(target=self.monitor_wallets, daemon=True).start()
        else:
            self.running = False
            self.start_btn.configure(text="Start Monitoring")
            self.log("Stopped monitoring")

    def fetch_token_info(self, token_address):
        if token_address in TOKEN_CACHE:
            return TOKEN_CACHE[token_address]
        
        print(f"DEBUG: Fetching token info for {token_address}")
        
        # Method 1: Try DexScreener search by token address
        try:
            r = requests.get(DEXSCREENER_URL + token_address, timeout=10)
            data = r.json()
            pairs = data.get("pairs", [])
            
            if pairs:
                # Find the best pair (highest liquidity)
                best = max(pairs, key=lambda p: p.get("liquidity", {}).get("usd", 0) or 0)
                
                name = best.get("baseToken", {}).get("name", "Unknown")
                symbol = best.get("baseToken", {}).get("symbol", "")
                market_cap = best.get("marketCap", 0) or 0
                liquidity = best.get("liquidity", {}).get("usd", 0) or 0
                volume = best.get("volume", {}).get("h24", 0) or 0
                price_usd = float(best.get("priceUsd", 0) or 0)
                
                # Calculate age
                ts = best.get("pairCreatedAt")
                age_str = "?"
                age_minutes = 999999
                if ts:
                    created_at = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                    now = datetime.now(timezone.utc)
                    age = now - created_at
                    age_minutes = age.total_seconds() / 60
                    
                    if age.days >= 365:
                        age_str = f"{age.days // 365} years"
                    elif age.days >= 1:
                        age_str = f"{age.days} days {age.seconds // 3600 % 24} hours"
                    elif age.seconds >= 3600:
                        age_str = f"{age.seconds // 3600} hours"
                    elif age.seconds >= 60:
                        age_str = f"{age.seconds // 60} minutes"
                    else:
                        age_str = f"{age.seconds} seconds"
                
                display_name = f"{name} ({symbol})" if symbol and symbol != name else name
                print(f"DEBUG: DexScreener Method 1 - Found token info - Name: {display_name}, Price: ${price_usd}, MC: ${market_cap}, Liq: ${liquidity}, Age: {age_str}")
                
                TOKEN_CACHE[token_address] = (display_name, age_str, market_cap, liquidity, volume, age_minutes, price_usd)
                return TOKEN_CACHE[token_address]
            else:
                print(f"DEBUG: DexScreener Method 1 - No trading pairs found for {token_address}")
                
        except Exception as e:
            print(f"DEBUG: DexScreener Method 1 failed for {token_address}: {e}")
        
        # Method 2: Try DexScreener tokens endpoint directly
        try:
            dex_tokens_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            r = requests.get(dex_tokens_url, timeout=10)
            data = r.json()
            pairs = data.get("pairs", [])
            
            if pairs:
                # Find the best pair (highest liquidity)
                best = max(pairs, key=lambda p: p.get("liquidity", {}).get("usd", 0) or 0)
                
                name = best.get("baseToken", {}).get("name", "Unknown")
                symbol = best.get("baseToken", {}).get("symbol", "")
                market_cap = best.get("marketCap", 0) or 0
                liquidity = best.get("liquidity", {}).get("usd", 0) or 0
                volume = best.get("volume", {}).get("h24", 0) or 0
                price_usd = float(best.get("priceUsd", 0) or 0)
                
                # Calculate age
                ts = best.get("pairCreatedAt")
                age_str = "?"
                age_minutes = 999999
                if ts:
                    created_at = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                    now = datetime.now(timezone.utc)
                    age = now - created_at
                    age_minutes = age.total_seconds() / 60
                    
                    if age.days >= 365:
                        age_str = f"{age.days // 365} years"
                    elif age.days >= 1:
                        age_str = f"{age.days} days {age.seconds // 3600 % 24} hours"
                    elif age.seconds >= 3600:
                        age_str = f"{age.seconds // 3600} hours"
                    elif age.seconds >= 60:
                        age_str = f"{age.seconds // 60} minutes"
                    else:
                        age_str = f"{age.seconds} seconds"
                
                display_name = f"{name} ({symbol})" if symbol and symbol != name else name
                print(f"DEBUG: DexScreener Method 2 - Found token info - Name: {display_name}, Price: ${price_usd}, MC: ${market_cap}, Liq: ${liquidity}, Age: {age_str}")
                
                TOKEN_CACHE[token_address] = (display_name, age_str, market_cap, liquidity, volume, age_minutes, price_usd)
                return TOKEN_CACHE[token_address]
            else:
                print(f"DEBUG: DexScreener Method 2 - No trading pairs found for {token_address}")
                
        except Exception as e:
            print(f"DEBUG: DexScreener Method 2 failed for {token_address}: {e}")
        
        # Method 3: Try getting token name from Solana RPC and retry with symbol
        try:
            # Get token metadata from Solana
            rpc_url = "https://api.mainnet-beta.solana.com"
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAccountInfo",
                "params": [
                    token_address,
                    {"encoding": "jsonParsed"}
                ]
            }
            response = requests.post(rpc_url, json=payload, timeout=10)
            data = response.json()
            
            if 'result' in data and data['result'] and data['result']['value']:
                account_data = data['result']['value']['data']
                if account_data.get('parsed'):
                    token_info = account_data['parsed']['info']
                    print(f"DEBUG: Got token info from RPC: {token_info}")
                    
                    # Try searching by symbol if available
                    if token_info.get('symbol'):
                        symbol = token_info['symbol']
                        print(f"DEBUG: Trying DexScreener search with symbol: {symbol}")
                        
                        r = requests.get(DEXSCREENER_URL + symbol, timeout=10)
                        search_data = r.json()
                        pairs = search_data.get("pairs", [])
                        
                        # Find pairs that match our token address
                        matching_pairs = [p for p in pairs if p.get("baseToken", {}).get("address") == token_address]
                        
                        if matching_pairs:
                            best = max(matching_pairs, key=lambda p: p.get("liquidity", {}).get("usd", 0) or 0)
                            
                            name = best.get("baseToken", {}).get("name", token_info.get('name', 'Unknown'))
                            symbol = best.get("baseToken", {}).get("symbol", symbol)
                            market_cap = best.get("marketCap", 0) or 0
                            liquidity = best.get("liquidity", {}).get("usd", 0) or 0
                            volume = best.get("volume", {}).get("h24", 0) or 0
                            price_usd = float(best.get("priceUsd", 0) or 0)
                            
                            # Calculate age
                            ts = best.get("pairCreatedAt")
                            age_str = "?"
                            age_minutes = 999999
                            if ts:
                                created_at = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                                now = datetime.now(timezone.utc)
                                age = now - created_at
                                age_minutes = age.total_seconds() / 60
                                
                                if age.days >= 365:
                                    age_str = f"{age.days // 365} years"
                                elif age.days >= 1:
                                    age_str = f"{age.days} days {age.seconds // 3600 % 24} hours"
                                elif age.seconds >= 3600:
                                    age_str = f"{age.seconds // 3600} hours"
                                elif age.seconds >= 60:
                                    age_str = f"{age.seconds // 60} minutes"
                                else:
                                    age_str = f"{age.seconds} seconds"
                            
                            display_name = f"{name} ({symbol})" if symbol and symbol != name else name
                            print(f"DEBUG: DexScreener Method 3 - Found token info via symbol search - Name: {display_name}, Price: ${price_usd}, MC: ${market_cap}, Liq: ${liquidity}, Age: {age_str}")
                            
                            TOKEN_CACHE[token_address] = (display_name, age_str, market_cap, liquidity, volume, age_minutes, price_usd)
                            return TOKEN_CACHE[token_address]
                
        except Exception as e:
            print(f"DEBUG: Method 3 (RPC + symbol search) failed for {token_address}: {e}")
        
        # Method 4: Try Jupiter API as last resort
        try:
            jupiter_url = f"https://price.jup.ag/v4/price?ids={token_address}"
            r = requests.get(jupiter_url, timeout=10)
            data = r.json()
            
            if 'data' in data and token_address in data['data']:
                token_data = data['data'][token_address]
                price_usd = float(token_data.get('price', 0))
                
                if price_usd > 0:
                    print(f"DEBUG: Jupiter API - Found price ${price_usd} for {token_address}")
                    # We have price but no other data from Jupiter
                    TOKEN_CACHE[token_address] = (f"Token ({token_address[:8]}...{token_address[-4:]})", "?", 0, 0, 0, 999999, price_usd)
                    return TOKEN_CACHE[token_address]
                    
        except Exception as e:
            print(f"DEBUG: Jupiter API failed for {token_address}: {e}")
        
        # All methods failed - cache as unknown but still show the transaction
        print(f"DEBUG: All methods failed for {token_address}, caching as unknown")
        TOKEN_CACHE[token_address] = ("Unknown Token", "?", 0, 0, 0, 999999, 0)
        return TOKEN_CACHE[token_address]

    def get_token_decimals(self, token_address):
        """Get the correct decimal places for a token"""
        try:
            rpc_url = "https://api.mainnet-beta.solana.com"
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAccountInfo",
                "params": [
                    token_address,
                    {"encoding": "jsonParsed"}
                ]
            }
            response = requests.post(rpc_url, json=payload, timeout=5)
            data = response.json()
            
            if 'result' in data and data['result'] and data['result']['value']:
                decimals = data['result']['value']['data']['parsed']['info']['decimals']
                return decimals
        except:
            pass
        return 9  # Default to 9 if we can't determine

    def get_sol_price(self):
        """Get current SOL price in USD"""
        try:
            response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd", timeout=5)
            return response.json()['solana']['usd']
        except:
            return 200  # Default fallback price

    def format_usd_amount(self, amount):
        """Format USD amount to show precise values, especially for small amounts"""
        if amount >= 1:
            return f"${amount:,.2f}"
        elif amount >= 0.01:
            return f"${amount:.4f}"
        elif amount >= 0.001:
            return f"${amount:.6f}"
        elif amount >= 0.0001:
            return f"${amount:.8f}"
        else:
            # For very small amounts, use scientific notation or show many decimals
            if amount > 0:
                return f"${amount:.10f}".rstrip('0').rstrip('.')
            else:
                return "$0.00"

    def calculate_transaction_value(self, tx, token_transfer, wallet):
        """Calculate the actual USD value of the transaction"""
        try:
            token_address = token_transfer.get("mint")
            token_amount = token_transfer.get("tokenAmount", 0)
            
            print(f"DEBUG: Calculating value for token {token_address}")
            print(f"DEBUG: Raw token amount from API: {token_amount}")
            
            # Check if it's a stablecoin first
            if token_address in STABLECOINS:
                if STABLECOINS[token_address] in ['USDC', 'USDT']:
                    usd_value = token_amount / 1e6
                    print(f"DEBUG: Stablecoin detected, USD value: {usd_value}")
                    return usd_value
                elif STABLECOINS[token_address] == 'SOL':
                    sol_price = self.get_sol_price()
                    sol_amount = token_amount  # Don't divide by 1e9 - it's already in SOL units
                    usd_value = sol_amount * sol_price
                    print(f"DEBUG: SOL detected, USD value: {usd_value}")
                    return usd_value
            
            # For other tokens, get price from DexScreener
            token_name, age_str, market_cap, liquidity, volume, age_minutes, price_usd = self.fetch_token_info(token_address)
            
            if price_usd > 0:
                decimals = self.get_token_decimals(token_address)
                print(f"DEBUG: Token decimals: {decimals}")
                # The API already returns the correct token amount, don't divide by decimals
                actual_token_amount = token_amount  # Use raw amount directly
                print(f"DEBUG: Using raw token amount: {actual_token_amount}")
                usd_value = actual_token_amount * price_usd
                print(f"DEBUG: Token price: ${price_usd}, Amount: {actual_token_amount}, USD value: ${usd_value}")
                return usd_value
            
            # Try to estimate from other transfers in the same transaction
            print(f"DEBUG: No price found for {token_address}, checking transaction for value estimation")
            
            if 'tokenTransfers' in tx:
                for other_transfer in tx['tokenTransfers']:
                    other_mint = other_transfer.get('mint')
                    other_amount = other_transfer.get('tokenAmount', 0)
                    
                    if other_mint in STABLECOINS and STABLECOINS[other_mint] in ['USDC', 'USDT']:
                        other_from = other_transfer.get('fromUserAccount')
                        other_to = other_transfer.get('toUserAccount')
                        current_from = token_transfer.get('fromUserAccount')
                        current_to = token_transfer.get('toUserAccount')
                        
                        if ((current_from == wallet and other_to == wallet) or 
                            (current_to == wallet and other_from == wallet)):
                            stablecoin_value = other_amount / 1e6
                            print(f"DEBUG: Found matching stablecoin transfer worth ${stablecoin_value}")
                            return stablecoin_value
            
            # Fallback: check native SOL transfers
            sol_change = 0
            if 'nativeTransfers' in tx:
                for native_transfer in tx['nativeTransfers']:
                    if native_transfer['toUserAccount'] == wallet:
                        sol_change += native_transfer['amount'] / 1e9
                    elif native_transfer['fromUserAccount'] == wallet:
                        sol_change -= native_transfer['amount'] / 1e9
            
            if abs(sol_change) > 0.001:
                sol_price = self.get_sol_price()
                usd_value = abs(sol_change) * sol_price
                print(f"DEBUG: Using SOL fallback, USD value: {usd_value}")
                return usd_value
                
            print(f"DEBUG: Could not determine USD value for {token_address}")
            return 0  # Return 0 but still show the transaction
            
        except Exception as e:
            print(f"DEBUG: Error calculating transaction value: {e}")
            return 0  # Return 0 but still show the transaction

    def should_show_transaction(self, usd_amount, market_cap, liquidity, volume, age_minutes, is_buy):
        """Check if transaction should be shown based on filters"""
        # If filters are not enabled, show everything
        if not self.enable_filters.get():
            print(f"DEBUG: Filters disabled, showing transaction")
            return True
        
        try:
            min_amount = float(self.sol_filter.get().strip() or 0)
            min_mcap = float(self.marketcap_filter.get().strip() or 0)
            min_volume = float(self.volume_filter.get().strip() or 0)
            min_liquidity = float(self.liquidity_filter.get().strip() or 0)
            min_age = float(self.age_min_filter.get().strip() or 0)
            max_age = float(self.age_max_filter.get().strip() or 9999999)  # Increased max age
            
            print(f"DEBUG: Filter values - Min Amount: ${min_amount}, Min MC: ${min_mcap}, Min Vol: ${min_volume}, Min Liq: ${min_liquidity}, Age Range: {min_age}-{max_age}")
            print(f"DEBUG: Transaction values - Amount: ${usd_amount}, MC: ${market_cap}, Vol: ${volume}, Liq: ${liquidity}, Age: {age_minutes} min")
            
        except Exception as e:
            print(f"DEBUG: Error parsing filters: {e}")
            # If there's an error parsing filters, show everything
            return True
        
        # Apply filters with debug logging
        if usd_amount < min_amount:
            print(f"DEBUG: Filtered out - Amount ${usd_amount} < Min ${min_amount}")
            return False
        if market_cap < min_mcap:
            print(f"DEBUG: Filtered out - MC ${market_cap} < Min ${min_mcap}")
            return False
        if liquidity < min_liquidity:
            print(f"DEBUG: Filtered out - Liq ${liquidity} < Min ${min_liquidity}")
            return False
        if volume < min_volume:
            print(f"DEBUG: Filtered out - Vol ${volume} < Min ${min_volume}")
            return False
        
        # Age filtering - skip for SOL transactions (age_minutes will be very high for SOL)
        if age_minutes >= 1000000:  # SOL transaction - skip age filtering
            print(f"DEBUG: SOL transaction detected (age: {age_minutes}), skipping age filter")
        elif not (min_age <= age_minutes <= max_age):
            print(f"DEBUG: Filtered out - Age {age_minutes} not in range {min_age}-{max_age}")
            return False
        
        # Transaction type filter
        tx_filter = self.tx_filter.get()
        if tx_filter == "Buys" and not is_buy:
            print(f"DEBUG: Filtered out - Filter set to 'Buys' but transaction is 'SELL'")
            return False
        if tx_filter == "Sells" and is_buy:
            print(f"DEBUG: Filtered out - Filter set to 'Sells' but transaction is 'BUY'")
            return False
        
        print(f"DEBUG: Transaction PASSED all filters")
        return True

    def toggle_mute_wallet(self):
        selected = self.wallet_listbox.curselection()
        if selected:
            wallet_index = selected[0]
            wallet = self.wallets[wallet_index]
            
            if wallet in self.muted_wallets:
                # Unmute
                self.muted_wallets.remove(wallet)
                self.log(f"Unmuted wallet: {wallet[:8]}...{wallet[-8:]}")
            else:
                # Mute
                self.muted_wallets.append(wallet)
                self.log(f"Muted wallet: {wallet[:8]}...{wallet[-8:]}")
            
            self.refresh_wallet_list()

    def monitor_wallets(self):
        while self.running:
            for wallet in self.wallets:
                # Skip muted wallets
                if wallet in self.muted_wallets:
                    continue
                    
                try:
                    response = requests.get(API_URL.format(wallet=wallet), timeout=10)
                    if response.status_code != 200:
                        continue
                        
                    txs = response.json()
                    for tx in txs[:5]:  # Check last 5 transactions
                        sig = tx['signature']
                        if wallet not in self.last_tx or sig != self.last_tx[wallet]:
                            self.last_tx[wallet] = sig
                            self.save_last_transactions()  # Save the updated last transaction
                            self.process_tx(tx, wallet)
                except Exception as e:
                    self.log(f"Error fetching data for wallet {wallet[:8]}...{wallet[-8:]}: {str(e)[:100]}")
            for _ in range(15):
                if not self.running:
                    break
                time.sleep(1)

    def process_tx(self, tx, wallet):
        try:
            if not tx.get("tokenTransfers"):
                return
                
            print(f"DEBUG: Processing transaction {tx.get('signature', 'unknown')} for wallet {wallet}")
                
            for transfer in tx["tokenTransfers"]:
                token_address = transfer.get("mint")
                print(f"DEBUG: Processing token address: {token_address}")
                # Skip Wrapped SOL (wSOL) transactions
                if token_address == "So11111111111111111111111111111111111111112":
                    print(f"DEBUG: Skipping Wrapped SOL (wSOL) transaction for {wallet}")
                    continue
                destination = transfer.get("toUserAccount")
                source = transfer.get("fromUserAccount")
                is_buy = (destination == wallet)
                tx_type = "BUY" if is_buy else "SELL"

                # Calculate USD value
                usd_amount = self.calculate_transaction_value(tx, transfer, wallet)
                
                # Get token info
                token_name, age_str, market_cap, liquidity, volume, age_minutes, price_usd = self.fetch_token_info(token_address)
                
                # Check if we should show this transaction
                if not self.should_show_transaction(usd_amount, market_cap, liquidity, volume, age_minutes, is_buy):
                    print(f"DEBUG: Transaction filtered out")
                    continue

                # Transaction passed filters - log it!
                print(f"DEBUG: Transaction PASSED filters, logging to GUI")

                if self.sound_alert.get():
                    try:
                        winsound.Beep(1000, 300)
                    except:
                        pass  # Ignore sound errors

                ts = datetime.utcfromtimestamp(tx['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                
                # Use the new formatting function for precise USD amounts
                formatted_amount = self.format_usd_amount(usd_amount)
                
                # Structured log for frontend
                log_entry = {
                    "timestamp": ts,
                    "type": tx_type,
                    "amount": formatted_amount,
                    "token": token_name,
                    "market_cap": market_cap,
                    "volume": volume,
                    "liquidity": liquidity,
                    "age": age_str,
                    "wallet": wallet,
                    "token_address": token_address
                }
                custom_log(log_entry, is_structured=True)
                self.log_clickable_token(token_address)
                
        except Exception as e:
            print(f"DEBUG: TX processing error: {e}")
            self.log(f"TX processing error for wallet {wallet[:8]}...{wallet[-8:]}: {str(e)[:100]}")

    def log(self, text, is_buy=None):
        def update_log():
            self.log_box.configure(state='normal')
            color = 'green' if is_buy else 'red' if is_buy is not None else 'white'
            self.log_box.insert(tk.END, text + "\n", color)
            self.log_box.see(tk.END)
            self.log_box.configure(state='disabled')
        
        # Ensure GUI updates happen on main thread
        self.after(0, update_log)

    def log_clickable_token(self, token_address):
        def update_link():
            def open_link(event, token=token_address):
                url = f"https://dexscreener.com/solana/{token}"
                webbrowser.open_new_tab(url)

            self.log_box.configure(state='normal')
            start_index = self.log_box.index(tk.END)
            self.log_box.insert(tk.END, f"    ➔ View Token on DexScreener\n", "link")
            end_index = self.log_box.index(tk.END)
            self.log_box.tag_add("link", start_index, end_index)
            self.log_box.tag_bind("link", "<Button-1>", open_link)
            self.log_box.configure(state='disabled')
        
        self.after(0, update_link)



app = Flask(__name__)
CORS(app)

global_filters = {}
global_wallets = []
log_buffer = []

def custom_log(log, is_structured=False, is_buy=None):
    # Ensure all logs have the same structure for frontend compatibility
    base_log = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "type": "info",
        "amount": "",
        "token": "",
        "market_cap": 0,
        "volume": 0,
        "liquidity": 0,
        "age": "",
        "wallet": "",
        "token_address": ""
    }
    if is_structured:
        base_log.update(log)
        log_buffer.append(base_log)
    else:
        base_log["text"] = log
        if is_buy is not None:
            base_log["type"] = "buy" if is_buy else "sell"
        log_buffer.append(base_log)
    if len(log_buffer) > 100:
        log_buffer.pop(0)

WalletTrackerApp.log = lambda self, text, is_buy=None: custom_log(text, is_structured=False, is_buy=is_buy)

@app.route("/api/start", methods=["POST"])
def start_monitoring():
    global global_filters, global_wallets, app_instance
    data = request.json
    global_wallets = data.get("wallets", [])
    global_filters = data.get("filters", {})

    app_instance = WalletTrackerApp()
    app_instance.wallets = global_wallets

    app_instance.enable_filters.get = lambda: True
    app_instance.sol_filter.get = lambda: str(global_filters.get("amount", 0))
    app_instance.marketcap_filter.get = lambda: str(global_filters.get("mcap", 0))
    app_instance.volume_filter.get = lambda: str(global_filters.get("volume", 0))
    app_instance.liquidity_filter.get = lambda: str(global_filters.get("liquidity", 0))
    app_instance.age_min_filter.get = lambda: str(global_filters.get("age_min", 0))
    app_instance.age_max_filter.get = lambda: str(global_filters.get("age_max", 9999999))
    app_instance.tx_filter.get = lambda: global_filters.get("tx_type", "All")
    app_instance.sound_alert.get = lambda: global_filters.get("sound_alert", False)

    app_instance.running = True
    threading.Thread(target=app_instance.monitor_wallets, daemon=True).start()
    return jsonify({ "status": "started", "wallets": global_wallets })

@app.route("/api/stop", methods=["POST"])
def stop_monitoring():
    global app_instance
    app_instance.running = False
    return jsonify({ "status": "stopped" })

@app.route("/api/logs", methods=["GET"])
def get_logs():
    return jsonify(log_buffer)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
