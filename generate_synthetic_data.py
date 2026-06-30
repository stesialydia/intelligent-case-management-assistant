"""Generate a synthetic case dataset for the portfolio app.

This script intentionally uses fictional, non-personal case descriptions. It
does not contain or create taxpayer, customer, HMRC, or personal data.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from case_logic import parse_submission_date, triage_case
from config import CUSTOMER_TYPES, DATA_PATH as OUTPUT_PATH, STATUS_OPTIONS


RANDOM_SEED = 42

SYNTHETIC_DESCRIPTIONS = [
    "Customer reports a refund delay after an overpayment adjustment.",
    "A refund appears to have been approved but has not reached the account.",
    "Payment failed during online checkout, but the balance still appears due.",
    "Direct debit was declined and the customer needs the payment issue reviewed.",
    "Possible duplicate claim submitted with suspicious supporting details.",
    "Urgent compliance case: legal review requested for a suspicious claim.",
    "Case is overdue and may involve a duplicate refund request.",
    "Missing document: customer needs to upload proof for a recent application.",
    "Supporting evidence is incomplete and a required form is missing.",
    "General query about how to update account contact details.",
    "Customer asks for guidance about a deadline and available support options.",
    "Agent asks whether a letter was received and how to provide an attachment.",
    "Failed card payment caused an incorrect charge to appear twice.",
    "Refund delay after a repayment calculation was corrected.",
    "Compliance review requested because the claim may contain a false declaration.",
    "Customer cannot find the upload link for requested evidence.",
    "Urgent legal concern about suspicious changes to a submitted case.",
    "General question about service hours and expected response times.",
    "Payment issue: bank transfer reference was entered incorrectly.",
    "Customer provided documents but one attachment cannot be opened.",
]

RESOLUTION_NOTES = [
    "",
    "",
    "",
    "Initial checks completed; awaiting customer response.",
    "Routed to specialist team for review.",
    "Closed after synthetic validation and customer notification.",
    "Escalated due to SLA risk and case complexity.",
]


def generate_cases(row_count: int = 220) -> pd.DataFrame:
    """Create a deterministic synthetic dataset."""

    random.seed(RANDOM_SEED)
    today = date.today()
    rows = []

    for index in range(1, row_count + 1):
        description = random.choice(SYNTHETIC_DESCRIPTIONS)
        triage = triage_case(description)
        submitted = today - timedelta(days=random.randint(0, 120))
        status = random.choices(
            STATUS_OPTIONS,
            weights=[0.28, 0.35, 0.12, 0.25],
            k=1,
        )[0]

        if status == "Closed":
            note = "Closed after synthetic review; no real customer data used."
        else:
            note = random.choice(RESOLUTION_NOTES)

        rows.append(
            {
                "case_id": f"CASE-{index:04d}",
                "customer_type": random.choice(CUSTOMER_TYPES),
                "case_description": description,
                "category": triage.category,
                "priority": triage.priority,
                "assigned_team": triage.assigned_team,
                "status": status,
                "submission_date": parse_submission_date(submitted),
                "sla_days": triage.sla_days,
                "triage_confidence": triage.confidence,
                "triage_explanation": triage.explanation,
                "resolution_notes": note,
            }
        )

    return pd.DataFrame(rows)


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df = generate_cases()
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Generated {len(df)} synthetic cases at {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
