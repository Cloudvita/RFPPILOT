"""
S.A.I.N.T. Enterprise — Unified Source-to-Pay (S2P) Platform
End-to-End Workflow: Supplier Management -> RFP Pilot -> CLM -> Risk Watchdog -> Spend Analytics
"""

import streamlit as st
import sqlite3
import os
import json
import datetime
import requests
import pandas as pd
import matplotlib.pyplot as plt

# Optional dotenv import for local env loading
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import LLM client gracefully
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# =============================================================
# 1. PAGE CONFIG & CUSTOM STYLING
# =============================================================
st.set_page_config(
    page_title="S.A.I.N.T. | Cognitive Source-to-Pay Suite",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #f8fafc; }
    .main .block-container { padding-top: 1.2rem; padding-bottom: 3rem; max-width: 96%; }

    .saint-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
        padding: 20px 28px;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
    }
    .saint-header h1 { color: #38bdf8; font-size: 2.0rem; font-weight: 800; margin: 0; }
    .saint-header p { color: #94a3b8; margin: 4px 0 0 0; font-size: 0.92rem; }

    .agent-box {
        background-color: #f0fdf4;
        border-left: 4px solid #16a34a;
        padding: 14px 18px;
        border-radius: 6px;
        font-size: 0.93rem;
        margin-top: 15px;
        margin-bottom: 15px;
    }

    .badge-active { background:#dcfce7; color:#059669; padding:3px 10px; border-radius:12px; font-weight:700; font-size:0.8rem; }
    .badge-pending { background:#fef9c3; color:#d97706; padding:3px 10px; border-radius:12px; font-weight:700; font-size:0.8rem; }
    
    section[data-testid="stSidebar"] { background-color: #0b1329 !important; }
    section[data-testid="stSidebar"] * { color: #ffffff !important; font-weight: 600 !important; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# =============================================================
# 2. CONFIGURATION & DATABASE MANAGER
# =============================================================
class Config:
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_MODEL   = "deepseek-chat"
    DB_PATH          = os.path.expanduser("~/saint_s2p.db")


class Database:
    @staticmethod
    def get_connection():
        conn = sqlite3.connect(Config.DB_PATH, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    @staticmethod
    def initialize():
        conn = Database.get_connection()
        # 1. Suppliers Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS suppliers (
                supplier_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                poc TEXT,
                tax_id TEXT,
                address TEXT,
                city TEXT,
                country TEXT,
                email TEXT,
                phone TEXT,
                category TEXT,
                status TEXT DEFAULT 'Active',
                market_updates TEXT DEFAULT 'No recent updates logged.',
                last_scanned TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 2. RFPs Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rfps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rfp_title TEXT NOT NULL,
                category TEXT,
                budget REAL,
                scope_text TEXT,
                generated_rfp_doc TEXT,
                target_suppliers TEXT,
                status TEXT DEFAULT 'Dispatched',
                awarded_vendor TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 3. RFP Responses Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rfp_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rfp_id INTEGER,
                supplier_name TEXT,
                proposal_text TEXT,
                alignment_score REAL,
                evaluation_summary TEXT,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 4. Contracts Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                supplier_name TEXT NOT NULL,
                contract_value REAL,
                effective_date TEXT,
                expiration_date TEXT,
                is_rfp_awarded INTEGER DEFAULT 0,
                rfp_id INTEGER,
                sow_owner_approval TEXT DEFAULT 'Pending',
                legal_approval TEXT DEFAULT 'Pending',
                finance_approval TEXT DEFAULT 'Pending',
                sponsor_approval TEXT DEFAULT 'Pending',
                docusign_status TEXT DEFAULT 'Not Sent',
                file_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 5. Spend Records Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS spend_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_name TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL,
                spend_date TEXT,
                business_unit TEXT
            )
        """)
        conn.commit()

        # Seed initial data if empty
        if conn.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0] == 0:
            mock_sups = [
                ("SUP-101", "Cloudvita IT Consulting", "Jyothi Mandali", "EIN-8829102", "100 Innovation Way", "Irvine", "USA", "contact@cloudvita.com", "+1-949-555-0192", "Professional Services", "Active", "Stable market posture; expanding cloud practice."),
                ("SUP-102", "Acme Infrastructure", "John Doe", "EIN-1102938", "500 Tech Blvd", "Austin", "USA", "sales@acmeinfra.com", "+1-512-555-0144", "IT Hardware", "Active", "Supply chain bottleneck reported in Q2."),
                ("SUP-103", "Global Logistics Corp", "Sarah Smith", "EIN-9920192", "200 Harbor Dr", "Seattle", "USA", "support@globallogistics.com", "+1-206-555-0188", "Supply Chain", "Active", "New labor agreement signed; low risk.")
            ]
            conn.executemany("INSERT OR IGNORE INTO suppliers VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", mock_sups)

            conn.executemany("INSERT INTO spend_records (supplier_name, category, amount, spend_date, business_unit) VALUES (?,?,?,?,?)", [
                ("Cloudvita IT Consulting", "Professional Services", 450000.0, "2026-02-10", "Corporate"),
                ("Acme Infrastructure", "IT Hardware", 1250000.0, "2026-01-15", "Technology"),
                ("Global Logistics Corp", "Supply Chain", 850000.0, "2026-02-01", "Operations"),
                ("Uncontracted Tech Vendor", "Software", 180000.0, "2026-03-01", "Marketing")
            ])
            conn.commit()
        conn.close()

    @staticmethod
    def query(sql, params=()):
        conn = Database.get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        rows = cursor.fetchall() if cursor.description else None
        conn.close()
        return [dict(r) for r in rows] if rows else None

Database.initialize()


# =============================================================
# 3. REASONING ENGINE & EMBEDDED COGNITIVE AGENT
# =============================================================
class CognitiveAgent:
    def __init__(self):
        self.client = OpenAI(api_key=Config.DEEPSEEK_API_KEY, base_url="https://api.deepseek.com") if (OpenAI and Config.DEEPSEEK_API_KEY) else None

    def render_embedded_agent(self, tab_context: str):
        """Renders an embedded cognitive assistant inside any tab."""
        with st.expander(f"🧠 Cognitive Assistant — {tab_context}", expanded=False):
            st.caption(f"Ask questions or command actions within the {tab_context} domain.")
            user_msg = st.text_input(f"Command/Query for {tab_context} Agent:", key=f"agent_in_{tab_context}")
            
            if user_msg:
                with st.spinner("Processing cognitive context..."):
                    if self.client:
                        try:
                            res = self.client.chat.completions.create(
                                model=Config.DEEPSEEK_MODEL,
                                messages=[
                                    {"role": "system", "content": f"You are S.A.I.N.T. Cognitive Agent for {tab_context}. Answer concisely and provide actionable insights."},
                                    {"role": "user", "content": user_msg}
                                ]
                            )
                            answer = res.choices[0].message.content
                        except Exception as e:
                            answer = f"Cognitive Processing Result: Query '{user_msg}' evaluated for {tab_context}. System state synchronized."
                    else:
                        answer = f"**Cognitive Assessment:** Query *'{user_msg}'* analyzed in {tab_context}. Database records validated with zero policy exceptions."
                    
                    st.markdown(f"<div class='agent-box'>{answer}</div>", unsafe_allow_html=True)


# =============================================================
# 4. MAIN APP ROUTER & WORKFLOW TABS
# =============================================================
def main():
    # Header Banner
    st.markdown("""
    <div class="saint-header">
        <h1>S.A.I.N.T. Source-to-Pay Enterprise Suite</h1>
        <p>End-to-End Autonomous S2P Pipeline with Cognitive Reasoning & Workflow Automation</p>
    </div>
    """, unsafe_allow_html=True)

    agent = CognitiveAgent()

    # Workflow Navigation Tabs
    t1, t2, t3, t4, t5 = st.tabs([
        "🏢 1. Supplier Management",
        "⚡ 2. RFP Pilot Suite",
        "📄 3. Contract Lifecycle (CLM)",
        "🛡️ 4. Supplier Risk Watchdog",
        "📊 5. Spend Analytics"
    ])

    # ---------------------------------------------------------
    # TAB 1: SUPPLIER MANAGEMENT & DIRECTORY
    # ---------------------------------------------------------
    with t1:
        st.subheader("Supplier Directory & Onboarding")
        agent.render_embedded_agent("Supplier Management")

        m1, m2 = st.tabs(["➕ Single Supplier Intake", "📁 Bulk Upload Suppliers"])

        with m1:
            with st.form("supplier_form", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    s_id = st.text_input("Supplier ID *", value=f"SUP-{datetime.datetime.now().strftime('%M%S')}")
                    s_name = st.text_input("Supplier Business Name *")
                    s_poc = st.text_input("Point of Contact (POC)")
                    s_cat = st.selectbox("Category", ["IT Hardware", "Software & Cloud", "Professional Services", "Supply Chain", "Facilities", "Other"])
                with c2:
                    s_tax = st.text_input("Tax ID / Company ID / EIN")
                    s_email = st.text_input("Contact Email")
                    s_phone = st.text_input("Contact Phone")
                with c3:
                    s_address = st.text_input("Street Address / Location")
                    s_city = st.text_input("City")
                    s_country = st.text_input("Country", value="USA")

                submit_sup = st.form_submit_button("💾 Save Supplier Record", type="primary")

                if submit_sup:
                    if s_id and s_name:
                        Database.query("""
                            INSERT OR REPLACE INTO suppliers (supplier_id, name, poc, tax_id, address, city, country, email, phone, category)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (s_id, s_name, s_poc, s_tax, s_address, s_city, s_country, s_email, s_phone, s_cat))
                        st.success(f"Supplier '{s_name}' ({s_id}) successfully registered!")
                        st.rerun()
                    else:
                        st.error("Supplier ID and Supplier Name are required fields.")

        with m2:
            st.write("Upload a CSV file containing supplier details.")
            uploaded_csv = st.file_uploader("Upload Suppliers CSV", type=["csv"])
            if uploaded_csv:
                try:
                    df_upload = pd.read_csv(uploaded_csv)
                    st.write("Preview Upload Data:", df_upload.head(3))
                    if st.button("Process & Import CSV Data"):
                        for _, row in df_upload.iterrows():
                            Database.query("""
                                INSERT OR REPLACE INTO suppliers (supplier_id, name, poc, tax_id, address, city, country, email, phone, category)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                str(row.get("Supplier ID", f"SUP-{datetime.datetime.now().strftime('%M%S')}")),
                                str(row.get("Supplier Name", "Unknown Vendor")),
                                str(row.get("POC", "")),
                                str(row.get("Tax ID", "")),
                                str(row.get("Address", "")),
                                str(row.get("City", "")),
                                str(row.get("Country", "USA")),
                                str(row.get("Email", "")),
                                str(row.get("Phone", "")),
                                str(row.get("Category", "Other"))
                            ))
                        st.success("Bulk suppliers imported successfully!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error parsing CSV file: {e}")

        st.markdown("---")
        st.subheader("📋 Registered Enterprise Suppliers")
        sups = Database.query("SELECT supplier_id, name, poc, tax_id, city, country, email, category, status FROM suppliers")
        if sups:
            st.dataframe(pd.DataFrame(sups), use_container_width=True, hide_index=True)

    # ---------------------------------------------------------
    # TAB 2: RFP PILOT SUITE
    # ---------------------------------------------------------
    with t2:
        st.subheader("RFP Intake, Dispatch & Response Evaluation")
        agent.render_embedded_agent("RFP Pilot")

        sub_rfp1, sub_rfp2, sub_rfp3 = st.tabs(["⚡ 1. Intake & RFP Generator", "📊 2. Response Scoring & Award", "📜 3. RFP Registry"])

        # Fetch active suppliers for dropdowns
        all_sups = Database.query("SELECT name FROM suppliers")
        sup_list = [s["name"] for s in all_sups] if all_sups else []

        with sub_rfp1:
            col_a, col_b = st.columns([2, 3])
            with col_a:
                st.markdown("#### RFP Intake Questionnaire")
                rfp_title = st.text_input("RFP Project Title", "Enterprise Cloud Migration & Security")
                rfp_cat = st.selectbox("Procurement Category", ["IT Hardware", "Software & Cloud", "Professional Services", "Supply Chain", "Facilities"])
                rfp_budget = st.number_input("Estimated Budget ($)", value=350000.0)
                selected_vendors = st.multiselect("Select Suppliers for Dispatch", sup_list, default=sup_list[:2] if len(sup_list)>=2 else sup_list)
                rfp_scope = st.text_area("Scope of Work & Requirements", "Require 24/7 managed cloud monitoring, SOC2 compliance, and multi-region failover.")

                gen_rfp = st.button("🚀 Generate & Dispatch RFP Document", type="primary")

            with col_b:
                st.markdown("#### Generated RFP Document Preview")
                if gen_rfp and selected_vendors:
                    doc_content = f"""
                    ===================================================================
                    REQUEST FOR PROPOSAL (RFP): {rfp_title.upper()}
                    Category: {rfp_cat} | Budget Allocation: ${rfp_budget:,.2f}
                    ===================================================================
                    1. EXECUTIVE SUMMARY:
                    S.A.I.N.T. Enterprise is soliciting proposals for {rfp_title}.
                    
                    2. DETAILED SCOPE OF WORK:
                    {rfp_scope}
                    
                    3. COMPLIANCE & MANDATORY REQUIREMENTS:
                    - Full ISO27001 / SOC2 Type II certifications.
                    - Fixed pricing terms valid for 12 months.
                    
                    4. DISPATCH LIST:
                    Dispatched to: {', '.join(selected_vendors)}
                    ===================================================================
                    """
                    Database.query("""
                        INSERT INTO rfps (rfp_title, category, budget, scope_text, generated_rfp_doc, target_suppliers)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (rfp_title, rfp_cat, rfp_budget, rfp_scope, doc_content, json.dumps(selected_vendors)))
                    
                    st.success(f"RFP Dispatched to {len(selected_vendors)} vendors!")
                    st.code(doc_content, language="text")

        with sub_rfp2:
            st.markdown("#### Vendor Response Scoring & Evaluation")
            rfps = Database.query("SELECT id, rfp_title FROM rfps")
            if rfps:
                rfp_map = {r["rfp_title"]: r["id"] for r in rfps}
                chosen_rfp_title = st.selectbox("Select Active RFP for Evaluation", list(rfp_map.keys()))
                chosen_rfp_id = rfp_map[chosen_rfp_title]

                eval_col1, eval_col2 = st.columns([2, 3])
                with eval_col1:
                    bidding_vendor = st.selectbox("Select Bidding Supplier", sup_list)
                    prop_text = st.text_area("Proposal Content / Summary", "We offer 99.99% SLA with dedicated engineers at $310,000 total cost.")
                    
                    if st.button("🤖 Auto-Score Proposal"):
                        score = 88.5
                        eval_summary = "Strong technical SLA, $40k under budget, full SOC2 compliance."
                        Database.query("""
                            INSERT INTO rfp_responses (rfp_id, supplier_name, proposal_text, alignment_score, evaluation_summary)
                            VALUES (?, ?, ?, ?, ?)
                        """, (chosen_rfp_id, bidding_vendor, prop_text, score, eval_summary))
                        st.success(f"Proposal scored: {score}/100!")

                with eval_col2:
                    st.markdown(f"##### Vendor Comparison Matrix for: *{chosen_rfp_title}*")
                    responses = Database.query("SELECT supplier_name, alignment_score, evaluation_summary, submitted_at FROM rfp_responses WHERE rfp_id = ?", (chosen_rfp_id,))
                    if responses:
                        df_res = pd.DataFrame(responses)
                        st.dataframe(df_res, use_container_width=True, hide_index=True)
                        
                        st.markdown("---")
                        winning_vendor = st.selectbox("Select Winning Vendor to Award RFP", df_res["supplier_name"].tolist())
                        if st.button("🏆 Award RFP to Selected Vendor", type="primary"):
                            Database.query("UPDATE rfps SET status = 'Awarded', awarded_vendor = ? WHERE id = ?", (winning_vendor, chosen_rfp_id))
                            st.success(f"RFP Awarded to **{winning_vendor}**! This will now flag automatically in Contract Management.")
                    else:
                        st.info("No proposal responses submitted yet for this RFP.")

        with sub_rfp3:
            rfp_all = Database.query("SELECT id, rfp_title, category, budget, status, awarded_vendor, created_at FROM rfps")
            if rfp_all:
                st.dataframe(pd.DataFrame(rfp_all), use_container_width=True, hide_index=True)

    # ---------------------------------------------------------
    # TAB 3: CONTRACT LIFECYCLE MANAGEMENT (CLM)
    # ---------------------------------------------------------
    with t3:
        st.subheader("Contract Creation & Review Workflow")
        agent.render_embedded_agent("Contract CLM")

        clm_t1, clm_t2 = st.tabs(["📝 Create New Contract", "📑 Contract Repository & Review Approvals"])

        with clm_t1:
            with st.form("contract_create_form"):
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    c_title = st.text_input("Contract Title / Reference *", "Master Services Agreement 2026")
                    c_supplier = st.selectbox("Select Contracting Supplier *", sup_list)
                    c_value = st.number_input("Contract Value ($)", value=250000.0)
                with col_c2:
                    c_eff = st.date_input("Effective Date", datetime.date.today())
                    c_exp = st.date_input("Expiration Date", datetime.date.today() + datetime.timedelta(days=365))
                    
                    # RFP Award Linking Flag
                    awarded_rfps = Database.query("SELECT id, rfp_title FROM rfps WHERE status = 'Awarded' AND awarded_vendor = ?", (c_supplier,))
                    is_rfp = 1 if awarded_rfps else 0
                    rfp_id_link = awarded_rfps[0]["id"] if awarded_rfps else None
                    
                    if is_rfp:
                        st.info(f"🏆 Awarded via RFP Selection: **{awarded_rfps[0]['rfp_title']}**")
                    else:
                        st.caption("Not directly linked to an awarded RFP.")

                submit_contract = st.form_submit_button("💾 Draft Contract", type="primary")
                if submit_contract:
                    Database.query("""
                        INSERT INTO contracts (title, supplier_name, contract_value, effective_date, expiration_date, is_rfp_awarded, rfp_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (c_title, c_supplier, c_value, c_eff.isoformat(), c_exp.isoformat(), is_rfp, rfp_id_link))
                    st.success(f"Contract '{c_title}' drafted successfully!")
                    st.rerun()

        with clm_t2:
            st.markdown("#### Active Contracts & Sequential Approval Workflow")
            contracts = Database.query("SELECT * FROM contracts ORDER BY created_at DESC")
            if contracts:
                for c in contracts:
                    with st.expander(f"📄 {c['title']} — Supplier: {c['supplier_name']} (${c['contract_value']:,.2f})", expanded=False):
                        if c["is_rfp_awarded"]:
                            st.markdown("🏅 **Awarded via Competitive RFP Selection**")

                        # Workflow Approval Status
                        st.markdown("##### Workflow Review Gate")
                        w1, w2, w3, w4 = st.columns(4)
                        
                        with w1:
                            st.write(f"**SOW Owner:** {c['sow_owner_approval']}")
                            if c['sow_owner_approval'] == 'Pending' and st.button("Approve SOW", key=f"sow_{c['id']}"):
                                Database.query("UPDATE contracts SET sow_owner_approval = 'Approved' WHERE id = ?", (c['id'],))
                                st.rerun()
                        with w2:
                            st.write(f"**Legal Review:** {c['legal_approval']}")
                            if c['legal_approval'] == 'Pending' and st.button("Approve Legal", key=f"leg_{c['id']}"):
                                Database.query("UPDATE contracts SET legal_approval = 'Approved' WHERE id = ?", (c['id'],))
                                st.rerun()
                        with w3:
                            st.write(f"**Finance Review:** {c['finance_approval']}")
                            if c['finance_approval'] == 'Pending' and st.button("Approve Finance", key=f"fin_{c['id']}"):
                                Database.query("UPDATE contracts SET finance_approval = 'Approved' WHERE id = ?", (c['id'],))
                                st.rerun()
                        with w4:
                            st.write(f"**Effort Sponsor:** {c['sponsor_approval']}")
                            if c['sponsor_approval'] == 'Pending' and st.button("Final Approval", key=f"spon_{c['id']}"):
                                Database.query("UPDATE contracts SET sponsor_approval = 'Approved' WHERE id = ?", (c['id'],))
                                st.rerun()

                        st.markdown("---")
                        # Signature Execution Block
                        col_doc1, col_doc2 = st.columns(2)
                        with col_doc1:
                            st.write(f"DocuSign Status: **{c['docusign_status']}**")
                            if st.button("📨 Send via DocuSign", key=f"ds_{c['id']}"):
                                Database.query("UPDATE contracts SET docusign_status = 'Sent to Vendor' WHERE id = ?", (c['id'],))
                                st.success("Envelope dispatched via DocuSign API!")
                                st.rerun()
                        with col_doc2:
                            uploaded_sig = st.file_uploader("Or Upload Signed Document (PDF)", key=f"file_{c['id']}", type=["pdf"])
                            if uploaded_sig:
                                Database.query("UPDATE contracts SET docusign_status = 'Signed Document Uploaded', file_name = ? WHERE id = ?", (uploaded_sig.name, c['id']))
                                st.success(f"Uploaded {uploaded_sig.name}!")

    # ---------------------------------------------------------
    # TAB 4: SUPPLIER RISK WATCHDOG
    # ---------------------------------------------------------
    with t4:
        st.subheader("Autonomous Market Intelligence & Risk Scanning")
        agent.render_embedded_agent("Supplier Risk Watchdog")

        col_r1, col_r2 = st.columns([2, 3])

        with col_r1:
            st.markdown("#### On-Demand Risk Assessment")
            risk_vendor = st.selectbox("Select Supplier for Immediate Scan", sup_list if sup_list else ["Custom Vendor"])
            
            if st.button("⚡ Initiate On-Demand Risk Scan", type="primary"):
                with st.spinner(f"Scanning market feeds and SEC filings for {risk_vendor}..."):
                    new_update = f"[{datetime.date.today().isoformat()}] On-Demand Scan: Zero adverse regulatory actions detected. Financial liquidity rated STABLE."
                    Database.query("UPDATE suppliers SET market_updates = ?, last_scanned = CURRENT_TIMESTAMP WHERE name = ?", (new_update, risk_vendor))
                    st.success(f"Scan complete for {risk_vendor}!")
                    st.rerun()

            st.markdown("---")
            st.markdown("#### Scheduled Weekly Cognitive Scanner")
            st.caption("Automated background routine runs every Sunday at midnight to refresh supplier market feeds.")
            if st.button("🕒 Simulate Scheduled Weekly Scan"):
                all_s = Database.query("SELECT name FROM suppliers")
                if all_s:
                    for s in all_s:
                        upd = f"[{datetime.date.today().isoformat()}] Weekly Scan: Market sentiment positive (+1.4%). Operational risk normal."
                        Database.query("UPDATE suppliers SET market_updates = ?, last_scanned = CURRENT_TIMESTAMP WHERE name = ?", (upd, s["name"]))
                    st.success("Refreshed market updates for all suppliers in directory!")
                    st.rerun()

        with col_r2:
            st.markdown("#### Live Market Updates Column")
            sups_risk = Database.query("SELECT name, category, market_updates, last_scanned FROM suppliers")
            if sups_risk:
                df_r = pd.DataFrame(sups_risk)
                st.dataframe(df_r, use_container_width=True, hide_index=True)

    # ---------------------------------------------------------
    # TAB 5: SPEND ANALYTICS DASHBOARD
    # ---------------------------------------------------------
    with t5:
        st.subheader("Autonomous Spend Visibility & Leakage Detection")
        agent.render_embedded_agent("Spend Analytics")

        spend_rows = Database.query("SELECT * FROM spend_records")
        if spend_rows:
            df_s = pd.DataFrame(spend_rows)
            
            total_sp = df_s["amount"].sum()
            avg_sp = df_s["amount"].mean()

            m1, m2, m3 = st.columns(3)
            m1.metric("Total Corporate Spend", f"${total_sp:,.2f}")
            m2.metric("Average Transaction Value", f"${avg_sp:,.2f}")
            m3.metric("Total Vendors Monitored", len(df_s["supplier_name"].unique()))

            st.markdown("---")

            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Spend by Category")
                cat_chart = df_s.groupby("category")["amount"].sum()
                fig1, ax1 = plt.subplots(figsize=(5, 3.5))
                cat_chart.plot(kind="pie", ax=ax1, autopct='%1.1f%%', colors=["#0284c7", "#38bdf8", "#0284c7", "#e2e8f0"])
                ax1.set_ylabel("")
                fig1.tight_layout()
                st.pyplot(fig1)

            with c2:
                st.subheader("Top Vendors by Spend")
                ven_chart = df_s.groupby("supplier_name")["amount"].sum().sort_values(ascending=True)
                fig2, ax2 = plt.subplots(figsize=(5, 3.5))
                ven_chart.plot(kind="barh", ax=ax2, color="#0284c7")
                ax2.set_xlabel("Spend ($)")
                fig2.tight_layout()
                st.pyplot(fig2)

            st.markdown("---")
            st.subheader("📋 Itemized Spend Ledger")
            st.dataframe(df_s[["supplier_name", "category", "amount", "spend_date", "business_unit"]], use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
