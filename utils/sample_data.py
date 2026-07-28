import json
import pandas as pd
from typing import Dict, List, Any

# Standard 8-10 evaluation parameters
DEFAULT_PARAMETERS = [
    "Technical Alignment",
    "Cost / Value Proposition",
    "SLA & Support Model",
    "Security & Compliance",
    "Vendor Experience & Track Record",
    "Architecture Scalability",
    "Risk Profile & Governance",
    "Implementation Timeline"
]

DEFAULT_WEIGHTS = {
    "Technical Alignment": 0.20,
    "Cost / Value Proposition": 0.20,
    "SLA & Support Model": 0.15,
    "Security & Compliance": 0.15,
    "Vendor Experience & Track Record": 0.10,
    "Architecture Scalability": 0.10,
    "Risk Profile & Governance": 0.05,
    "Implementation Timeline": 0.05
}

def get_sample_vendor_scores() -> pd.DataFrame:
    """
    Returns a pandas DataFrame containing sample vendor response scores (1-10 scale)
    across the 8 evaluation parameters.
    """
    sample_data = [
        {
            "Vendor": "Apex Digital Solutions (Vendor A)",
            "Technical Alignment": 9,
            "Cost / Value Proposition": 7,
            "SLA & Support Model": 8,
            "Security & Compliance": 9,
            "Vendor Experience & Track Record": 8,
            "Architecture Scalability": 9,
            "Risk Profile & Governance": 8,
            "Implementation Timeline": 7,
            "Comments": "Strong cloud native architecture with SOC 2 compliance. Slightly higher price point."
        },
        {
            "Vendor": "Nexus Enterprise Systems (Vendor B)",
            "Technical Alignment": 7,
            "Cost / Value Proposition": 9,
            "SLA & Support Model": 7,
            "Security & Compliance": 8,
            "Vendor Experience & Track Record": 9,
            "Architecture Scalability": 8,
            "Risk Profile & Governance": 7,
            "Implementation Timeline": 9,
            "Comments": "Highly competitive pricing and fast 4-month timeline. Legacy module compatibility required."
        },
        {
            "Vendor": "Vanguard Tech Innovations (Vendor C)",
            "Technical Alignment": 8,
            "Cost / Value Proposition": 6,
            "SLA & Support Model": 9,
            "Security & Compliance": 10,
            "Vendor Experience & Track Record": 9,
            "Architecture Scalability": 8,
            "Risk Profile & Governance": 9,
            "Implementation Timeline": 8,
            "Comments": "Industry leader in security and compliance with 24/7 dedicated support team."
        }
    ]
    return pd.DataFrame(sample_data)

def parse_uploaded_file(uploaded_file) -> tuple[pd.DataFrame | None, str]:
    """
    Parses uploaded CSV or JSON file into a standardized DataFrame for evaluation scoring.
    """
    try:
        filename = uploaded_file.name.lower()
        if filename.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
            return df, "CSV file uploaded successfully."
        elif filename.endswith(".json"):
            data = json.load(uploaded_file)
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                df = pd.DataFrame([data])
            else:
                return None, "Invalid JSON structure. Expected a list of objects or single object."
            return df, "JSON file uploaded successfully."
        else:
            return None, "Unsupported file format. Please upload a .csv or .json file."
    except Exception as e:
        return None, f"Error parsing uploaded file: {str(e)}"
