import streamlit as st
import requests
import time

st.set_page_config(page_title="Eye.See.V1 Trial Version Made by Melosh", layout="wide")

st.title("Eye.See.V1 Trial Version Made by Melosh")

wallets_input = st.text_area("Enter wallet addresses (comma-separated)", height=100)
min_amount = st.number_input("Minimum USD Amount", value=20.0)
min_mcap = st.number_input("Minimum Market Cap", value=100000.0)
min_volume = st.number_input("Minimum Volume", value=10000.0)
min_liquidity = st.number_input("Minimum Liquidity", value=10000.0)
min_age = st.number_input("Minimum Age (minutes)", value=0)
max_age = st.number_input("Maximum Age (minutes)", value=1440)

# Add transaction type filter
transaction_type = st.selectbox("Transaction Type", ["All", "Buys", "Sells"])

# Add sound alert toggle
sound_alert = st.checkbox("🔔 Sound Alert", value=False)

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
        requests.post("http://localhost:5000/api/start", json={"wallets": wallets, "filters": filters})
        st.success("Monitoring started!")

with col2:
    if st.button("🛑 Stop Monitoring"):
        requests.post("http://localhost:5000/api/stop")
        st.warning("Monitoring stopped.")

st.markdown("---")
st.subheader("📢 Live Logs")

placeholder = st.empty()

while True:
    try:
        logs = requests.get("http://localhost:5000/api/logs").json()
        with placeholder.container():
            for log in reversed(logs):
                st.markdown(f"""
                **[{log['timestamp']}] {log['type']}**: {log['amount']} | Token: `{log['token']}`  
                💰 Market Cap: {log['market_cap']} | 📊 Volume: {log['volume']} | 💧 Liquidity: {log['liquidity']} | Age: {log['age']}  
                🔍 Wallet Address: `{log['wallet']}`
                """)
                # Show token address and DexScreener link if available
                if log.get("token_address"):
                    dexscreener_url = f"https://dexscreener.com/solana/{log['token_address']}"
                    st.markdown(f"🪙 Token Address: `{log['token_address']}`<br/>🔗 [View on DexScreener]({dexscreener_url})", unsafe_allow_html=True)
    except:
        st.error("Server not running or connection error.")
    time.sleep(15)
