# Intelligent Case Management Assistant

A portfolio-ready, Power Platform-inspired case triage system for a public-sector tax/customer-service environment. The app uses synthetic data only and does not include real taxpayer, HMRC, customer, or personal data.

## What It Does

- Generates synthetic case data with case identifiers, customer type, description, category, priority, routing team, status, submission date, SLA days, and resolution notes.
- Classifies new case descriptions into:
  - Refund
  - Payment Issue
  - Compliance/Fraud
  - Missing Documents
  - General Query
- Scores priority from transparent rules:
  - High: fraud, suspicious, duplicate claim, overdue, urgent, legal, compliance.
  - Medium: refund delays and failed payments.
  - Low: missing documents and general queries.
- Routes work automatically:
  - Compliance/Fraud -> Compliance Team
  - Refund -> Refunds Team
  - Payment Issue -> Payments Team
  - Missing Documents and General Query -> Customer Support
- Tracks SLA deadlines, flags at-risk cases, and flags overdue cases.
- Supports status updates: New, In Progress, Escalated, Closed.
- Provides dashboard and manager views with interactive Plotly visuals.

## Project Structure

```text
intelligent-case-management-assistant/
|-- app.py
|-- case_logic.py
|-- generate_synthetic_data.py
|-- requirements.txt
|-- README.md
|-- run_app.bat
|-- data/
|   `-- synthetic_cases.csv
`-- screenshots/
    `-- .gitkeep
```

## Run Locally

### Fast Windows Option

Double-click `run_app.bat`, or run this from the project folder:

```powershell
.\run_app.bat
```

The script creates a virtual environment, installs dependencies, refreshes the synthetic dataset, and starts Streamlit.

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

## App Pages

- **Dashboard:** operational KPIs, category mix, priority split, open vs closed cases, SLA status, team workload, and monthly trends.
- **New Case:** synthetic case submission form with automated classification, priority scoring, routing, and SLA assignment.
- **Case Review:** searchable case table with status and resolution-note updates.
- **Manager View:** team workload, SLA exposure, and a queue of at-risk or overdue open cases.

## Data Ethics Note

All records in `data/synthetic_cases.csv` are generated from fictional text templates. The project is designed to demonstrate case triage, NLP-assisted routing, workflow management, and dashboarding patterns without using sensitive or personal information.

## Suggested Screenshots

The `screenshots` folder is included as a placeholder. After running the app, capture:

- Dashboard overview
- New case submission
- Case review update flow
- Manager SLA view
