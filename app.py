import streamlit as st
import os

# Optional dotenv import for local .env loading
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Streamlit Page Configuration
st.set_page_config(
    page_title="SAINT_APP | Enterprise RFP Suite",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS Styling for High-Contrast Dark Sidebar and White Bold Text
CUSTOM_CSS = """
<style>
    /* Main container styling */
    .main .block-container {
        padding-top: 1.8rem;
        padding-bottom: 3rem;
        max-width: 95%;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #ffffff;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.8rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    }
    .main-header h1 {
        margin: 0;
        font-size: 1.8rem;
        font-weight: 700;
        letter-spacing: -0.5px;
        color: #ffffff;
    }
    .main-header p {
        margin: 0.4rem 0 0 0;
        color: #94a3b8;
        font-size: 0.95rem;
    }

    /* Winner Banner Card */
    .winner-card {
        background: linear-gradient(135deg, #065f46 0%, #047857 100%);
        color: #ffffff;
        padding: 1.25rem 1.75rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 15px rgba(4, 120, 87, 0.25);
    }
    .winner-card h3 {
        margin: 0 0 0.3rem 0;
        color: #ecfdf5;
        font-size: 1.4rem;
    }
    .winner-card p {
        margin: 0.2rem 0;
        color: #d1fae5;
        font-size: 0.95rem;
    }

    /* ========================================================= */
    /* SIDEBAR STYLING - HIGH CONTRAST DARK NAVY WITH WHITE BOLD TEXT */
    /* ========================================================= */
    section[data-testid="stSidebar"] {
        background-color: #0b1329 !important; /* Deep contrast dark navy */
    }

    /* Target all sidebar text, labels, headers, radio options */
    section[data-testid="stSidebar"] *, 
    section[data-testid="stSidebar"] p, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] div {
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
    }

    /* Sidebar Title & Caption Header */
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3 {
        color: #ffffff !important;
        font-weight: 800 !important;
    }

    /* Radio button active state highlight */
    div[data-testid="stRadioButton"] label {
        padding: 8px 12px;
        border-radius: 8px;
        transition: background-color 0.2s ease;
    }
    div[data-testid="stRadioButton"] label:hover {
        background-color: rgba(255, 255, 255, 0.15) !important;
    }

    /* Metric Badges */
    div[data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 700;
    }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Module Imports
from modules.vendor_management import render_vendor_management_module
from modules.rfp_builder import render_rfp_builder_module
from modules.response_eval import render_response_eval_module
from modules.cpo_dashboard import render_cpo_dashboard_module

def main():
    # Sidebar Navigation Header
    st.sidebar.image("https://img.icons8.com/isometric/96/lightning-bolt.png", width=55)
    st.sidebar.title("SAINT_APP")
    st.sidebar.caption("Enterprise RFP Suite")

    st.sidebar.markdown("---")

    # 4-Step Logical Navigation Flow
    selected_module = st.sidebar.radio(
        "PROCUREMENT WORKFLOW",
        [
            "Step 1: Vendor Directory",
            "Step 2: RFP Builder & Dispatch",
            "Step 3: Evaluation & Scoring",
            "Step 4: CPO Historical Dashboard"
        ],
        index=0
    )

    st.sidebar.markdown("---")
    st.sidebar.caption("SAINT_APP Enterprise v2.0")

    # Retrieve API key silently from env if available
    api_key_input = os.getenv("MISTRAL_API_KEY", "")

    # Navigation Router
    if "Step 1" in selected_module:
        render_vendor_management_module()
    elif "Step 2" in selected_module:
        render_rfp_builder_module(api_key_input)
    elif "Step 3" in selected_module:
        render_response_eval_module()
    elif "Step 4" in selected_module:
        render_cpo_dashboard_module()

if __name__ == "__main__":
    main()
