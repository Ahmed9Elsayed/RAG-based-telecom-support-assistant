



import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# =========================
# Configuration
# =========================
# API_URL = "http://127.0.0.1:8000/ask"
API_URL = "https://fading-legged-customary.ngrok-free.dev/ask"
SHEET_URL = "https://docs.google.com/spreadsheets/d/1-l1q85UCA9EN8r4NqJMOUIBstkckuMGFXuy_cU1U-4U/export?format=csv"

# Force wide layout and a custom title
st.set_page_config(page_title="NileTel Agent Workspace", page_icon="📡", layout="wide", initial_sidebar_state="expanded")

# =========================
# CUSTOM CSS BRANDING (Dark Mode Optimized)
# =========================
st.markdown("""
<style>
    /* Hide default Streamlit watermarks */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Dark mode friendly tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 15px;
        background-color: #1E1E2E; /* Dark elegant background instead of stark white */
        padding: 10px 15px;
        border-radius: 10px;
        border: 1px solid #333;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: transparent;
        border-radius: 5px;
        padding: 0px 20px;
        font-weight: 600;
        font-size: 16px;
        color: #A0A0B0; /* Light grey text for unselected tabs */
    }
    .stTabs [aria-selected="true"] {
        background-color: #004B87 !important; /* NileTel Corporate Blue */
        color: white !important;
    }
    
    /* Dashboard Metrics Styling */
    [data-testid="stMetricValue"] {
        font-size: 2.2rem;
        color: #4DA8DA; /* Lighter blue so it pops in dark mode */
    }
</style>
""", unsafe_allow_html=True)

# =========================
# SIDEBAR: Agent Profile
# =========================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2885/2885412.png", width=80)
    st.title("NileTel Portal")
    st.markdown("---")
    st.write("👤 **Agent:** Ahmed (ID: 4092)")
    st.write("🏢 **Dept:** Tier 1 Tech Support")
    st.write(f"📅 **Date:** {datetime.now().strftime('%Y-%m-%d')}")
    st.markdown("---")
    st.success("🟢 All Systems Operational")
    st.warning("⚠️ High Volume: Delta Region")
    st.markdown("---")
    st.caption("v2.2.0 | Authorized Personnel Only")

# =========================
# MAIN HEADER
# =========================
st.header("📡 NileTel AI Copilot")
st.markdown("Ask technical questions, troubleshoot connectivity, or escalate network issues directly to the NOC.")

# =========================
# UI Layout: Tabs
# =========================
tab1, tab2 = st.tabs(["💬 Technical Support Chat", "📊 NOC Ticket Dashboard"])

# =========================
# TAB 1: Chat Interface
# =========================
with tab1:
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "أهلاً بك يا بطل الدعم الفني! أنا مساعد NileTel الذكي. إزاي أقدر أساعدك في حل مشاكل العملاء النهاردة؟", "meta": None}
        ]

    # FIX: Wrap the chat history in a scrollable container with a fixed height.
    # This guarantees the input box stays anchored to the bottom!
    chat_container = st.container(height=500)

    # Render History inside the container
    with chat_container:
        for message in st.session_state.messages:
            avatar = "👤" if message["role"] == "user" else "🤖"
            with st.chat_message(message["role"], avatar=avatar):
                st.markdown(message["content"])
                
                if message.get("meta"):
                    with st.expander("🛠️ System Logs & Context"):
                        if message["meta"]["needs_action"] == "YES":
                            st.error("🚨 NOC Ticket Triggered via n8n")
                        else:
                            st.info("✅ Resolved locally by Copilot")
                        if message["meta"]["sources"]:
                            st.markdown("**Referenced Manuals:**")
                            for src in message["meta"]["sources"]:
                                st.caption(f"- {src}")

    # st.chat_input sits outside the container, naturally pinning beneath it
    if prompt := st.chat_input("Type your support query here... (Press Enter to send)"):
        
        # Save user message to state
        st.session_state.messages.append({"role": "user", "content": prompt, "meta": None})

        # Immediately render the new messages inside the scrollable container
        with chat_container:
            st.chat_message("user", avatar="👤").markdown(prompt)

            with st.spinner("Analyzing NileTel Knowledge Base... 🔍"):
                try:
                    response = requests.post(API_URL, json={"query": prompt})
                    if response.status_code == 200:
                        data = response.json()
                        answer = data["answer"]
                        meta = {"needs_action": data["needs_action"], "sources": data["sources"]}

                        with st.chat_message("assistant", avatar="🤖"):
                            st.markdown(answer)
                            with st.expander("🛠️ System Logs & Context"):
                                if meta["needs_action"] == "YES":
                                    st.error("🚨 NOC Ticket Triggered via n8n")
                                else:
                                    st.info("✅ Resolved locally by Copilot")
                                if meta["sources"]:
                                    st.markdown("**Referenced Manuals:**")
                                    for src in meta["sources"]:
                                        st.caption(f"- {src}")

                        # Save AI message to state
                        st.session_state.messages.append({"role": "assistant", "content": answer, "meta": meta})
                    else:
                        st.error(f"API Error: {response.status_code}")
                except Exception as e:
                    st.error(f"Connection error: {e}. Is your FastAPI server running?")

# =========================
# TAB 2: Ticket Dashboard
# =========================
with tab2:
    st.subheader("Live Network Operations Center (NOC)")
    
    try:
        df = pd.read_csv(SHEET_URL)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Total Tickets Today", value=len(df), delta="+2 in last hour", delta_color="inverse")
        with col2:
            st.metric(label="Active Network Outages", value="1", delta="-1 since yesterday")
        with col3:
            st.metric(label="Avg Resolution Time", value="14m", delta="-2m", delta_color="normal")
            
        st.markdown("---")
        st.markdown("### 📋 Recent Escalations Database")
        
        st.dataframe(df, use_container_width=True, height=350)
        
        if st.button("🔄 Force Sync with Database"):
            st.toast("Successfully synced with Google Sheets and n8n pipelines!", icon="✅")
            
    except Exception as e:
        st.warning("⚠️ Could not connect to the live database. Waiting for the first ticket to be created or checking sheet permissions.")
        st.caption(str(e))