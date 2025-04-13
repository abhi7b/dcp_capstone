import streamlit as st
import requests
from typing import Optional

# --- CONFIG ---
API_URL = "https://your-api-url.com/companies"  # Replace with deployed FastAPI endpoint
API_KEY = st.secrets["api_key"] if "api_key" in st.secrets else "YOUR_API_KEY_HERE"

# --- APP LAYOUT ---
st.set_page_config(page_title="VC Insight Explorer", layout="wide")
st.title("🚀 Duke VC Insight Explorer")
st.markdown("Search for Duke-affiliated startups and founders to assess VC potential.")

# --- SEARCH INPUT ---
search_query = st.text_input("🔍 Enter Company or Person Name")

# --- FUNCTION TO QUERY API ---
def query_api(name: str) -> Optional[dict]:
    try:
        headers = {"X-API-Key": API_KEY}
        response = requests.get(f"{API_URL}?name={name}", headers=headers)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            st.warning("Company or person not found.")
        else:
            st.error(f"Error {response.status_code}: {response.text}")
    except Exception as e:
        st.error(f"Request failed: {e}")
    return None

# --- DISPLAY RESULTS ---
if search_query:
    with st.spinner("Querying VC Insight Engine..."):
        result = query_api(search_query)

    if result:
        if result.get("excluded"):
            st.error("This entity is excluded from VC consideration (e.g., law firm, dental practice).")
        else:
            col1, col2 = st.columns([2, 1])
            with col1:
                st.subheader(result.get("name", "Unknown"))
                st.write(f"**Sector:** {result.get('sector', 'N/A')}")
                st.write(f"**Growth Score:** {result.get('vc_rank', 'N/A')} / 100")
                if result.get("currently_raising"):
                    st.success("Currently raising capital! Top priority.")
                else:
                    st.info("Not currently raising capital.")

            with col2:
                if st.button("Mark for Follow-Up"):
                    st.success("Saved for periodic review.")

        st.divider()
        st.caption("Powered by Duke DCP Capstone Project")
    else:
        st.error("No results returned from the API.")
