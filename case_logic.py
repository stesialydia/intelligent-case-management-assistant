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

from config import SLA_DAYS_BY_PRIORITY, STATUS_OPTIONS, TEAMS_BY_CATEGORY

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:  # pragma: no cover
    TfidfVectorizer = None
    cosine_similarity = None


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
        "payment failed",
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
    confidence: float
    explanation: str


def normalise_text(text: str) -> str:
    """Return lower-case text suitable for keyword matching."""
    return " ".join(str(text or "").lower().split())


def _matched_terms(text: str, terms: Iterable[str]) -> list[str]:
    """Return terms found in the normalised input text."""
    return [term for term in terms if term in text]


def classify_category(description: str) -> tuple[str, float, str]:
    """Classify case text and return category, confidence and reason."""
    text = normalise_text(description)
    for category, keywords in KEYWORDS_BY_CATEGORY.items():
        matches = _matched_terms(text, keywords)
        if matches:
            return category, 0.95, f"Keyword match: {', '.join(matches[:3])}"

    example_texts = [item[0] for item in TRAINING_EXAMPLES]
    labels = [item[1] for item in TRAINING_EXAMPLES]

    if TfidfVectorizer is not None and cosine_similarity is not None:
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
        matrix = vectorizer.fit_transform(example_texts + [text])
        scores = cosine_similarity(matrix[-1], matrix[:-1]).flatten()
        best_idx = int(scores.argmax())
        best_score = float(scores[best_idx])
        if best_score > 0:
            return labels[best_idx], round(max(0.55, min(best_score, 0.89)), 2), "TF-IDF similarity fallback"
        return "General Query", 0.4, "No strong match; routed as general query"

    input_terms = set(text.split())
    best_label = "General Query"
    best_score = 0
    for example_text, label in TRAINING_EXAMPLES:
        score = len(input_terms.intersection(normalise_text(example_text).split()))
        if score > best_score:
            best_label = label
            best_score = score
    if best_score > 0:
        return best_label, 0.55, "Token overlap fallback"
    return "General Query", 0.4, "No strong match; routed as general query"


def score_priority(description: str, category: str) -> tuple[str, str]:
    """Assign priority from trigger terms and category-level defaults."""
    text = normalise_text(description)
    high_matches = _matched_terms(text, HIGH_PRIORITY_TERMS)
    if category == "Compliance/Fraud" or high_matches:
        reason = "Compliance/fraud category" if category == "Compliance/Fraud" else f"High-priority trigger: {', '.join(high_matches[:3])}"
        return "High", reason

    medium_matches = _matched_terms(text, MEDIUM_PRIORITY_TERMS)
    if category in {"Refund", "Payment Issue"} or medium_matches:
        reason = f"Medium-priority category: {category}"
        if medium_matches:
            reason = f"Medium-priority trigger: {', '.join(medium_matches[:3])}"
        return "Medium", reason

    low_matches = _matched_terms(text, LOW_PRIORITY_TERMS)
    if category in {"Missing Documents", "General Query"} or low_matches:
        return "Low", f"Lower-risk category: {category}"
    return "Low", "Default low priority"


def route_case(category: str) -> str:
    """Return the assigned service team for a category."""
    return TEAMS_BY_CATEGORY.get(category, "Customer Support")


def triage_case(description: str) -> TriageResult:
    """Classify, score, route, set SLA and explain a submitted case."""
    category, confidence, category_reason = classify_category(description)
    priority, priority_reason = score_priority(description, category)
    assigned_team = route_case(category)
    sla_days = SLA_DAYS_BY_PRIORITY[priority]
    explanation = f"{category_reason}. {priority_reason}. Routed to {assigned_team}; SLA {sla_days} days."
    return TriageResult(category, priority, assigned_team, sla_days, confidence, explanation)


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
