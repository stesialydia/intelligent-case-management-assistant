"""Shared configuration for the Intelligent Case Management Assistant."""

from pathlib import Path

DATA_PATH = Path("data/synthetic_cases.csv")
AUDIT_LOG_PATH = Path("data/audit_log.csv")

CATEGORIES = [
    "Refund",
    "Payment Issue",
    "Compliance/Fraud",
    "Missing Documents",
    "General Query",
]

PRIORITY_ORDER = ["High", "Medium", "Low"]
STATUS_OPTIONS = ["New", "In Progress", "Escalated", "Closed"]

CUSTOMER_TYPES = [
    "Individual",
    "Small Business",
    "Agent",
    "Charity",
    "Public Body",
]

TEAMS_BY_CATEGORY = {
    "Compliance/Fraud": "Compliance Team",
    "Refund": "Refunds Team",
    "Payment Issue": "Payments Team",
    "Missing Documents": "Customer Support",
    "General Query": "Customer Support",
}

SLA_DAYS_BY_PRIORITY = {
    "High": 3,
    "Medium": 7,
    "Low": 14,
}
