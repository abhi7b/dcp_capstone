import os
import requests
import streamlit as st
import pandas as pd

# --- Settings ---
st.sidebar.header("Settings")
API_BASE_URL = st.sidebar.text_input(
    "API Base URL", 
    value=st.secrets.get("api_base_url", os.getenv("API_BASE_URL", "http://localhost:8000"))
)
API_KEY = st.sidebar.text_input(
    "API Key", 
    value=st.secrets.get("api_key", os.getenv("API_KEY", "")),
    type="password"
)

# HTTP headers for API calls
headers = {"X-API-Key": API_KEY} if API_KEY else {}

# --- App Title ---
st.title("Duke VC Insight Engine")
st.markdown("Use this app to search companies and founders via the Duke VC Insight Engine API.")

# --- Navigation ---
tab = st.sidebar.radio("Select Function", ["Company Search", "Founder Search"])

# --- Company Search ---
if tab == "Company Search":
    st.header("🔍 Company Search")
    company_name = st.text_input("Enter company name:")
    force_refresh = st.checkbox("Force refresh data", value=False, 
                              help="Check this to fetch fresh data from sources instead of using cached data")
    if st.button("Search Company"):
        if not company_name:
            st.error("Please enter a company name to search.")
        else:
            try:
                response = requests.get(
                    f"{API_BASE_URL}/api/company/search/{company_name}", 
                    headers=headers, 
                    params={"force_refresh": force_refresh}
                )
                response.raise_for_status()
                data = response.json()

                if isinstance(data, list):
                    df = pd.DataFrame(data)
                    st.dataframe(df)
                else:
                    st.json(data)
            except requests.exceptions.RequestException as e:
                st.error(f"API request failed: {e}")

# --- Founder Search ---
elif tab == "Founder Search":
    st.header("🔍 Founder Search")
    founder_name = st.text_input("Enter founder name:")
    force_refresh = st.checkbox("Force refresh data", value=False, 
                              help="Check this to fetch fresh data from sources instead of using cached data")
    if st.button("Search Founder"):
        if not founder_name:
            st.error("Please enter a founder name to search.")
        else:
            try:
                response = requests.get(
                    f"{API_BASE_URL}/api/founder/search/{founder_name}", 
                    headers=headers, 
                    params={"force_refresh": force_refresh}
                )
                response.raise_for_status()
                data = response.json()

                if isinstance(data, list):
                    df = pd.DataFrame(data)
                    st.dataframe(df)
                else:
                    st.json(data)
            except requests.exceptions.RequestException as e:
                st.error(f"API request failed: {e}")

# --- Instructions ---
st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Deployment:** Add this file to your project root and run `streamlit run streamlit_app.py`.\n"
    "Make sure to set `API_BASE_URL` and `API_KEY` in the Streamlit secrets or sidebar."
)