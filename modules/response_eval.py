import streamlit as st
import pandas as pd

try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

from utils.sample_data import get_sample_vendor_scores, DEFAULT_PARAMETERS, DEFAULT_WEIGHTS

def render_response_eval_module():
    """
    Renders Step 3: RFP Evaluation & Scoring
    """
    st.markdown('<div class="main-header"><h1>📊 Step 3: RFP Response Evaluation & Scoring</h1><p>Select an active RFP, score candidate vendor responses, and review decision analytics.</p></div>', unsafe_allow_html=True)

    # Initialize historical_rfps if not present
    if "historical_rfps" not in st.session_state or not st.session_state.historical_rfps:
        # Create default historical RFP for instant testing
        st.session_state.historical_rfps = [
            {
                "id": "RFP-2026-001",
                "title": "Enterprise Cloud & AI Migration RFP",
                "timestamp": "2026-07-26 10:00",
                "rfp_text": "Sample RFP Document...",
                "dispatched_vendors": [
                    "Apex Digital Solutions (Vendor A)",
                    "Nexus Enterprise Systems (Vendor B)",
                    "Vanguard Tech Innovations (Vendor C)"
                ],
                "status": "Dispatched",
                "winning_vendor": "Pending Evaluation",
                "scores": {}
            }
        ]

    rfp_list = st.session_state.historical_rfps
    rfp_options = {f"{r['id']} - {r['title']} ({r['timestamp']})": r for r in rfp_list}

    # ==========================================
    # SECTION 1: RFP SELECTOR
    # ==========================================
    st.markdown("### 🔍 1. Select RFP to Evaluate")
    selected_label = st.selectbox(
        "Choose Target RFP Program:",
        options=list(rfp_options.keys()),
        index=0
    )

    selected_rfp = rfp_options[selected_label]
    st.info(f"📌 **Evaluating RFP:** {selected_rfp['title']} | **Dispatched Vendors:** {', '.join(selected_rfp['dispatched_vendors'])}")

    st.divider()

    # ==========================================
    # SECTION 2: WEIGHTING & SCORING GRID
    # ==========================================
    st.markdown("### 📝 2. Vendor Scoring Grid & Evaluator Rationale")
    st.caption("Provide quantitative scores (1-10 scale) and qualitative evaluator notes for each vendor.")

    if "weights" not in st.session_state:
        st.session_state.weights = DEFAULT_WEIGHTS.copy()

    with st.expander("🎛️ Configure Evaluation Parameter Weights", expanded=False):
        w_cols = st.columns(4)
        new_weights = {}
        for idx, param in enumerate(DEFAULT_PARAMETERS):
            col_target = w_cols[idx % 4]
            with col_target:
                current_w = int(st.session_state.weights.get(param, 0.1) * 100)
                new_w = st.slider(f"{param}", min_value=1, max_value=50, value=max(current_w, 5), step=1, key=f"w_eval_{param}")
                new_weights[param] = new_w

        total_w = sum(new_weights.values())
        normalized_weights = {k: v / total_w for k, v in new_weights.items()}
        st.session_state.weights = normalized_weights

    # Generate or retrieve vendor score dataset for selected RFP
    target_vendors = selected_rfp["dispatched_vendors"]
    
    # Store scores per RFP in session state
    rfp_score_key = f"score_data_{selected_rfp['id']}"
    if rfp_score_key not in st.session_state:
        # Build initial dataframe for target vendors
        init_rows = []
        for idx, vname in enumerate(target_vendors):
            row = {"Vendor": vname, "Notes / Rationale": f"Evaluator feedback for {vname}."}
            # Give reasonable initial default scores
            base_score = 9 - idx
            for p in DEFAULT_PARAMETERS:
                row[p] = max(min(base_score + (1 if len(p)%2==0 else -1), 10), 5)
            init_rows.append(row)
        st.session_state[rfp_score_key] = pd.DataFrame(init_rows)

    df_eval = st.session_state[rfp_score_key].copy()

    # Score editing tabs for each vendor
    tabs = st.tabs([f"🏢 {vname}" for vname in target_vendors])

    for idx, tab in enumerate(tabs):
        with tab:
            vname = target_vendors[idx]
            st.markdown(f"#### Quantitative Scoring & Notes for **{vname}**")
            
            # Find row index for vendor
            v_idx_list = df_eval.index[df_eval["Vendor"] == vname].tolist()
            row_idx = v_idx_list[0] if v_idx_list else 0

            s_cols = st.columns(2)
            for p_idx, param in enumerate(DEFAULT_PARAMETERS):
                col_target = s_cols[p_idx % 2]
                with col_target:
                    curr_val = int(df_eval.at[row_idx, param]) if param in df_eval.columns else 7
                    score_val = st.slider(
                        f"{param} (Weight: {st.session_state.weights[param]*100:.1f}%)",
                        min_value=1,
                        max_value=10,
                        value=curr_val,
                        key=f"s_{selected_rfp['id']}_{idx}_{param}"
                    )
                    df_eval.at[row_idx, param] = score_val

            notes_val = st.text_area(
                "Qualitative Evaluator Notes & Rationale",
                value=str(df_eval.at[row_idx, "Notes / Rationale"]) if "Notes / Rationale" in df_eval.columns else "",
                key=f"notes_{selected_rfp['id']}_{idx}",
                height=90
            )
            df_eval.at[row_idx, "Notes / Rationale"] = notes_val

    st.session_state[rfp_score_key] = df_eval

    st.divider()

    # ==========================================
    # SECTION 3: DECISION ANALYTICS & GRAPH
    # ==========================================
    st.markdown("### 📈 3. Consolidated Decision Analytics & Recommendation")

    df_calc = df_eval.copy()

    def calc_weighted_score(row):
        total = 0.0
        for param in DEFAULT_PARAMETERS:
            if param in row and param in st.session_state.weights:
                total += float(row[param]) * st.session_state.weights[param]
        return round(total, 2)

    df_calc["Weighted Total Score (Out of 10)"] = df_calc.apply(calc_weighted_score, axis=1)
    df_calc = df_calc.sort_values(by="Weighted Total Score (Out of 10)", ascending=False).reset_index(drop=True)

    winner_row = df_calc.iloc[0]

    # Winner Card
    st.markdown(f"""
    <div class="winner-card">
        <h3>🏆 Top Recommended Vendor: {winner_row['Vendor']}</h3>
        <p><strong>Overall Score:</strong> {winner_row['Weighted Total Score (Out of 10)']:.2f} / 10.0</p>
        <p><em>Notes: "{winner_row.get('Notes / Rationale', 'Top scores across key parameters.')}"</em></p>
    </div>
    """, unsafe_allow_html=True)

    # Save Evaluation to History Button
    if st.button("💾 Save Final Evaluation to RFP History", type="primary", use_container_width=True):
        # Update selected RFP in session state
        for r in st.session_state.historical_rfps:
            if r["id"] == selected_rfp["id"]:
                r["winning_vendor"] = winner_row['Vendor']
                r["status"] = "Evaluated & Awarded"
                r["scores"] = df_calc.to_dict(orient="records")
        st.success(f"Evaluation committed! Vendor '{winner_row['Vendor']}' officially saved as selected winner for {selected_rfp['id']}.")

    st.markdown("#### Consolidated Score Table")
    st.dataframe(df_calc, use_container_width=True)

    # Graphs
    st.markdown("#### Score Visualization")
    if HAS_PLOTLY:
        melted_df = pd.melt(
            df_calc,
            id_vars=["Vendor"],
            value_vars=DEFAULT_PARAMETERS,
            var_name="Parameter",
            value_name="Score (1-10)"
        )
        fig_bar = px.bar(
            melted_df,
            x="Parameter",
            y="Score (1-10)",
            color="Vendor",
            barmode="group",
            title=f"Vendor Comparison for {selected_rfp['title']}",
            height=450,
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        fig_bar.update_layout(xaxis_tickangle=-30, xaxis_title="")
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        chart_df = df_calc.set_index("Vendor")[DEFAULT_PARAMETERS].T
        st.bar_chart(chart_df)
