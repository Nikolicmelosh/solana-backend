
import streamlit as st
import requests
import time

st.set_page_config(page_title="Solana Wallet Tracker", layout="wide")

st.title("🧠 Solana Wallet Tracker SaaS")

wallets_input = st.text_area("Enter wallet addresses (comma-separated)", height=100)
min_amount = st.number_input("Minimum USD Amount", value=20.0)
min_mcap = st.number_input("Minimum Market Cap", value=100000.0)
min_volume = st.number_input("Minimum Volume", value=10000.0)
min_liquidity = st.number_input("Minimum Liquidity", value=10000.0)
min_age = st.number_input("Minimum Age (minutes)", value=0)
max_age = st.number_input("Maximum Age (minutes)", value=1440)

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
            "age_max": max_age
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
                🔍 Wallet: `{log['wallet']}`
                """)
    except:
        st.error("Server not running or connection error.")
    time.sleep(15)
