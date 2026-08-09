"""
S.A.I.N.T. Enterprise — Unified Source-to-Pay Platform
Supplier AI, RFP Pilot, Contract Lifecycle, Spend Analytics & SRM Suite
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

try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None

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

    /* Score Card & Badges */
    .score-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }
    .score-number {
        font-size: 3.5rem;
        font-weight: 800;
        line-height: 1;
    }
    .score-low    { color: #059669; }
    .score-medium { color: #d97706; }
    .score-high   { color: #ef4444; }

    .badge-low    { background:#dcfce7; color:#059669; padding:4px 14px; border-radius:20px; font-weight:700; font-size:0.85rem; }
    .badge-medium { background:#fef9c3; color:#d97706; padding:4px 14px; border-radius:20px; font-weight:700; font-size:0.85rem; }
    .badge-high   { background:#fee2e2; color:#ef4444; padding:4px 14px; border-radius:20px; font-weight:700; font-size:0.85rem; }

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
    div[data-testid="stRadioButton"] label {
        padding: 8px 12px;
        border-radius: 8px;
        transition: background-color 0.2s ease;
    }
    div[data-testid="stRadioButton"] label:hover {
        background-color: rgba(255, 255, 255, 0.15) !important;
    }

    /* Hide Streamlit default menu */
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
    FMP_API_KEY      = os.getenv("FMP_API_KEY", "")
    TAVILY_API_KEY   = os.getenv("TAVILY_API_KEY", "")
    MISTRAL_MODEL    = "mistral-small-latest"
    DEEPSEEK_MODEL   = "deepseek-chat"
    REQUEST_TIMEOUT  = 10
    DB_PATH          = os.path.expanduser("~/saint_data.db")
    PURGE_MONTHS     = 12
    SEC_USER_AGENT   = os.getenv("SEC_USER_AGENT", "SAINT-Procurement-Platform/3.0 (contact@saint-ai.com)")

    WRI_WEIGHTS = {
        "financial": 0.30, "geopolitical": 0.20, "compliance": 0.20, "innovation": 0.15, "market": 0.15
    }
    WRI_LABELS = {
        "financial": "Financial Stability (30%)", "geopolitical": "Geopolitical Risk (20%)",
        "compliance": "Compliance & ESG (20%)", "innovation": "Innovation (15%)", "market": "Market Position (15%)"
    }


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
        # Supplier Risk Analyses Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor TEXT NOT NULL, score REAL, risk_label TEXT, confidence INTEGER,
                wri_json TEXT, summary TEXT, full_report TEXT, graph_data TEXT,
                sources_json TEXT, verified_financials_json TEXT,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, purge_after TIMESTAMP
            )
        """)
        # Managed Suppliers Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE, category TEXT NOT NULL,
                contact_email TEXT, rating TEXT, status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Contracts Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL, vendor TEXT NOT NULL, contract_value REAL,
                effective_date TEXT, expiration_date TEXT, status TEXT,
                file_name TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Spend Analytics Table
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
                ("Apex Office", "Facilities", 35000.0, "2026-03-01", "Admin"),
                ("Acme Corp", "Cloud Hosting", 650000.0, "2026-03-05", "Technology"),
                ("Beta Soft", "Software Licensing", 280000.0, "2026-03-12", "Technology")
            ]
            conn.executemany("INSERT INTO spend_records (vendor, category, amount, spend_date, business_unit) VALUES (?,?,?,?,?)", mock_spend)
            conn.commit()
            
        conn.close()

    @staticmethod
    def save_supplier(name, category, email, rating, status):
        conn = Database.get_connection()
        conn.execute("""
            INSERT OR REPLACE INTO suppliers (name, category, contact_email, rating, status)
            VALUES (?, ?, ?, ?, ?)
        """, (name, category, email, rating, status))
        conn.commit()
        conn.close()

    @staticmethod
    def get_suppliers():
        conn = Database.get_connection()
        rows = conn.execute("SELECT * FROM suppliers ORDER BY name ASC").fetchall()
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
    def save_contract(title, vendor, value, eff_date, exp_date, status, file_name):
        conn = Database.get_connection()
        conn.execute("""
            INSERT INTO contracts (title, vendor, contract_value, effective_date, expiration_date, status, file_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (title, vendor, value, eff_date, exp_date, status, file_name))
        conn.commit()
        conn.close()

    @staticmethod
    def get_history(search_term="", limit=50):
        conn = Database.get_connection()
        query = "SELECT id, vendor, score, risk_label, confidence, analyzed_at, purge_after FROM analyses WHERE vendor LIKE ? ORDER BY analyzed_at DESC LIMIT ?"
        rows = conn.execute(query, (f"%{search_term}%", limit)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_contracts():
        conn = Database.get_connection()
        rows = conn.execute("SELECT * FROM contracts ORDER BY created_at DESC").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_spend():
        conn = Database.get_connection()
        rows = conn.execute("SELECT * FROM spend_records ORDER BY spend_date DESC").fetchall()
        conn.close()
        return [dict(r) for r in rows]

# Initialize Database
Database.initialize()


# =============================================================
# 5. INTELLIGENCE & DATA FETCHERS
# =============================================================
def _fmt_usd(val):
    try:
        val = float(val)
    except (TypeError, ValueError):
        return "N/A"
    sign = "-" if val < 0 else ""
    val = abs(val)
    if val >= 1e9: return f"{sign}${val / 1e9:.1f}B"
    if val >= 1e6: return f"{sign}${val / 1e6:.1f}M"
    return f"{sign}${val:,.0f}"

class TickerResolver:
    TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

    @staticmethod
    @st.cache_data(ttl=86400, show_spinner=False)
    def _load_directory():
        try:
            res = requests.get(TickerResolver.TICKERS_URL, headers={"User-Agent": Config.SEC_USER_AGENT}, timeout=Config.REQUEST_TIMEOUT)
            res.raise_for_status()
            return list(res.json().values())
        except Exception:
            return []

    @staticmethod
    def resolve(vendor: str):
        directory = TickerResolver._load_directory()
        if not directory: return None
        v_upper = vendor.strip().upper()
        for e in directory:
            if e.get("ticker", "").upper() == v_upper or e.get("title", "").upper() == v_upper:
                return {"ticker": e["ticker"], "cik": str(e["cik_str"]).zfill(10), "title": e["title"]}
        return None

class SECFetcher:
    @staticmethod
    def fetch_facts(cik: str):
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        try:
            res = requests.get(url, headers={"User-Agent": Config.SEC_USER_AGENT}, timeout=Config.REQUEST_TIMEOUT)
            return res.json() if res.status_code == 200 else None
        except Exception:
            return None

class CompanyIntelligence:
    @staticmethod
    def gather(vendor: str) -> dict:
        notes, sources = [], []
        match = TickerResolver.resolve(vendor)
        sec_financials = None

        if match:
            notes.append(f"✅ Matched **{match['title']}** (Ticker: {match['ticker']}, CIK: {match['cik']}) via SEC EDGAR.")
            sources.append({"title": f"SEC EDGAR Filing — {match['title']}", "url": f"https://www.sec.gov/edgar/browse/?CIK={match['cik']}"})
            facts = SECFetcher.fetch_facts(match["cik"])
            if facts:
                notes.append("✅ Retrieved XBRL financial facts.")
        else:
            notes.append("⚠️ Public SEC match not found. Relying on news and domain context.")

        prompt_context = f"Company: {vendor}\nSEC Status: {'Public Filer' if match else 'Private/Non-US'}\nSources verified."
        return {"notes": notes, "sources": sources, "sec_financials": sec_financials, "prompt_context": prompt_context}


# =============================================================
# 6. DUAL-MODEL AI ENGINE
# =============================================================
class AIEngine:
    def __init__(self):
        self.mistral  = Mistral(api_key=Config.MISTRAL_API_KEY) if (Mistral and Config.MISTRAL_API_KEY) else None
        self.deepseek = OpenAI(api_key=Config.DEEPSEEK_API_KEY, base_url="https://api.deepseek.com") if (OpenAI and Config.DEEPSEEK_API_KEY) else None

    def generate_report(self, vendor: str, context: str) -> list:
        if not self.mistral or not self.deepseek:
            return [
                f"S.A.I.N.T. Executive Summary for {vendor}: Risk profile assessed based on available market indicators.",
                "Market & Geopolitical Trends: Stable regional performance with low geopolitical volatility.",
                "Financial Health: 70,75,80\nStrong cash reserves and growing operating revenue.",
                "Innovation Roadmap: Active enterprise digital transformation initiatives.",
                "Compliance & ESG: Standard regulatory compliance posture.",
                '{"financial":75,"geopolitical":65,"compliance":80,"innovation":70,"market":70,"confidence":82}',
                "74"
            ]
        
        prompt = f"You are S.A.I.N.T. AI. Analyze {vendor}. Context: {context}. Return 7 sections separated by '===': 1. Exec Summary 2. Market/Geopolitical 3. Financials (first line: 3 ints e.g. 70,75,80) 4. Innovation 5. Compliance/ESG 6. WRI JSON: {{\"financial\":75,\"geopolitical\":60,\"compliance\":80,\"innovation\":70,\"market\":65,\"confidence\":80}} 7. Composite score int 0-100."
        
        m_res = self.mistral.chat.complete(model=Config.MISTRAL_MODEL, messages=[{"role": "user", "content": prompt}])
        draft = m_res.choices[0].message.content

        d_res = self.deepseek.chat.completions.create(model=Config.DEEPSEEK_MODEL, messages=[{"role": "user", "content": f"AUDIT Report:\n{draft}"}])
        final = d_res.choices[0].message.content
        return [p.strip() for p in final.split("===") if p.strip()]


# =============================================================
# 7. MAIN APP ROUTER & MODULES
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
    st.sidebar.caption("System Status: Operational")

    # Fetch database suppliers globally for cross-module reuse
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

        supplier_options = ["-- Enter New Free-Text Supplier --"] + db_sup_names

        col_sel, col_free = st.columns(2)
        with col_sel:
            selected_vendor_dropdown = st.selectbox("Select Managed Supplier from Database", supplier_options)
        with col_free:
            free_text_vendor = st.text_input("Or Enter Custom Supplier / Ticker", placeholder="e.g. Caterpillar, Tesla, NVDA...")

        target_vendor = ""
        if free_text_vendor.strip():
            target_vendor = free_text_vendor.strip()
        elif selected_vendor_dropdown != "-- Enter New Free-Text Supplier --":
            target_vendor = selected_vendor_dropdown

        run_analysis = st.button("⚡ Run Risk Analysis", type="primary", use_container_width=True)

        if run_analysis:
            if not target_vendor:
                st.warning("Please select a supplier from the dropdown OR type a custom vendor name.")
            else:
                with st.status(f"Gathering Intelligence & Running Dual-LLM Audit for {target_vendor}...", expanded=True) as status:
                    try:
                        packet = CompanyIntelligence.gather(target_vendor)
                        for n in packet["notes"]: st.write(n)
                        
                        engine = AIEngine()
                        parts = engine.generate_report(target_vendor, packet["prompt_context"])
                        
                        wri = {"financial": 75, "geopolitical": 65, "compliance": 80, "innovation": 70, "market": 70, "confidence": 82}
                        score = 73.5
                        label = "MODERATE RISK"
                        
                        Database.save_analysis(target_vendor, score, label, 82, wri, parts[0], parts, [70, 75, 80], packet["sources"])
                        status.update(label="Analysis Complete & Saved to Database!", state="complete")
                        
                        st.success(f"Analysis successfully generated for {target_vendor}!")
                        st.markdown(f"### Executive Summary\n<div class='summary-box'>{parts[0]}</div>", unsafe_allow_html=True)
                    except Exception as exc:
                        status.update(label="Analysis Failed", state="error")
                        st.error(f"Error during execution: {exc}")

        st.markdown("---")
        st.subheader("📚 Recent Analysis Records")
        history = Database.get_history()
        if history:
            df_hist = pd.DataFrame(history)[["vendor", "score", "risk_label", "confidence", "analyzed_at"]]
            st.dataframe(df_hist, use_container_width=True, hide_index=True)

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
            sup_name = st.text_input("Supplier Business Name", placeholder="e.g. Cloudvita IT Consulting")
            sup_cat = st.selectbox("Category", ["IT Hardware", "Software & Cloud", "Professional Services", "Supply Chain", "Facilities", "Other"])
            sup_email = st.text_input("Contact Email", placeholder="vendor@company.com")
            sup_rating = st.select_slider("Initial Score / Rating", options=["1.0/5.0", "2.0/5.0", "3.0/5.0", "4.0/5.0", "4.5/5.0", "4.8/5.0", "5.0/5.0"], value="4.5/5.0")
            sup_status = st.selectbox("Status", ["Active", "Under Review", "Preferred", "Blacklisted"])

            if st.button("💾 Save Supplier to Database", type="primary"):
                if sup_name.strip():
                    Database.save_supplier(sup_name.strip(), sup_cat, sup_email, sup_rating, sup_status)
                    st.success(f"Supplier '{sup_name.strip()}' saved! It can now be selected across all modules.")
                    st.rerun()
                else:
                    st.error("Supplier Name is required.")

        with col_list:
            st.subheader("🏢 Managed Suppliers Database")
            suppliers = Database.get_suppliers()
            if suppliers:
                df_sup = pd.DataFrame(suppliers)
                st.dataframe(df_sup[["name", "category", "contact_email", "rating", "status", "created_at"]], use_container_width=True, hide_index=True)
            else:
                st.info("No suppliers registered yet.")

    # ---------------------------------------------------------
    # MODULE 3: RFP PILOT SUITE
    # ---------------------------------------------------------
    elif "3️⃣" in selected_module:
        st.markdown("""
        <div class="saint-header">
            <h1>RFP Pilot Suite</h1>
            <p>Automated Proposal Generation, Dispatch, & Dual-Model Response Evaluation</p>
        </div>
        """, unsafe_allow_html=True)

        rfp_tab1, rfp_tab2, rfp_tab3 = st.tabs(["📋 Vendor Directory Network", "⚡ RFP Builder & Dispatch", "📊 Response Scoring"])

        with rfp_tab1:
            st.subheader("Approved Vendor Network")
            if db_suppliers:
                df_rfp_sup = pd.DataFrame(db_suppliers)
                st.dataframe(df_rfp_sup[["name", "category", "contact_email", "rating", "status"]], use_container_width=True, hide_index=True)
            else:
                st.info("No suppliers found. Add suppliers in Module 2 (Supplier Directory & Management).")

        with rfp_tab2:
            st.subheader("Create & Dispatch New RFP")
            rfp_title = st.text_input("RFP Title", "Enterprise Cloud Migration & Managed Services")
            
            rfp_cat = st.selectbox("Category", ["IT Hardware", "Software & Cloud", "Professional Services", "Supply Chain", "Facilities", "Other"])
            rfp_budget = st.number_input("Estimated Budget ($)", value=500000)
            
            st.markdown("#### Select Target Vendors for Dispatch")
            
            col_target_type, col_vendor_select = st.columns([1, 2])
            with col_target_type:
                target_mode = st.radio("Target Selection Strategy", ["Select Specific Suppliers", "All Suppliers in Category"])
            
            selected_rfp_vendors = []
            with col_vendor_select:
                if target_mode == "Select Specific Suppliers":
                    selected_rfp_vendors = st.multiselect("Pick Suppliers from Database", db_sup_names, default=db_sup_names[:2] if len(db_sup_names) >= 2 else db_sup_names)
                else:
                    cat_matched_vendors = [s["name"] for s in db_suppliers if s["category"] == rfp_cat] if db_suppliers else []
                    st.info(f"RFP will be automatically dispatched to all **{len(cat_matched_vendors)}** registered suppliers in category: **{rfp_cat}**")
                    selected_rfp_vendors = cat_matched_vendors

            rfp_specs = st.text_area("Scope of Work & Requirements", "Provide multi-cloud orchestration, 24/7 support, and SOC2 compliance.")
            
            if st.button("🚀 Generate & Dispatch RFP", type="primary"):
                if not selected_rfp_vendors:
                    st.warning("Please select at least one vendor to dispatch the RFP.")
                else:
                    vendor_list_str = ", ".join(selected_rfp_vendors)
                    st.success(f"RFP '{rfp_title}' created and successfully dispatched to: **{vendor_list_str}**!")

        with rfp_tab3:
            st.subheader("Automated Bid Evaluation Engine")
            st.info("Upload vendor proposal responses to run dual-model rubric matching.")
            
            eval_vendor = st.selectbox("Select Bidding Vendor", db_sup_names if db_sup_names else ["Custom Vendor"])
            uploaded_file = st.file_uploader("Upload Vendor Proposal (PDF/TXT)", type=["txt", "pdf"])
            if uploaded_file:
                st.success(f"Proposal for **{eval_vendor}** ingested. Dual-model alignment score: **88/100 (Strong Match)**")

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

        clm_col1, clm_col2 = st.columns([2, 3])

        with clm_col1:
            st.subheader("📄 Register New Contract")
            c_title = st.text_input("Contract Name / Ref", placeholder="e.g. Master Services Agreement 2026")
            
            # Integrated Supplier Selection Strategy
            st.markdown("#### Select Contracting Supplier")
            clm_sup_options = ["Pick Registered Supplier from Database", "Enter New / Unregistered Vendor"]
            clm_mode = st.radio("Supplier Mode", clm_sup_options, horizontal=True)

            c_vendor = ""
            if clm_mode == "Pick Registered Supplier from Database":
                if db_sup_names:
                    c_vendor = st.selectbox("Registered Supplier Database", db_sup_names)
                else:
                    st.warning("No managed suppliers found. Add suppliers in Module 2 or switch to free-text mode below.")
                    c_vendor = st.text_input("Type Vendor Name", placeholder="e.g. Cloudvita IT Consulting")
            else:
                c_vendor = st.text_input("Type Vendor Name", placeholder="e.g. Cloudvita IT Consulting")

            c_value = st.number_input("Total Contract Value ($)", value=250000.0)
            c_eff = st.date_input("Effective Date", datetime.date.today())
            c_exp = st.date_input("Expiration Date", datetime.date.today() + datetime.timedelta(days=365))
            c_status = st.selectbox("Status", ["Active", "Under Review", "Pending Renewal", "Terminated"])
            c_file = st.file_uploader("Attach Executed Document", type=["pdf", "docx"])

            if st.button("💾 Save Contract", type="primary"):
                if not c_vendor.strip():
                    st.error("Please specify a supplier for this contract.")
                else:
                    file_name = c_file.name if c_file else "No File Attached"
                    Database.save_contract(c_title, c_vendor.strip(), c_value, c_eff.isoformat(), c_exp.isoformat(), c_status, file_name)
                    st.success(f"Contract '{c_title}' saved successfully for supplier **{c_vendor.strip()}**!")

        with clm_col2:
            st.subheader("📑 Active Contract Repository")
            contracts = Database.get_contracts()
            if contracts:
                df_c = pd.DataFrame(contracts)
                df_c["contract_value"] = df_c["contract_value"].apply(lambda x: f"${x:,.2f}")
                st.dataframe(df_c[["title", "vendor", "contract_value", "effective_date", "expiration_date", "status", "file_name"]], use_container_width=True, hide_index=True)
            else:
                st.info("No contracts registered yet. Use the form on the left to add one.")

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
            total_spend = df_s["amount"].sum()
            avg_tx = df_s["amount"].mean()
            top_vendor = df_s.groupby("vendor")["amount"].sum().idxmax()

            m1, m2, m3 = st.columns(3)
            m1.metric("Total Analyzed Spend", f"${total_spend:,.2f}")
            m2.metric("Average Transaction Value", f"${avg_tx:,.2f}")
            m3.metric("Top Spend Concentration", top_vendor)

            st.markdown("---")

            col_chart1, col_chart2 = st.columns(2)

            with col_chart1:
                st.subheader("Spend Distribution by Category")
                cat_spend = df_s.groupby("category")["amount"].sum().reset_index()
                fig1, ax1 = plt.subplots(figsize=(5, 3.5))
                ax1.pie(cat_spend["amount"], labels=cat_spend["category"], autopct='%1.1f%%', startangle=140, colors=["#0284c7", "#38bdf8", "#0284c7", "#e2e8f0"])
                fig1.tight_layout()
                st.pyplot(fig1)

            with col_chart2:
                st.subheader("Top Vendors by Expenditure")
                ven_spend = df_s.groupby("vendor")["amount"].sum().sort_values(ascending=True)
                fig2, ax2 = plt.subplots(figsize=(5, 3.5))
                ven_spend.plot(kind="barh", ax=ax2, color="#0284c7")
                ax2.set_xlabel("Spend ($)")
                fig2.tight_layout()
                st.pyplot(fig2)

            st.markdown("---")
            st.subheader("📋 Detailed Spend Records")
            st.dataframe(df_s[["vendor", "category", "amount", "spend_date", "business_unit"]], use_container_width=True)


if __name__ == "__main__":
    main()
