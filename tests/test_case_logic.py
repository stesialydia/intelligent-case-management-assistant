from datetime import date

import pandas as pd

from case_logic import add_sla_columns, next_case_id, triage_case


def test_compliance_case_is_high_priority():
    result = triage_case("Urgent suspicious duplicate claim needs compliance investigation")
    assert result.category == "Compliance/Fraud"
    assert result.priority == "High"
    assert result.assigned_team == "Compliance Team"
    assert result.sla_days == 3
    assert result.confidence > 0


def test_payment_case_routes_to_payments():
    result = triage_case("Payment failed and the customer paid twice")
    assert result.category == "Payment Issue"
    assert result.priority == "Medium"
    assert result.assigned_team == "Payments Team"


def test_sla_columns_flag_overdue():
    df = pd.DataFrame([
        {"case_id": "CASE-0001", "status": "New", "submission_date": "2026-01-01", "sla_days": 3}
    ])
    enriched = add_sla_columns(df, today=date(2026, 1, 10))
    assert enriched.loc[0, "sla_status"] == "Overdue"


def test_next_case_id_increments():
    df = pd.DataFrame({"case_id": ["CASE-0001", "CASE-0009"]})
    assert next_case_id(df) == "CASE-0010"
