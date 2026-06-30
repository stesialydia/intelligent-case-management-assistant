"""Reusable triage logic for the Intelligent Case Management Assistant.

The project uses synthetic public-sector case records only. Classification is
implemented with transparent keyword rules plus a lightweight scikit-learn text
similarity fallback so the behaviour is explainable in a portfolio review.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable

import pandas as pd

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:  # pragma: no cover - exercised only in lean local runtimes
    TfidfVectorizer = None
    cosine_similarity = None


CATEGORIES = [
    "Refund",
    "Payment Issue",
    "Compliance/Fraud",
    "Missing Documents",
    "General Query",
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

STATUS_OPTIONS = ["New", "In Progress", "Escalated", "Closed"]

KEYWORDS_BY_CATEGORY = {
    "Compliance/Fraud": [
        "fraud",
        "fraudulent",
        "suspicious",
        "duplicate claim",
        "duplicate refund",
        "legal",
        "compliance",
        "investigation",
        "identity",
        "false declaration",
    ],
    "Refund": [
        "refund",
        "repayment",
        "rebate",
        "overpaid",
        "overpayment",
        "refund delay",
        "waiting for refund",
    ],
    "Payment Issue": [
        "payment",
        "failed payment",
        "card declined",
        "direct debit",
        "bank transfer",
        "incorrect charge",
        "paid twice",
    ],
    "Missing Documents": [
        "missing document",
        "document",
        "evidence",
        "upload",
        "attachment",
        "proof",
        "letter",
        "form",
    ],
    "General Query": [
        "question",
        "query",
        "guidance",
        "how do i",
        "update details",
        "change address",
        "deadline",
        "account access",
    ],
}

HIGH_PRIORITY_TERMS = [
    "fraud",
    "suspicious",
    "duplicate claim",
    "duplicate refund",
    "overdue",
    "urgent",
    "legal",
    "compliance",
    "investigation",
]

MEDIUM_PRIORITY_TERMS = [
    "refund delay",
    "waiting for refund",
    "failed payment",
    "payment failed",
    "card declined",
    "paid twice",
]

LOW_PRIORITY_TERMS = [
    "missing document",
    "document",
    "evidence",
    "general",
    "question",
    "guidance",
    "update details",
]

TRAINING_EXAMPLES = [
    ("I need an update on my delayed refund after overpaying", "Refund"),
    ("The refund has not arrived and the customer is waiting", "Refund"),
    ("Payment failed but the money appears to have left the account", "Payment Issue"),
    ("The direct debit was declined and the balance still shows unpaid", "Payment Issue"),
    ("This looks like a suspicious duplicate claim and needs investigation", "Compliance/Fraud"),
    ("Potential fraud and legal compliance review required", "Compliance/Fraud"),
    ("The supporting document is missing from the case upload", "Missing Documents"),
    ("Please attach proof of identity and the missing form", "Missing Documents"),
    ("Customer asks for guidance on account access and deadlines", "General Query"),
    ("General query about updating contact details", "General Query"),
]


@dataclass(frozen=True)
class TriageResult:
    category: str
    priority: str
    assigned_team: str
    sla_days: int


def normalise_text(text: str) -> str:
    """Return lower-case text suitable for keyword matching."""

    return " ".join(str(text or "").lower().split())


def _contains_any(text: str, terms: Iterable[str]) -> bool:
    return any(term in text for term in terms)


def classify_category(description: str) -> str:
    """Classify case text into the portfolio categories.

    The deterministic rules run first. If none match, a small TF-IDF similarity
    model compares the description to synthetic labelled examples.
    """

    text = normalise_text(description)
    for category, keywords in KEYWORDS_BY_CATEGORY.items():
        if _contains_any(text, keywords):
            return category

    example_texts = [item[0] for item in TRAINING_EXAMPLES]
    labels = [item[1] for item in TRAINING_EXAMPLES]

    if TfidfVectorizer is not None and cosine_similarity is not None:
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
        matrix = vectorizer.fit_transform(example_texts + [text])
        scores = cosine_similarity(matrix[-1], matrix[:-1]).flatten()
        return labels[int(scores.argmax())] if scores.max() > 0 else "General Query"

    # Simple offline fallback for environments that have not installed sklearn.
    input_terms = set(text.split())
    best_label = "General Query"
    best_score = 0
    for example_text, label in TRAINING_EXAMPLES:
        score = len(input_terms.intersection(normalise_text(example_text).split()))
        if score > best_score:
            best_label = label
            best_score = score
    return best_label


def score_priority(description: str, category: str) -> str:
    """Assign priority from trigger terms and category-level defaults."""

    text = normalise_text(description)
    if category == "Compliance/Fraud" or _contains_any(text, HIGH_PRIORITY_TERMS):
        return "High"
    if category in {"Refund", "Payment Issue"} or _contains_any(text, MEDIUM_PRIORITY_TERMS):
        return "Medium"
    if category in {"Missing Documents", "General Query"} or _contains_any(text, LOW_PRIORITY_TERMS):
        return "Low"
    return "Low"


def route_case(category: str) -> str:
    """Return the assigned service team for a category."""

    return TEAMS_BY_CATEGORY.get(category, "Customer Support")


def triage_case(description: str) -> TriageResult:
    """Classify, score, route, and set SLA for a submitted case."""

    category = classify_category(description)
    priority = score_priority(description, category)
    assigned_team = route_case(category)
    sla_days = SLA_DAYS_BY_PRIORITY[priority]
    return TriageResult(category, priority, assigned_team, sla_days)


def calculate_sla_status(row: pd.Series, today: date | None = None) -> str:
    """Return On Track, At Risk, Overdue, or Closed for one case row."""

    if row.get("status") == "Closed":
        return "Closed"

    today = today or date.today()
    submitted = pd.to_datetime(row["submission_date"]).date()
    deadline = submitted + timedelta(days=int(row["sla_days"]))
    days_remaining = (deadline - today).days

    if days_remaining < 0:
        return "Overdue"
    if days_remaining <= 2:
        return "At Risk"
    return "On Track"


def add_sla_columns(df: pd.DataFrame, today: date | None = None) -> pd.DataFrame:
    """Add deadline, days remaining, and SLA status columns to case data."""

    if df.empty:
        return df.copy()

    enriched = df.copy()
    today = today or date.today()
    submitted = pd.to_datetime(enriched["submission_date"])
    deadlines = submitted + pd.to_timedelta(enriched["sla_days"].astype(int), unit="D")
    enriched["deadline_date"] = deadlines.dt.date.astype(str)
    enriched["days_remaining"] = [(deadline.date() - today).days for deadline in deadlines]
    enriched["sla_status"] = enriched.apply(calculate_sla_status, axis=1, today=today)
    return enriched


def next_case_id(df: pd.DataFrame) -> str:
    """Create the next readable case identifier."""

    if df.empty or "case_id" not in df.columns:
        return "CASE-0001"

    numeric_ids = (
        df["case_id"]
        .astype(str)
        .str.extract(r"(\d+)$", expand=False)
        .dropna()
        .astype(int)
    )
    next_id = int(numeric_ids.max()) + 1 if not numeric_ids.empty else len(df) + 1
    return f"CASE-{next_id:04d}"


def parse_submission_date(value: str | date | datetime) -> str:
    """Store submission dates consistently as ISO strings."""

    return pd.to_datetime(value).date().isoformat()
