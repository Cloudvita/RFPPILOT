import os
import time
from typing import Dict, Any

def generate_mock_rfp(intake_data: Dict[str, str]) -> str:
    """
    Generates a structured, professional RFP Markdown document using template expansion
    when no API key is available or as a fallback for offline demonstration.
    """
    outcomes = intake_data.get("q1_outcomes", "Achieve operational efficiency, scale infrastructure, and lower total cost of ownership.")
    scope = intake_data.get("q2_scope", "End-to-end software integration, cloud migration, and workflow automation.")
    tech_reqs = intake_data.get("q3_tech", "REST APIs, microservices architecture, OAuth2 authentication, scalable databases.")
    timeline = intake_data.get("q4_timeline", "6-month delivery timeline with bi-weekly sprint reviews.")
    budget = intake_data.get("q5_budget", "Target budget cap $250,000 with milestone-based payment schedules.")
    sla = intake_data.get("q6_sla", "99.9% service uptime, < 15 min critical issue response time, 24/7 coverage.")
    compliance = intake_data.get("q7_security", "SOC 2 Type II, ISO 27001, GDPR compliance, end-to-end data encryption.")
    support = intake_data.get("q8_support", "Dedicated technical account manager, tier-3 engineering escalation, SLA guarantees.")
    vendor_qual = intake_data.get("q9_qualifications", "5+ years enterprise track record, minimum 3 reference clients in fintech/healthcare.")
    pricing = intake_data.get("q10_pricing", "Fixed-fee milestone payments with optional maintenance tier add-ons.")

    doc = f"""# REQUEST FOR PROPOSAL (RFP)
## Enterprise Solution & Strategic Partnership

**Document Reference:** RFP-SAINT-{int(time.time())}  
**Date:** {time.strftime('%B %d, %Y')}  
**Status:** Active Distribution  

---

### 1. EXECUTIVE SUMMARY & OBJECTIVES
The Sponsor Organization is requesting proposals from qualified vendors to deliver an end-to-end solution alignment.

#### Core RFP Program Objectives:
{outcomes}

---

### 2. SCOPE OF WORK & SYSTEM BOUNDARIES
The selected vendor will be responsible for planning, executing, and sustaining the following key scope areas:
- **Primary Scope:** {scope}
- **Implementation Methodology:** Agile development methodology with phased milestone validation.
- **Deliverables:** Technical architecture design, system integration, deployment scripts, documentation, and user enablement workshops.

---

### 3. TECHNICAL & SYSTEM REQUIREMENTS
Proposals must demonstrate complete alignment with the following core architectural requirements:
- **Technical Architecture:** {tech_reqs}
- **Data Integrity & Interoperability:** Standardized JSON/REST APIs with modular microservices design.
- **Scalability:** System must handle continuous workload scaling with auto-recovery and zero-downtime deployments.

---

### 4. TIMELINE, PHASING & DELIVERABLES
- **Project Schedule & Key Milestones:** {timeline}
- **Phasing Plan:** Phase 1 (Discovery & Architecture) -> Phase 2 (Core Build & Integration) -> Phase 3 (UAT & Go-Live).

---

### 5. BUDGETARY CONSTRAINTS & COST STRUCTURE
- **Target Budget Frame:** {budget}
- **Pricing Breakdown:** {pricing}
- **Billing Schedule:** Payment tied directly to verified milestone sign-offs.

---

### 6. SERVICE LEVEL AGREEMENTS (SLA) & SUPPORT MODEL
- **Uptime & Performance Guarantees:** {sla}
- **Support Infrastructure:** {support}

---

### 7. SECURITY, COMPLIANCE & RISK MANAGEMENT
- **Regulatory Framework:** {compliance}
- **Data Protection:** Data must be encrypted both at rest (AES-256) and in transit (TLS 1.3).
- **Audit & Governance:** Mandatory annual penetration testing and compliance audit reports.

---

### 8. VENDOR QUALIFICATIONS & REFERENCES
- **Capabilities & Experience:** {vendor_qual}
- **Reference Checks:** Submit minimum 3 case studies of similar scale deployments.

---

### 9. SUBMISSION GUIDELINES & PROPOSAL INSTRUCTIONS
1. **Submission Format:** Electronic submission via official RFP portal or direct response upload.
2. **Response Structure:** Must include Executive Summary, Technical Response Grid, Pricing Schedule, and SLA Commitments.
3. **Evaluation Criteria:** Responses will be evaluated across Technical Alignment, Cost Value, SLA Guarantees, Compliance, and Vendor Track Record.
"""
    return doc


def generate_rfp_document(api_key: str, intake_data: Dict[str, str]) -> tuple[str, str]:
    """
    Constructs a formal, structured RFP document using Mistral AI API or fallback mock generator.
    Returns a tuple of (generated_rfp_text, status_message).
    """
    if not api_key:
        return generate_mock_rfp(intake_data), "Generated using Mock LLM Engine (No API Key provided)."

    prompt = f"""
You are an expert Enterprise Solutions Architect and Procurement Officer drafting a formal Request for Proposal (RFP) document.
Below are 10 brief intake constraints supplied by the project sponsor (each constrained to under 200 characters).

Your task is to expand these concise inputs into a comprehensive, highly formal, professional, and well-structured Markdown RFP document.
Ensure the output includes Executive Summary, Detailed Scope of Work, Technical Requirements, Phased Timeline, Budget & Pricing Guidelines, SLA & Support Framework, Security & Compliance, Vendor Qualification Criteria, and Proposal Submission Guidelines.

Intake Responses:
1. Program Objectives / Top 3 Outcomes: {intake_data.get('q1_outcomes', '')}
2. Scope of Work: {intake_data.get('q2_scope', '')}
3. Technical Requirements: {intake_data.get('q3_tech', '')}
4. Timeline & Phasing: {intake_data.get('q4_timeline', '')}
5. Budget Constraints: {intake_data.get('q5_budget', '')}
6. Service Level Agreements (SLA): {intake_data.get('q6_sla', '')}
7. Security & Compliance: {intake_data.get('q7_security', '')}
8. Support Model: {intake_data.get('q8_support', '')}
9. Vendor Qualifications: {intake_data.get('q9_qualifications', '')}
10. Pricing Structure & Payment Terms: {intake_data.get('q10_pricing', '')}

Format the response in clean, professional GitHub-flavored Markdown with headers, callout sections, bullet points, and clear instructions for responding vendors.
"""

    # Attempt to call Mistral SDK v1+ or fallback
    try:
        from mistralai import Mistral
        client = Mistral(api_key=api_key)
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[
                {"role": "system", "content": "You are a professional enterprise procurement officer creating structured RFPs."},
                {"role": "user", "content": prompt}
            ]
        )
        rfp_text = response.choices[0].message.content
        return rfp_text, "Successfully generated using Mistral AI API."

    except ImportError:
        # Try older mistralai SDK if v1 isn't installed
        try:
            from mistralai.client import MistralClient
            from mistralai.models.chat_completion import ChatMessage
            client = MistralClient(api_key=api_key)
            response = client.chat(
                model="mistral-small-latest",
                messages=[ChatMessage(role="user", content=prompt)]
            )
            rfp_text = response.choices[0].message.content
            return rfp_text, "Successfully generated using Mistral AI API (Legacy SDK)."
        except Exception as e:
            return generate_mock_rfp(intake_data), f"Mistral API Error ({str(e)}). Fallback mock generator used."

    except Exception as e:
        return generate_mock_rfp(intake_data), f"Mistral API Error ({str(e)}). Fallback mock generator used."
