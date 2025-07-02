import streamlit as st
import requests

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
        requests.post("https://wallet-tracker-tdsa.onrender.com/api/start",
                      json={"wallets": wallets, "filters": filters})
        st.success("Monitoring started!")

with col2:
    if st.button("🛑 Stop Monitoring"):
        requests.post("https://wallet-tracker-tdsa.onrender.com/api/stop")
        st.warning("Monitoring stopped.")

st.markdown("---")
st.subheader("📢 Live Logs")

placeholder = st.empty()

# Initialize session state for logs if not already
if 'logs_data' not in st.session_state:
    st.session_state['logs_data'] = []

# Button to refresh logs
if st.button("🔄 Refresh Logs"):
    try:
        logs = requests.get("https://wallet-tracker-tdsa.onrender.com/api/logs").json()
        st.session_state['logs_data'] = logs if isinstance(logs, list) else []
    except Exception as e:
        st.error("Server not running or connection error.")

# Display logs from session state
with placeholder.container():
    logs_to_display = st.session_state.get('logs_data', [])
    if logs_to_display:
        for log in reversed(logs_to_display):
            ts = log.get('timestamp') or 'N/A'
            log_type = log.get('type') or 'N/A'
            if log.get('text'):
                desc = log.get('text')
            else:
                amount_val = log.get('amount')
                token_val = log.get('token')
                desc_amount = amount_val if (amount_val is not None and not (isinstance(amount_val, str) and amount_val == "")) else 'N/A'
                desc_token = token_val if (token_val is not None and not (isinstance(token_val, str) and token_val == "")) else 'N/A'
                desc = f"{desc_amount} | Token: `{desc_token}`"
            market_cap_val = log.get('market_cap', 'N/A')
            volume_val = log.get('volume', 'N/A')
            liquidity_val = log.get('liquidity', 'N/A')
            age_val = log.get('age')
            age_display = age_val if (age_val is not None and not (isinstance(age_val, str) and age_val == "")) else 'N/A'
            wallet_val = log.get('wallet')
            wallet_display = wallet_val if (wallet_val is not None and not (isinstance(wallet_val, str) and wallet_val == "")) else 'N/A'
            log_markdown = (f"**[{ts}] {log_type}**: {desc}  \n"
                            f"💰 Market Cap: {market_cap_val} | 📊 Volume: {volume_val} | 💧 Liquidity: {liquidity_val} | Age: {age_display}  \n"
                            f"🔍 Wallet Address: `{wallet_display}`")
            st.markdown(log_markdown)
            if log.get('token_address'):
                dexscreener_url = f"https://dexscreener.com/solana/{log['token_address']}"
                st.markdown(
                    f"🪙 Token Address: `{log['token_address']}`<br/>🔗 [View on DexScreener]({dexscreener_url})",
                    unsafe_allow_html=True
                )
    else:
        st.markdown("_No logs to display yet._")
