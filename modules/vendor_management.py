import streamlit as st

def render_vendor_management_module():
    """
    Renders Step 1: Candidate Vendor Directory Management
    Captures: Vendor Name, Point of Contact, and Email Address.
    """
    st.markdown('<div class="main-header"><h1>🏢 Step 1: Candidate Vendor Directory</h1><p>Manage candidate vendors, contact representatives, and target emails for RFP distribution.</p></div>', unsafe_allow_html=True)

    # Initialize default vendor list if not present
    if "vendors" not in st.session_state:
        st.session_state.vendors = [
            {
                "id": 1,
                "selected": True,
                "name": "Apex Digital Solutions (Vendor A)",
                "poc": "Sarah Jenkins (VP Enterprise)",
                "email": "rfp-team@apexdigital.com"
            },
            {
                "id": 2,
                "selected": True,
                "name": "Nexus Enterprise Systems (Vendor B)",
                "poc": "Marcus Vance (Account Executive)",
                "email": "proposals@nexussystems.com"
            },
            {
                "id": 3,
                "selected": True,
                "name": "Vanguard Tech Innovations (Vendor C)",
                "poc": "Elena Rostova (Client Director)",
                "email": "enterprise-sales@vanguardtech.io"
            }
        ]

    # Add New Vendor Container
    with st.expander("➕ Add New Candidate Vendor", expanded=True):
        with st.form("add_vendor_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                v_name = st.text_input("Vendor Name *", placeholder="e.g. Acme Cloud Systems")
            with col2:
                v_poc = st.text_input("Point of Contact (POC) *", placeholder="e.g. Jane Doe (Account Rep)")
            with col3:
                v_email = st.text_input("Account Representative Email *", placeholder="e.g. jane.doe@acmecloud.com")

            submit_v = st.form_submit_button("💾 Save Vendor to Directory", use_container_width=True, type="primary")
            if submit_v:
                if v_name and v_poc and v_email:
                    new_id = max([v["id"] for v in st.session_state.vendors], default=0) + 1
                    st.session_state.vendors.append({
                        "id": new_id,
                        "selected": True,
                        "name": v_name,
                        "poc": v_poc,
                        "email": v_email
                    })
                    st.success(f"Vendor '{v_name}' successfully added!")
                    st.rerun()
                else:
                    st.error("Please fill in all 3 required fields: Vendor Name, Point of Contact, and Email.")

    st.divider()

    # Manage Existing Vendors Table / Card List
    st.markdown("### 📋 Active Vendor Roster")
    st.caption("Review or update registered vendors below.")

    if not st.session_state.vendors:
        st.info("No vendors currently registered. Use the form above to add vendor records.")
        return

    updated_vendors = []
    cols = st.columns(3)
    for idx, vendor in enumerate(st.session_state.vendors):
        col_target = cols[idx % 3]
        with col_target:
            with st.container(border=True):
                st.markdown(f"#### 🏢 {vendor['name']}")
                name_val = st.text_input("Vendor Name", value=vendor["name"], key=f"v_name_{vendor['id']}")
                poc_val = st.text_input("Point of Contact", value=vendor["poc"], key=f"v_poc_{vendor['id']}")
                email_val = st.text_input("Contact Email", value=vendor["email"], key=f"v_email_{vendor['id']}")
                sel_val = st.checkbox("Active Distribution Target", value=vendor["selected"], key=f"v_sel_{vendor['id']}")
                
                if st.button("🗑️ Remove", key=f"del_v_{vendor['id']}", type="secondary", use_container_width=True):
                    st.session_state.vendors = [v for v in st.session_state.vendors if v["id"] != vendor["id"]]
                    st.toast(f"Removed vendor {vendor['name']}", icon="🗑️")
                    st.rerun()

                updated_vendors.append({
                    "id": vendor["id"],
                    "selected": sel_val,
                    "name": name_val,
                    "poc": poc_val,
                    "email": email_val
                })

    st.session_state.vendors = updated_vendors
    active_count = sum(1 for v in st.session_state.vendors if v["selected"])
    st.info(f"📌 **Directory Summary:** {len(st.session_state.vendors)} total vendors registered ({active_count} selected for active RFP distribution).")
