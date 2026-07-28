import streamlit as st
import time
from utils.llm_helper import generate_rfp_document

DEFAULT_INTAKE_RESPONSES = {
    "q1_outcomes": "1. Modernize legacy workflow platform. 2. Achieve 99.99% system availability. 3. Reduce API latency under 100ms.",
    "q2_scope": "Full cloud-native platform migration, API gateway setup, microservices restructuring, and automated CI/CD pipeline implementation.",
    "q3_tech": "Python / FastAPI backend, React / TypeScript UI, PostgreSQL database, Docker & Kubernetes deployment, Kafka event streaming.",
    "q4_timeline": "Target 6-month timeline: Phase 1 Architecture (Mo 1-2), Phase 2 Core Build (Mo 3-4), Phase 3 Testing & Go-Live (Mo 5-6).",
    "q5_budget": "Target budget range: $200,000 - $300,000 with milestone payment release upon UAT acceptance.",
    "q6_sla": "99.9% uptime guarantee, < 15 min response time for Critical P1 incidents, 24/7 dedicated engineering support escalation.",
    "q7_security": "SOC 2 Type II certification mandatory, ISO 27001 compliance, GDPR compliance, AES-256 data encryption at rest and TLS 1.3 in transit.",
    "q8_support": "Dedicated Technical Account Manager, monthly status reviews, guaranteed 4-hour resolution for P2 issues, quarterly patch upgrades.",
    "q9_qualifications": "Minimum 5 years enterprise software integration experience, 3 verified customer references in financial or healthcare sectors.",
    "q10_pricing": "Fixed-price milestone structure, transparent maintenance & licensing tier costs, itemized hourly rate for out-of-scope work."
}

