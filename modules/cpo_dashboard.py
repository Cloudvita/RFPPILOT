import streamlit as st
import pandas as pd

def render_cpo_dashboard_module():
    """
    Renders Step 4: Chief Procurement Officer (CPO) Historical Dashboard
    Provides CPO executive visibility into all past RFPs run, vendor selections, and score audits.
    """
    st.markdown('<div class="main-header"><h1>👑 Step 4: Chief Procurement Officer (CPO) Historical Dashboard</h1><p>Executive governance portal to track, review, and audit all historical RFP procurement cycles.</p></div>', unsafe_allow_html=True)

    rfp_history = st.session_state.get("historical_rfps", [])

    if not rfp_history:
        st.info("No historical RFP records found. Run an RFP cycle in Step 2 & Step 3 to view CPO analytics.")
        return

    # Executive Overview KPI Cards
    total_rfps = len(rfp_history)
    awarded_rfps = sum(1 for r in rfp_history if r.get("winning_vendor") != "Pending Evaluation")
    pending_rfps = total_rfps - awarded_rfps
    
    unique_vendors = set()
    for r in rfp_history:
        for v in r.get("dispatched_vendors", []):
            unique_vendors.add(v)

    st.markdown("### 📊 Executive Portfolio Overview")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total RFPs Executed", total_rfps)
    with m2:
        st.metric("Vendor Selections Awarded", awarded_rfps)
    with m3:
        st.metric("Pending Evaluations", pending_rfps)
    with m4:
        st.metric("Unique Vendors Participated", len(unique_vendors))

    st.divider()

    # Master Historical Registry Table
    st.markdown("### 📜 Master RFP Historical Registry")
    st.caption("Consolidated audit trail of all historical RFP programs.")

    summary_rows = []
    for r in rfp_history:
        summary_rows.append({
            "RFP Reference ID": r.get("id"),
            "Program Title": r.get("title"),
            "Date Dispatched": r.get("timestamp"),
            "Dispatched Vendors": ", ".join(r.get("dispatched_vendors", [])),
            "Selected Winner": r.get("winning_vendor", "Pending Evaluation"),
            "Status": r.get("status", "Dispatched")
        })

    registry_df = pd.DataFrame(summary_rows)
    st.dataframe(registry_df, use_container_width=True)

    st.divider()

    # Detailed Audit Inspector
    st.markdown("### 🔍 Detailed RFP Program Audit Inspector")
    st.caption("Select a past RFP program to inspect complete intake, generated artifact, vendor scores, and evaluator notes.")

    rfp_options = {f"{r['id']} - {r['title']}": r for r in rfp_history}
    chosen_label = st.selectbox("Select Historical RFP to Audit:", list(rfp_options.keys()))
    chosen_rfp = rfp_options[chosen_label]

    st.markdown(f"#### Audit Details for **{chosen_rfp['title']}** (`{chosen_rfp['id']}`)")
    
    col_a1, col_a2 = st.columns(2)
    with col_a1:
        st.markdown(f"**Date Dispatched:** {chosen_rfp.get('timestamp')}")
        st.markdown(f"**Current Status:** {chosen_rfp.get('status')}")
    with col_a2:
        st.markdown(f"**Winning Vendor Selected:** 🏆 `{chosen_rfp.get('winning_vendor')}`")

    audit_tab1, audit_tab2, audit_tab3 = st.tabs(["📄 Generated RFP Document", "📊 Vendor Scores & Notes", "🏢 Dispatched Vendors"])

    with audit_tab1:
        with st.container(border=True):
            st.markdown(chosen_rfp.get("rfp_text", "*No RFP Document text recorded.*"))

    with audit_tab2:
        scores_data = chosen_rfp.get("scores", [])
        if scores_data:
            scores_df = pd.DataFrame(scores_data)
            st.dataframe(scores_df, use_container_width=True)
        else:
            st.info("Evaluation scoring pending or not yet finalized for this RFP.")

    with audit_tab3:
        st.markdown("##### Candidate Vendors Dispatched:")
        for vname in chosen_rfp.get("dispatched_vendors", []):
            st.markdown(f"- **{vname}**")
