# SAINT_APP - End-to-End Request for Proposal (RFP) Prototype

A production-ready, modular Streamlit web application that serves as an enterprise Request for Proposal (RFP) lifecycle platform.

## 🚀 Key Modules

### Module 1: RFP Builder & Vendor Distribution
- **Candidate Vendor Directory**: Dynamically add, edit, and select vendors with dedicated account representative emails.
- **Sponsor Questionnaire Intake**: 10 standardized core requirement fields with strict 200-character limits and visual character count tracking.
- **Mistral LLM Integration**: Generates formal, expanded Markdown RFP documents using Mistral AI (or intelligent mock generator fallback).
- **Export & Vendor Dispatch**: Download generated RFPs as `.md` or `.txt` and simulate email dispatch to selected vendor representatives.

### Module 2: Response Evaluation & Scoring Dashboard
- **Vendor Response Upload**: Upload CSV or JSON vendor response matrices or click "Load Sample Responses" for instant zero-setup testing.
- **Dynamic Scoring Framework**: 8 key evaluation parameters with customizable parameter weightings.
- **Interactive Scoring Grid**: Score vendors individually via tabbed UI views or interactive matrix data editor (`st.data_editor`).
- **Decision Matrix & Analytics**: Automated weighted score calculations, ranking badges, Plotly grouped bar charts, and multi-dimensional radar strength profiles.

---

## 🛠️ Installation & Quickstart

```bash
cd /Users/Prabhu/.gemini/antigravity/scratch/saint_app

# Install required dependencies
pip install -r requirements.txt

# Run the Streamlit Application
streamlit run app.py
```

---

## 🔑 Environment Variables (Optional)

Create a `.env` file or provide your Mistral API key directly in the app sidebar:
```env
MISTRAL_API_KEY=your_mistral_api_key_here
```
*Note: If no API key is set, the app gracefully falls back to an internal Mock LLM generator so all features can be tested offline without errors.*
