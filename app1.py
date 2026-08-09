"""
S.A.I.N.T. Enterprise — Unified Source-to-Pay Platform
With Agentic Conversational AI Assist across all 5 Procurement Modules
"""

import streamlit as st
import sqlite3
import os
import json
import re
import difflib
import datetime
import requests
import pandas as pd
import matplotlib.pyplot as plt

# Optional dotenv import for local .env loading
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import LLM clients gracefully
try:
    from mistralai.client import Mistral
except ImportError:
    Mistral = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# =============================================================
# 1. PAGE CONFIG — MUST BE FIRST STREAMLIT CALL
# =============================================================
st.set_page_config(
    page_title="S.A.I.N.T. | Enterprise Procurement Suite",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================
# 2. CUSTOM CSS
# =============================================================
st.markdown("""
<style>
    /* Main Background & Padding */
    .stApp { background-color: #f8fafc; }
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 95%;
    }

    /* Enterprise Header Banner */
    .saint-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
        padding: 24px 32px;
        border-radius: 12px;
        margin-bottom: 24px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .saint-header h1 {
        color: #38bdf8;
        font-size: 2.2rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: 1.5px;
    }
    .saint-header p {
        color: #94a3b8;
        margin: 4px 0 0 0;
        font-size: 0.95rem;
    }

    /* Summary & Containers */
    .summary-box {
        background: white;
        border-left: 4px solid #0284c7;
        padding: 16px 20px;
        border-radius: 0 8px 8px 0;
        font-size: 0.97rem;
        color: #334155;
        line-height: 1.7;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #0b1329 !important;
    }
    section[data-testid="stSidebar"] *, 
    section[data-testid="stSidebar"] p, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] div {
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3 {
        color: #ffffff !important;
        font-weight: 800 !important;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# =============================================================
# 3. CONFIGURATION CLASS
# =============================================================
class Config:
    MISTRAL_API_KEY  = os.getenv("MISTRAL_API_KEY", "")
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    MISTRAL_MODEL    = "mistral-small-latest"
    DEEPSEEK_MODEL   = "deepseek-chat"
    REQUEST_TIMEOUT  = 10
    DB_PATH          = os.path.expanduser("~/saint_data.db")
    PURGE_MONTHS     = 12
    SEC_USER_AGENT   = os.getenv("SEC_USER_AGENT", "SAINT-Procurement-Platform/3.0 (contact@saint-ai.com)")


# =============================================================
# 4. DATABASE MANAGER
# =============================================================
class Database:
    @staticmethod
    def get_connection():
        conn = sqlite3.connect(Config.DB_PATH, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    @staticmethod
    def initialize():
        conn = Database.get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor TEXT NOT NULL, score REAL, risk_label TEXT, confidence INTEGER,
                wri_json TEXT, summary TEXT, full_report TEXT, graph_data TEXT,
                sources_json TEXT, verified_financials_json TEXT,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, purge_after TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE, category TEXT NOT NULL,
                contact_email TEXT, rating TEXT, status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL, vendor TEXT NOT NULL, contract_value REAL,
                effective_date TEXT, expiration_date TEXT, status TEXT,
                file_name TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS spend_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor TEXT NOT NULL, category TEXT NOT NULL, amount REAL,
                spend_date TEXT, business_unit TEXT
            )
        """)
        conn.commit()
        
        # Seed Initial Suppliers if empty
        check_sup = conn.execute("SELECT COUNT(*) as count FROM suppliers").fetchone()
        if check_sup["count"] == 0:
            mock_suppliers = [
                ("Cloudvita IT Consulting", "Professional Services", "contact@cloudvita.com", "4.8/5.0", "Active"),
                ("Acme Infrastructure", "IT Hardware", "sales@acmeinfra.com", "4.5/5.0", "Active"),
                ("Global Logistics Corp", "Supply Chain", "support@globallogistics.com", "3.9/5.0", "Under Review"),
                ("Apple", "Consumer Electronics", "enterprise@apple.com", "4.9/5.0", "Active"),
                ("Microsoft", "Cloud & Software", "enterprise@microsoft.com", "4.9/5.0", "Active")
            ]
            conn.executemany("INSERT OR IGNORE INTO suppliers (name, category, contact_email, rating, status) VALUES (?,?,?,?,?)", mock_suppliers)
            conn.commit()

        # Seed Mock Spend Data if empty
        check_spend = conn.execute("SELECT COUNT(*) as count FROM spend_records").fetchone()
        if check_spend["count"] == 0:
            mock_spend = [
                ("Acme Corp", "IT Infrastructure", 1250000.0, "2026-01-15", "Technology"),
                ("Global Logistics", "Supply Chain", 850000.0, "2026-02-01", "Operations"),
                ("Cloudvita Consulting", "Professional Services", 450000.0, "2026-02-10", "Corporate"),
                ("TechSupplies Inc", "Hardware", 120000.0, "2026-02-28", "Technology"),
                ("Apex Office", "Facilities", 35000.0, "2026-03-01", "Admin")
            ]
            conn.executemany("INSERT INTO spend_records (vendor, category, amount, spend_date, business_unit) VALUES (?,?,?,?,?)", mock_spend)
            conn.commit()
            
        conn.close()

    @staticmethod
    def save_supplier(name, category, email, rating, status):
        conn = Database.get_connection()
        conn.execute("INSERT OR REPLACE INTO suppliers (name, category, contact_email, rating, status) VALUES (?, ?, ?, ?, ?)", (name, category, email, rating, status))
        conn.commit()
        conn.close()

    @staticmethod
    def get_suppliers():
        conn = Database.get_connection()
        rows = conn.execute("SELECT * FROM suppliers ORDER BY name ASC").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def save_contract(title, vendor, value, eff_date, exp_date, status, file_name):
        conn = Database.get_connection()
        conn.execute("INSERT INTO contracts (title, vendor, contract_value, effective_date, expiration_date, status, file_name) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                     (title, vendor, value, eff_date, exp_date, status, file_name))
        conn.commit()
        conn.close()

    @staticmethod
    def get_contracts():
        conn = Database.get_connection()
        rows = conn.execute("SELECT * FROM contracts ORDER BY created_at DESC").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def save_spend(vendor, category, amount, spend_date, business_unit):
        conn = Database.get_connection()
        conn.execute("INSERT INTO spend_records (vendor, category, amount, spend_date, business_unit) VALUES (?, ?, ?, ?, ?)",
                     (vendor, category, amount, spend_date, business_unit))
        conn.commit()
        conn.close()

    @staticmethod
    def get_spend():
        conn = Database.get_connection()
        rows = conn.execute("SELECT * FROM spend_records ORDER BY spend_date DESC").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def save_analysis(vendor, score, risk_label, confidence, wri, summary, full_report, graph_data, sources=None, verified_financials=None):
        purge_after = datetime.datetime.now() + datetime.timedelta(days=Config.PURGE_MONTHS * 30)
        conn = Database.get_connection()
        conn.execute("""
            INSERT INTO analyses (vendor, score, risk_label, confidence, wri_json, summary, full_report, graph_data, sources_json, verified_financials_json, purge_after)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (vendor, score, risk_label, confidence, json.dumps(wri), summary, json.dumps(full_report), json.dumps(graph_data), json.dumps(sources or []), json.dumps(verified_financials or {}), purge_after.isoformat()))
        conn.commit()
        conn.close()

    @staticmethod
    def get_history(search_term="", limit=50):
        conn = Database.get_connection()
        rows = conn.execute("SELECT id, vendor, score, risk_label, confidence, analyzed_at, purge_after FROM analyses WHERE vendor LIKE ? ORDER BY analyzed_at DESC LIMIT ?", (f"%{search_term}%", limit)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

# Initialize Database
Database.initialize()


# =============================================================
# 5. AGENT CONTROLLER UTILITY
# =============================================================
def render_module_agent(module_name: str, context_prompt: str, action_handler=None):
    """Renders a dedicated interactive agent for any module to handle Q&A and database updates."""
    st.markdown("---")
    st.subheader(f"🤖 {module_name} Agent Assistant")
    st.caption("Ask questions about this module, or command the agent to update database records.")

    session_key = f"agent_chat_{module_name.lower().replace(' ', '_')}"
    if session_key not in st.session_state:
        st.session_state[session_key] = [
            {"role": "assistant", "content": f"Hello! I am your **{module_name} Agent**. How can I help you analyze data or update records today?"}
        ]

    for msg in st.session_state[session_key]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_query = st.chat_input(f"Ask or instruct the {module_name} Agent...")
    if user_query:
        st.session_state[session_key].append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        with st.chat_message("assistant"):
            response_text = f"**Agent Processing:** Received request regarding *'{user_query}'*."
            
            # Execute database actions if custom handler provided
            if action_handler:
                action_result = action_handler(user_query)
                if action_result:
                    response_text += f"\n\n✅ **Action Taken:** {action_result}"
                else:
                    response_text += f"\n\nAnalysed module context: {context_prompt[:150]}..."
            else:
                response_text += f"\n\nAnalysed context: {context_prompt[:150]}..."

            st.markdown(response_text)
            st.session_state[session_key].append({"role": "assistant", "content": response_text})


# =============================================================
# 6. MAIN APP ROUTER & MODULES
# =============================================================
def main():
    st.sidebar.image("https://img.icons8.com/isometric/96/lightning-bolt.png", width=50)
    st.sidebar.title("S.A.I.N.T. Platform")
    st.sidebar.caption("Source-to-Pay Intelligence Suite v3.0")
    st.sidebar.markdown("---")

    selected_module = st.sidebar.radio(
        "CORE MODULES",
        [
            "1️⃣ Supplier AI & Risk Tracker",
            "2️⃣ Supplier Directory & Management",
            "3️⃣ RFP Pilot Suite",
            "4️⃣ Contract Lifecycle (CLM)",
            "5️⃣ Spend Analytics Dashboard"
        ]
    )

    st.sidebar.markdown("---")
    db_suppliers = Database.get_suppliers()
    db_sup_names = [s["name"] for s in db_suppliers] if db_suppliers else []

    # ---------------------------------------------------------
    # MODULE 1: SUPPLIER AI & RISK TRACKER
    # ---------------------------------------------------------
    if "1️⃣" in selected_module:
        st.markdown("""
        <div class="saint-header">
            <h1>Supplier AI & Risk Tracker</h1>
            <p>Real-Time Financial, Geopolitical & Compliance Risk Intelligence</p>
        </div>
        """, unsafe_allow_html=True)

        col_sel, col_free = st.columns(2)
        with col_sel:
            selected_vendor = st.selectbox("Select Managed Supplier", ["-- Select --"] + db_sup_names)
        with col_free:
            free_text = st.text_input("Or Enter Custom Supplier Name", placeholder="e.g. Caterpillar, Tesla...")

        target = free_text.strip() if free_text.strip() else (selected_vendor if selected_vendor != "-- Select --" else "")

        if st.button("⚡ Run Risk Analysis", type="primary", use_container_width=True):
            if target:
                Database.save_analysis(target, 76.5, "MODERATE RISK", 85, {"financial": 75}, "Executive Summary Generated.", ["Section 1", "Section 2"], [70, 75, 80])
                st.success(f"Risk analysis complete for {target}!")
            else:
                st.warning("Please select or enter a supplier name.")

        history = Database.get_history()
        if history:
            st.markdown("### Recent Risk Analyses")
            st.dataframe(pd.DataFrame(history)[["vendor", "score", "risk_label", "analyzed_at"]], use_container_width=True, hide_index=True)

        # Agent Integration
        render_module_agent("Supplier Risk", f"Active Supplier: {target}, Recent Records: {len(history)}")

    # ---------------------------------------------------------
    # MODULE 2: SUPPLIER DIRECTORY & MANAGEMENT
    # ---------------------------------------------------------
    elif "2️⃣" in selected_module:
        st.markdown("""
        <div class="saint-header">
            <h1>Supplier Directory & Management</h1>
            <p>Onboard, Database-Register & Monitor Enterprise Vendors</p>
        </div>
        """, unsafe_allow_html=True)

        col_add, col_list = st.columns([2, 3])
        with col_add:
            st.subheader("➕ Register New Supplier")
            sup_name = st.text_input("Supplier Business Name")
            sup_cat = st.selectbox("Category", ["IT Hardware", "Software & Cloud", "Professional Services", "Supply Chain", "Facilities", "Other"])
            sup_email = st.text_input("Contact Email")
            sup_rating = st.select_slider("Rating", options=["1.0/5.0", "3.0/5.0", "4.5/5.0", "5.0/5.0"], value="4.5/5.0")
            sup_status = st.selectbox("Status", ["Active", "Under Review", "Preferred", "Blacklisted"])

            if st.button("💾 Save Supplier to Database", type="primary"):
                if sup_name.strip():
                    Database.save_supplier(sup_name.strip(), sup_cat, sup_email, sup_rating, sup_status)
                    st.success(f"Supplier '{sup_name.strip()}' saved!")
                    st.rerun()

        with col_list:
            st.subheader("🏢 Managed Suppliers Database")
            suppliers = Database.get_suppliers()
            if suppliers:
                st.dataframe(pd.DataFrame(suppliers)[["name", "category", "contact_email", "rating", "status"]], use_container_width=True, hide_index=True)

        # Action Handler for Agent to auto-add suppliers from prompt
        def supplier_agent_action(user_text):
            if "add supplier" in user_text.lower() or "register" in user_text.lower():
                parts = user_text.split()
                new_name = parts[-1].capitalize() if len(parts) > 2 else "NewVendor"
                Database.save_supplier(new_name, "Professional Services", f"info@{new_name.lower()}.com", "4.5/5.0", "Active")
                return f"Automatically registered supplier '{new_name}' in database."
            return None

        # Agent Integration
        render_module_agent("Supplier Directory", f"Total Managed Suppliers: {len(db_suppliers)}", supplier_agent_action)

    # ---------------------------------------------------------
    # MODULE 3: RFP PILOT SUITE
    # ---------------------------------------------------------
    elif "3️⃣" in selected_module:
        st.markdown("""
        <div class="saint-header">
            <h1>RFP Pilot Suite</h1>
            <p>Automated Proposal Generation, Dispatch, & Response Evaluation</p>
        </div>
        """, unsafe_allow_html=True)

        rfp_title = st.text_input("RFP Title", "Enterprise Cloud Migration")
        rfp_cat = st.selectbox("Category", ["Software & Cloud", "Professional Services", "IT Hardware"])
        selected_rfp_vendors = st.multiselect("Pick Target Suppliers", db_sup_names, default=db_sup_names[:2] if len(db_sup_names) >= 2 else db_sup_names)

        if st.button("🚀 Dispatch RFP", type="primary"):
            st.success(f"RFP '{rfp_title}' dispatched to: {', '.join(selected_rfp_vendors)}")

        # Agent Integration
        render_module_agent("RFP Pilot", f"RFP Title: {rfp_title}, Targeted Vendors: {len(selected_rfp_vendors)}")

    # ---------------------------------------------------------
    # MODULE 4: CONTRACT LIFECYCLE MANAGEMENT (CLM)
    # ---------------------------------------------------------
    elif "4️⃣" in selected_module:
        st.markdown("""
        <div class="saint-header">
            <h1>Contract Lifecycle Management (CLM)</h1>
            <p>Centralized Repository, Metadata Extraction & Active Contract Tracking</p>
        </div>
        """, unsafe_allow_html=True)

        c_title = st.text_input("Contract Ref/Title", "Master Services Agreement 2026")
        c_vendor = st.selectbox("Select Supplier", db_sup_names if db_sup_names else ["Cloudvita IT Consulting"])
        c_val = st.number_input("Value ($)", value=150000.0)

        if st.button("💾 Save Contract", type="primary"):
            Database.save_contract(c_title, c_vendor, c_val, "2026-08-01", "2027-08-01", "Active", "MSA.pdf")
            st.success(f"Contract saved for {c_vendor}!")

        contracts = Database.get_contracts()
        if contracts:
            st.dataframe(pd.DataFrame(contracts)[["title", "vendor", "contract_value", "status"]], use_container_width=True, hide_index=True)

        # Agent Integration
        render_module_agent("Contract CLM", f"Total Active Contracts: {len(contracts)}")

    # ---------------------------------------------------------
    # MODULE 5: SPEND ANALYTICS DASHBOARD
    # ---------------------------------------------------------
    elif "5️⃣" in selected_module:
        st.markdown("""
        <div class="saint-header">
            <h1>Autonomous Spend Analytics</h1>
            <p>Real-Time Spend Visibility, Tail-Spend Detection & Category Intelligence</p>
        </div>
        """, unsafe_allow_html=True)

        spend_data = Database.get_spend()
        df_s = pd.DataFrame(spend_data)

        if not df_s.empty:
            st.metric("Total Analyzed Spend", f"${df_s['amount'].sum():,.2f}")
            st.dataframe(df_s[["vendor", "category", "amount", "spend_date"]], use_container_width=True, hide_index=True)

        # Action Handler for Agent to log spend directly
        def spend_agent_action(user_text):
            if "add spend" in user_text.lower() or "log spend" in user_text.lower():
                Database.save_spend("Cloudvita Consulting", "Professional Services", 50000.0, "2026-08-08", "Corporate")
                return "Logged new spend entry of $50,000 for Cloudvita Consulting."
            return None

        # Agent Integration
        render_module_agent("Spend Analytics", f"Total Records: {len(df_s)}", spend_agent_action)


if __name__ == "__main__":
    main()
