"""CSV persistence helpers for the portfolio prototype.

For a production system, this layer would be replaced by Dataverse, PostgreSQL,
or another governed case-management datastore. Keeping storage isolated makes
that future migration straightforward.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from config import AUDIT_LOG_PATH, DATA_PATH
from generate_synthetic_data import generate_cases

CASE_COLUMNS = [
    "case_id",
    "customer_type",
    "case_description",
    "category",
    "priority",
    "assigned_team",
    "status",
    "submission_date",
    "sla_days",
    "triage_confidence",
    "triage_explanation",
    "resolution_notes",
]


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def migrate_cases(df: pd.DataFrame) -> pd.DataFrame:
    """Add missing portfolio columns to older generated datasets."""
    migrated = df.copy()
    defaults = {
        "triage_confidence": 0.95,
        "triage_explanation": "Generated synthetic seed case using portfolio triage rules.",
        "resolution_notes": "",
    }
    for column, default in defaults.items():
        if column not in migrated.columns:
            migrated[column] = default
    for column in CASE_COLUMNS:
        if column not in migrated.columns:
            migrated[column] = ""
    return migrated[CASE_COLUMNS]


def load_cases() -> pd.DataFrame:
    """Load synthetic cases, creating the sample CSV when needed."""
    if not DATA_PATH.exists():
        save_cases(generate_cases())
    return migrate_cases(pd.read_csv(DATA_PATH))


def save_cases(df: pd.DataFrame) -> None:
    """Persist case updates to the local CSV store."""
    _ensure_parent(DATA_PATH)
    migrate_cases(df).to_csv(DATA_PATH, index=False)


def append_audit_event(case_id: str, action: str, detail: str) -> None:
    """Append a lightweight audit trail row for portfolio evidence."""
    _ensure_parent(AUDIT_LOG_PATH)
    row = pd.DataFrame(
        [
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "case_id": case_id,
                "action": action,
                "detail": detail,
            }
        ]
    )
    if AUDIT_LOG_PATH.exists():
        existing = pd.read_csv(AUDIT_LOG_PATH)
        pd.concat([existing, row], ignore_index=True).to_csv(AUDIT_LOG_PATH, index=False)
    else:
        row.to_csv(AUDIT_LOG_PATH, index=False)


def load_audit_log() -> pd.DataFrame:
    """Load audit events for review in the manager view."""
    if not AUDIT_LOG_PATH.exists():
        return pd.DataFrame(columns=["timestamp", "case_id", "action", "detail"])
    return pd.read_csv(AUDIT_LOG_PATH)