def render_rfp_builder_module(api_key: str = ""):
    """
    Renders Step 2: RFP Intake Questionnaire & Vendor Dispatch
    """
    st.markdown('<div class="main-header"><h1>📝 Step 2: RFP Builder & Vendor Dispatch</h1><p>Fill intake requirements, generate formal RFP via AI, and dispatch to selected vendors.</p></div>', unsafe_allow_html=True)

    if "intake_responses" not in st.session_state:
        st.session_state.intake_responses = DEFAULT_INTAKE_RESPONSES.copy()

    if "rfp_title" not in st.session_state:
        st.session_state.rfp_title = "Enterprise Platform Modernization RFP"

    if "generated_rfp" not in st.session_state:
        st.session_state.generated_rfp = ""

    if "dispatched_records" not in st.session_state:
        st.session_state.dispatched_records = []

    # Title & Save/Reset Top Toolbar
    t_col1, t_col2, t_col3 = st.columns([3, 1, 1])
    with t_col1:
        st.session_state.rfp_title = st.text_input("RFP Program Title", value=st.session_state.rfp_title)
    with t_col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 Save Intake", type="primary", use_container_width=True):
            st.toast("RFP intake responses saved to session state!", icon="💾")
    with t_col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Reset Intake", type="secondary", use_container_width=True):
            st.session_state.intake_responses = {
                "q1_outcomes": "List minimum or top 3 outcomes/objectives of the RFP program.",
                "q2_scope": "",
                "q3_tech": "",
                "q4_timeline": "",
                "q5_budget": "",
                "q6_sla": "",
                "q7_security": "",
                "q8_support": "",
                "q9_qualifications": "",
                "q10_pricing": ""
            }
            st.session_state.generated_rfp = ""
            st.toast("Intake form reset!", icon="🔄")
            st.rerun()

    st.divider()

    # Intake Form
    st.markdown("### 📋 RFP Intake Questionnaire (10 Core Requirements)")
    st.caption("Each field is strictly capped at 200 characters to enforce precise procurement objectives.")

    intake_questions = [
        ("q1_outcomes", "1. Program Objectives / Top 3 Outcomes (Pre-filled)", True),
        ("q2_scope", "2. Scope of Work & Core Deliverables", False),
        ("q3_tech", "3. Technical & Architectural Requirements", False),
        ("q4_timeline", "4. Project Timeline & Key Milestones", False),
        ("q5_budget", "5. Budget Constraints & Payment Structure", False),
        ("q6_sla", "6. Service Level Agreement (SLA) & Performance Limits", False),
        ("q7_security", "7. Security, Compliance & Governance Standards", False),
        ("q8_support", "8. Support Model & Escalation Protocols", False),
        ("q9_qualifications", "9. Vendor Qualifications & Reference Requirements", False),
        ("q10_pricing", "10. Pricing Structure & Rate Card Guidelines", False),
    ]

    col1, col2 = st.columns(2)
    current_responses = {}
    for idx, (q_key, q_label, is_prefilled) in enumerate(intake_questions):
        col_target = col1 if idx % 2 == 0 else col2
        with col_target:
            val = st.session_state.intake_responses.get(q_key, "")
            char_count = len(val)
            st.markdown(f"**{q_label}** <span style='float:right; font-size:12px; color:#888;'>{char_count}/200 chars</span>", unsafe_allow_html=True)
            resp = st.text_area(
                label=q_label,
                value=val,
                max_chars=200,
                height=100,
                key=f"input_{q_key}",
                label_visibility="collapsed"
            )
            current_responses[q_key] = resp

    st.session_state.intake_responses = current_responses

    st.divider()

    # Generate RFP Section
    st.markdown("### 🤖 LLM RFP Document Generation")
    if st.button("🚀 Generate Formal RFP Document", type="primary", use_container_width=True):
        with st.spinner("Mistral AI engine expanding 10 intake responses into formal Markdown RFP..."):
            generated_rfp, status_msg = generate_rfp_document(api_key, current_responses)
            st.session_state.generated_rfp = generated_rfp
            st.success(status_msg)

    if st.session_state.generated_rfp:
        with st.container(border=True):
            st.markdown("#### Generated Document Preview")
            st.markdown(st.session_state.generated_rfp)

        st.divider()

        # Vendor Selection & Dispatch
        st.markdown("### ✉️ Vendor Distribution & Dispatch")
        st.caption("Select destination vendors from Step 1 directory and send the generated RFP.")

        all_vendors = st.session_state.get("vendors", [])
        if not all_vendors:
            st.warning("No vendors found in Directory! Please add vendors in Step 1.")
            return

        st.markdown("##### Target Vendors Selection:")
        dispatch_selected_vendors = []
        v_cols = st.columns(3)
        for v_idx, vendor in enumerate(all_vendors):
            with v_cols[v_idx % 3]:
                is_chk = st.checkbox(
                    f"**{vendor['name']}**\n\nPOC: {vendor['poc']} ({vendor['email']})",
                    value=vendor.get("selected", True),
                    key=f"disp_chk_{vendor['id']}"
                )
                if is_chk:
                    dispatch_selected_vendors.append(vendor)

        st.markdown("<br>", unsafe_allow_html=True)
        d_col1, d_col2 = st.columns(2)

        with d_col1:
            if st.button("📨 Send RFP to Selected Vendors", type="primary", use_container_width=True):
                if not dispatch_selected_vendors:
                    st.error("Please select at least one vendor to dispatch.")
                else:
                    progress_bar = st.progress(0)
                    for idx, v in enumerate(dispatch_selected_vendors):
                        time.sleep(0.3)
                        progress_bar.progress((idx + 1) / len(dispatch_selected_vendors))
                    
                    # Create Historical Record
                    rfp_id = f"RFP-{int(time.time())}"
                    new_rfp_record = {
                        "id": rfp_id,
                        "title": st.session_state.rfp_title,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M"),
                        "rfp_text": st.session_state.generated_rfp,
                        "dispatched_vendors": [v["name"] for v in dispatch_selected_vendors],
                        "vendor_details": dispatch_selected_vendors,
                        "status": "Dispatched",
                        "winning_vendor": "Pending Evaluation",
                        "scores": {}
                    }

                    if "historical_rfps" not in st.session_state:
                        st.session_state.historical_rfps = []

                    st.session_state.historical_rfps.insert(0, new_rfp_record)
                    st.session_state.current_rfp_id = rfp_id
                    st.success(f"🎉 RFP '{st.session_state.rfp_title}' successfully dispatched to {len(dispatch_selected_vendors)} vendors!")

        with d_col2:
            if st.button("🔄 Reset / Start New RFP Run", type="secondary", use_container_width=True):
                st.session_state.generated_rfp = ""
                st.session_state.rfp_title = "New Enterprise Solution RFP"
                st.toast("Session reset for new RFP creation!", icon="🔄")
                st.rerun()
