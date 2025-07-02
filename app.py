import streamlit as st
import requests

# Optional: enable auto-refresh every 15 seconds
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=15 * 1000, limit=None, key="refresh")

st.set_page_config(page_title="Eye.See.V1 Trial Version Made by Melosh", layout="wide")
st.title("Eye.See.V1 Trial Version Made by Melosh")

# Backend API URL
BACKEND_URL = "https://wallet-tracker-tdsa.onrender.com"

# UI Inputs
wallets_input = st.text_area("Enter wallet addresses (comma-separated)", height=100)
min_amount = st.number_input("Minimum USD Amount", value=20.0)
min_mcap = st.number_input("Minimum Market Cap", value=100000.0)
min_volume = st.number_input("Minimum Volume", value=10000.0)
min_liquidity = st.number_input("Minimum Liquidity", value=10000.0)
min_age = st.number_input("Minimum Age (minutes)", value=0)
max_age = st.number_input("Maximum Age (minutes)", value=1440)
transaction_type = st.selectbox("Transaction Type", ["All", "Buys", "Sells"])
sound_alert = st.checkbox("🔔 Sound Alert", value=False)

# Initialize session state
if "monitoring" not in st.session_state:
    st.session_state.monitoring = False

# Start / Stop buttons
col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 Start Monitoring"):
        wallets = [w.strip() for w in wallets_input.split(",") if w.strip()]
        filters = {
            "amount": min_amount,
            "mcap": min_mcap,
            "volume": min_volume,
            "liquidity": min_liquidity,
            "age_min": min_age,
            "age_max": max_age,
            "tx_type": transaction_type,
            "sound_alert": sound_alert
        }
        try:
            r = requests.post(f"{BACKEND_URL}/api/start", json={"wallets": wallets, "filters": filters})
            if r.status_code == 200:
                st.success("✅ Monitoring started!")
                st.session_state.monitoring = True
            else:
                st.error(f"❌ Failed to start monitoring. Code: {r.status_code}")
        except Exception as e:
            st.error(f"Server connection error: {e}")

with col2:
    if st.button("🛑 Stop Monitoring"):
        try:
            requests.post(f"{BACKEND_URL}/api/stop")
            st.warning("🛑 Monitoring stopped.")
            st.session_state.monitoring = False
        except:
            st.error("Server connection error.")

st.markdown("---")
st.subheader("📢 Live Logs")

if st.session_state.monitoring:
    placeholder = st.empty()
    logs = []
    try:
        logs = requests.get(f"{BACKEND_URL}/api/logs").json()
    except:
        st.error("Server not running or connection error.")

    with placeholder.container():
        for log in reversed(logs):
            st.markdown(f"""
            **[{log['timestamp']}] {log['type']}**: {log['amount']} | Token: `{log['token']}`  
            💰 Market Cap: {log['market_cap']} | 📊 Volume: {log['volume']} | 💧 Liquidity: {log['liquidity']} | Age: {log['age']}  
            🔍 Wallet Address: `{log['wallet']}`  
            🪙 Token Address: `{log.get('token_address', 'N/A')}`  
            🔗 [View on DexScreener](https://dexscreener.com/solana/{log.get('token_address', '')})
            """, unsafe_allow_html=True)
