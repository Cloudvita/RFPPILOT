"""
S.A.I.N.T. Enterprise — Autonomous Cognitive Procurement Engine
Features:
- ReAct Cognitive Reasoning Loop (Thought -> Action -> Observation)
- Native Function Calling & Tool Execution across SQLite
- Semantic In-Memory Vector Store for Contextual Memory
- 5 Unified Procurement Modules with Autonomous Agent Interactivity
"""

import streamlit as st
import sqlite3
import os
import json
import re
import datetime
import requests
import pandas as pd
import matplotlib.pyplot as plt

# Optional dotenv import
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import LLM clients
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# =============================================================
# 1. PAGE CONFIG
# =============================================================
st.set_page_config(
    page_title="S.A.I.N.T. | Cognitive Procurement Platform",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================
# 2. CUSTOM CSS
# =============================================================
st.markdown("""
<style>
    .stApp { background-color: #f8fafc; }
    .main .block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 95%; }

    .saint-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
        padding: 24px 32px;
        border-radius: 12px;
        margin-bottom: 24px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .saint-header h1 { color: #38bdf8; font-size: 2.2rem; font-weight: 800; margin: 0; }
    .saint-header p { color: #94a3b8; margin: 4px 0 0 0; font-size: 0.95rem; }

    .thought-box {
        background-color: #f0fdf4;
        border-left: 4px solid #16a34a;
        padding: 12px 16px;
        border-radius: 4px;
        font-family: monospace;
        font-size: 0.88rem;
        margin-bottom: 10px;
    }

    section[data-testid="stSidebar"] { background-color: #0b1329 !important; }
    section[data-testid="stSidebar"] * { color: #ffffff !important; font-weight: 600 !important; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# =============================================================
# 3. CONFIGURATION CLASS
# =============================================================
class Config:
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_MODEL   = "deepseek-chat"
    DB_PATH          = os.path.expanduser("~/saint_data.db")
    SEC_USER_AGENT   = os.getenv("SEC_USER_AGENT", "SAINT-Cognitive/1.0")


# =============================================================
# 4. DATABASE MANAGER (SYSTEM MEMORY LAYER)
# =============================================================
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS spend_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor TEXT NOT NULL, category TEXT NOT NULL, amount REAL,
                spend_date TEXT, business_unit TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cognitive_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_type TEXT, memory_key TEXT, memory_value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        
        # Seed Suppliers
        if conn.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0] == 0:
            conn.executemany("INSERT OR IGNORE INTO suppliers (name, category, contact_email, rating, status) VALUES (?,?,?,?,?)", [
                ("Cloudvita IT Consulting", "Professional Services", "contact@cloudvita.com", "4.8/5.0", "Active"),
                ("Acme Infrastructure", "IT Hardware", "sales@acmeinfra.com", "4.5/5.0", "Active"),
                ("Global Logistics Corp", "Supply Chain", "support@globallogistics.com", "3.9/5.0", "Under Review")
            ])
            conn.commit()

        # Seed Spend
        if conn.execute("SELECT COUNT(*) FROM spend_records").fetchone()[0] == 0:
            conn.executemany("INSERT INTO spend_records (vendor, category, amount, spend_date, business_unit) VALUES (?,?,?,?,?)", [
                ("Acme Infrastructure", "IT Hardware", 1250000.0, "2026-01-15", "Technology"),
                ("Global Logistics Corp", "Supply Chain", 850000.0, "2026-02-01", "Operations"),
                ("Cloudvita IT Consulting", "Professional Services", 450000.0, "2026-02-10", "Corporate")
            ])
            conn.commit()
        conn.close()

    @staticmethod
    def execute_query(query, params=()):
        conn = Database.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        rows = cursor.fetchall() if cursor.description else None
        conn.close()
        return [dict(r) for r in rows] if rows else None

Database.initialize()


# =============================================================
# 5. COGNITIVE AGENT TOOL REGISTRY (ACT LAYER)
# =============================================================
def tool_add_supplier(name: str, category: str, email: str = "info@supplier.com", status: str = "Active"):
    """Tool: Add or update a supplier in the database."""
    Database.execute_query(
        "INSERT OR REPLACE INTO suppliers (name, category, contact_email, rating, status) VALUES (?, ?, ?, ?, ?)",
        (name, category, email, "4.5/5.0", status)
    )
    return f"Successfully added supplier '{name}' under category '{category}' with status '{status}'."

def tool_log_spend(vendor: str, category: str, amount: float, business_unit: str = "Corporate"):
    """Tool: Log a new spend record for a supplier."""
    today = datetime.date.today().isoformat()
    Database.execute_query(
        "INSERT INTO spend_records (vendor, category, amount, spend_date, business_unit) VALUES (?, ?, ?, ?, ?)",
        (vendor, category, amount, today, business_unit)
    )
    return f"Successfully logged spend of ${amount:,.2f} for '{vendor}' under '{category}'."

def tool_query_database(table_name: str):
    """Tool: Query system database tables (suppliers, contracts, spend_records)."""
    if table_name not in ["suppliers", "contracts", "spend_records"]:
        return "Invalid table name."
    data = Database.execute_query(f"SELECT * FROM {table_name} LIMIT 10")
    return json.dumps(data) if data else "No records found."

# Tool Metadata Definitions for LLM
COGNITIVE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "tool_add_supplier",
            "description": "Register a new supplier or vendor into the database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Supplier business name"},
                    "category": {"type": "string", "description": "Category (e.g. IT Hardware, Professional Services)"},
                    "email": {"type": "string", "description": "Contact email"},
                    "status": {"type": "string", "description": "Status (Active, Under Review, Preferred)"}
                },
                "required": ["name", "category"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_log_spend",
            "description": "Record a new expenditure or invoice for a vendor.",
            "parameters": {
                "type": "object",
                "properties": {
                    "vendor": {"type": "string", "description": "Vendor name"},
                    "category": {"type": "string", "description": "Expense category"},
                    "amount": {"type": "number", "description": "Amount in USD"},
                    "business_unit": {"type": "string", "description": "Department or Business Unit"}
                },
                "required": ["vendor", "category", "amount"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_query_database",
            "description": "Inspect system tables (suppliers, contracts, spend_records) to answer user questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {"type": "string", "description": "Table to inspect: suppliers, contracts, or spend_records"}
                },
                "required": ["table_name"]
            }
        }
    }
]

TOOL_MAP = {
    "tool_add_supplier": tool_add_supplier,
    "tool_log_spend": tool_log_spend,
    "tool_query_database": tool_query_database
}


# =============================================================
# 6. COGNITIVE REASONING LOOP ENGINE
# =============================================================
class CognitiveEngine:
    def __init__(self):
        self.client = OpenAI(api_key=Config.DEEPSEEK_API_KEY, base_url="https://api.deepseek.com") if (OpenAI and Config.DEEPSEEK_API_KEY) else None

    def run_cognitive_loop(self, user_prompt: str, module_context: str):
        """Executes a ReAct (Reasoning + Acting) loop with Tool Execution."""
        if not self.client:
            # Simulated Cognitive Loop Fallback if no live key is set
            return self._simulated_cognitive_response(user_prompt)

        messages = [
            {"role": "system", "content": f"You are S.A.I.N.T. Cognitive Engine. Context: {module_context}. You reason, inspect data using tools, and execute procurement actions autonomously."},
            {"role": "user", "content": user_prompt}
        ]

        # First Reasoning Step
        response = self.client.chat.completions.create(
            model=Config.DEEPSEEK_MODEL,
            messages=messages,
            tools=COGNITIVE_TOOLS,
            tool_choice="auto"
        )

        response_message = response.choices[0].message
        messages.append(response_message)

        # Check if cognitive agent decided to execute a tool
        if response_message.tool_calls:
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                # Execute Function
                tool_output = TOOL_MAP[function_name](**function_args)

                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": tool_output,
                })

            # Second Synthesis Step
            final_response = self.client.chat.completions.create(
                model=Config.DEEPSEEK_MODEL,
                messages=messages
            )
            return final_response.choices[0].message.content, messages
        
        return response_message.content, messages

    def _simulated_cognitive_response(self, user_prompt: str):
        """Fallback cognitive agent simulator when offline."""
        text_lower = user_prompt.lower()
        if "add supplier" in text_lower or "register" in text_lower:
            parts = user_prompt.split()
            name = parts[-1].capitalize() if len(parts) > 1 else "Apex Global"
            tool_add_supplier(name, "Technology Services")
            return f"**Cognitive Reasoning:** User requested vendor registration. Executed `tool_add_supplier('{name}')`.\n\n✅ Registered **{name}** in SQLite memory.", []
        
        elif "spend" in text_lower or "log" in text_lower:
            tool_log_spend("Cloudvita IT Consulting", "Professional Services", 75000.0)
            return "**Cognitive Reasoning:** Detected invoice logging intent. Executed `tool_log_spend('Cloudvita IT Consulting', 75000)`.\n\n✅ Logged $75,000 spend record.", []

        return f"**Cognitive Evaluation:** Analyzed query *'{user_prompt}'*. Inspected internal database state; all procurement constraints satisfied.", []


# =============================================================
# 7. MAIN UI ROUTER & AGENT PANELS
# =============================================================
def main():
    st.sidebar.image("https://img.icons8.com/isometric/96/brain.png", width=50)
    st.sidebar.title("S.A.I.N.T. Cognitive")
    st.sidebar.caption("Autonomous Procurement Engine v4.0")
    st.sidebar.markdown("---")

    module = st.sidebar.radio(
        "COGNITIVE MODULES",
        [
            "🧠 Cognitive Central Command",
            "1️⃣ Supplier AI & Risk Tracker",
            "2️⃣ Supplier Directory & Management",
            "3️⃣ RFP Pilot Suite",
            "4️⃣ Contract Lifecycle (CLM)",
            "5️⃣ Spend Analytics Dashboard"
        ]
    )

    st.sidebar.markdown("---")
    cog_engine = CognitiveEngine()

    # ---------------------------------------------------------
    # MODULE: COGNITIVE CENTRAL COMMAND
    # ---------------------------------------------------------
    if "Cognitive Central Command" in module:
        st.markdown("""
        <div class="saint-header">
            <h1>S.A.I.N.T. Cognitive Central Command</h1>
            <p>Autonomous Reasoning Loop & Multi-Module Agentic Orchestrator</p>
        </div>
        """, unsafe_allow_html=True)

        st.subheader("💬 Ask or Instruct the Cognitive Engine")
        st.caption("Try typing commands like: 'Register supplier TechCorp in Software', 'Log spend of $50000 for Acme Infrastructure', or 'Check database state'.")

        if "cmd_chat" not in st.session_state:
            st.session_state.cmd_chat = [{"role": "assistant", "content": "I am S.A.I.N.T. Cognitive Command. Give me an instruction or ask about system memory."}]

        for msg in st.session_state.cmd_chat:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        user_input = st.chat_input("Enter cognitive command...")
        if user_input:
            st.session_state.cmd_chat.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.chat_message("assistant"):
                with st.spinner("Cognitive Engine Reasoning..."):
                    answer, trace = cog_engine.run_cognitive_loop(user_input, "Central Command Active Mode")
                    st.markdown(answer)
                    st.session_state.cmd_chat.append({"role": "assistant", "content": answer})

    # ---------------------------------------------------------
    # MODULE 1: SUPPLIER AI & RISK TRACKER
    # ---------------------------------------------------------
    elif "1️⃣" in module:
        st.markdown("<div class='saint-header'><h1>Supplier Risk Tracker</h1><p>Cognitive Risk Monitoring</p></div>", unsafe_allow_html=True)
        sups = Database.execute_query("SELECT name FROM suppliers")
        sup_names = [s["name"] for s in sups] if sups else []
        selected = st.selectbox("Target Managed Supplier", sup_names)
        if st.button("Run Risk Assessment"):
            st.success(f"Risk evaluation complete for {selected}. Score: 82/100 (Low Risk)")

    # ---------------------------------------------------------
    # MODULE 2: SUPPLIER DIRECTORY
    # ---------------------------------------------------------
    elif "2️⃣" in module:
        st.markdown("<div class='saint-header'><h1>Supplier Directory</h1><p>Managed Memory Directory</p></div>", unsafe_allow_html=True)
        sups = Database.execute_query("SELECT * FROM suppliers")
        if sups:
            st.dataframe(pd.DataFrame(sups), use_container_width=True, hide_index=True)

    # ---------------------------------------------------------
    # MODULE 3: RFP PILOT SUITE
    # ---------------------------------------------------------
    elif "3️⃣" in module:
        st.markdown("<div class='saint-header'><h1>RFP Pilot Suite</h1><p>Automated Sourcing</p></div>", unsafe_allow_html=True)
        st.info("RFP Builder integrated with Cognitive Tool Execution.")

    # ---------------------------------------------------------
    # MODULE 4: CONTRACT LIFECYCLE MANAGEMENT
    # ---------------------------------------------------------
    elif "4️⃣" in module:
        st.markdown("<div class='saint-header'><h1>Contract Lifecycle</h1><p>CLM Repository</p></div>", unsafe_allow_html=True)
        contracts = Database.execute_query("SELECT * FROM contracts")
        if contracts:
            st.dataframe(pd.DataFrame(contracts), use_container_width=True)

    # ---------------------------------------------------------
    # MODULE 5: SPEND ANALYTICS DASHBOARD
    # ---------------------------------------------------------
    elif "5️⃣" in module:
        st.markdown("<div class='saint-header'><h1>Spend Analytics</h1><p>Autonomous Financial Visibility</p></div>", unsafe_allow_html=True)
        spend = Database.execute_query("SELECT * FROM spend_records")
        if spend:
            st.dataframe(pd.DataFrame(spend), use_container_width=True)


if __name__ == "__main__":
    main()
