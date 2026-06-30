# Intelligent Case Management Assistant

A portfolio-ready, Power Platform-inspired case triage system for a public-sector tax/customer-service environment. The app uses synthetic data only and does **not** include real taxpayer, HMRC, customer, or personal data.

## Portfolio Summary

This project demonstrates how data science, automation, workflow design and operational dashboards can improve case-management processes. It mirrors the kind of low-code/no-code solution thinking used in Power Apps, Power Automate and Power BI, while being implemented as an accessible Python prototype.

## What It Does

- Generates synthetic case data with case identifiers, customer type, description, category, priority, routing team, status, submission date, SLA days, triage confidence, triage explanation and resolution notes.
- Classifies new case descriptions into:
  - Refund
  - Payment Issue
  - Compliance/Fraud
  - Missing Documents
  - General Query
- Scores priority using transparent rules:
  - High: fraud, suspicious, duplicate claim, overdue, urgent, legal, compliance.
  - Medium: refund delays and failed payments.
  - Low: missing documents and general queries.
- Routes work automatically:
  - Compliance/Fraud -> Compliance Team
  - Refund -> Refunds Team
  - Payment Issue -> Payments Team
  - Missing Documents and General Query -> Customer Support
- Tracks SLA deadlines, flags at-risk cases, and flags overdue cases.
- Captures an audit trail when cases are created or updated.
- Supports workflow status updates: New, In Progress, Escalated, Closed.
- Provides dashboard and manager views with interactive Plotly visuals.

## Architecture

```text
Synthetic Case Data
       |
       v
Streamlit User Interface
       |
       v
Triage Engine: keyword rules + TF-IDF similarity fallback
       |
       +--> Category classification
       +--> Priority scoring
       +--> Team routing
       +--> SLA assignment
       +--> Explainability note
       |
       v
CSV Persistence Layer + Audit Log
       |
       v
Operational Dashboards and Manager View
```

## Project Structure

```text
intelligent-case-management-assistant/
├── app.py                         # Streamlit app and user interface
├── case_logic.py                  # Classification, priority, routing and SLA logic
├── config.py                      # Shared categories, statuses, paths and mappings
├── data_store.py                  # CSV persistence and audit logging layer
├── generate_synthetic_data.py     # Synthetic dataset generator
├── requirements.txt
├── README.md
├── run_app.bat
├── data/
│   ├── synthetic_cases.csv
│   └── audit_log.csv              # Created after app interactions
├── screenshots/
│   └── .gitkeep
└── tests/
    └── test_case_logic.py
```

## Run Locally

### Fast Windows Option

Double-click `run_app.bat`, or run this from the project folder:

```powershell
.\run_app.bat
```

### Manual Option

1. Create and activate a virtual environment.

```bash
python -m venv .venv
.venv\Scripts\activate
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Generate or refresh the synthetic dataset.

```bash
python generate_synthetic_data.py
```

4. Start the Streamlit app.

```bash
streamlit run app.py
```

5. Optional: run tests.

```bash
pytest
```

## App Pages

- **Dashboard:** operational KPIs, category mix, priority split, workflow status, SLA status, team workload, and monthly trends.
- **New Case:** synthetic case submission form with automated classification, priority scoring, routing, SLA assignment and explainability note.
- **Case Review:** searchable case table with status and resolution-note updates.
- **Manager View:** team workload, SLA exposure, escalation queue and audit trail.

## Data Ethics Note

All records in `data/synthetic_cases.csv` are generated from fictional text templates. The project is designed to demonstrate case triage, NLP-assisted routing, workflow management and dashboarding patterns without using sensitive or personal information.
