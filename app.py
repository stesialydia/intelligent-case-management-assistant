"""Streamlit app for an Intelligent Case Management Assistant."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from case_logic import (
    STATUS_OPTIONS,
    add_sla_columns,
    next_case_id,
    parse_submission_date,
    triage_case,
)
from generate_synthetic_data import CUSTOMER_TYPES, generate_cases


DATA_PATH = Path("data/synthetic_cases.csv")
PRIORITY_ORDER = ["High", "Medium", "Low"]


st.set_page_config(
    page_title="Intelligent Case Management Assistant",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def load_cases() -> pd.DataFrame:
    """Load synthetic cases, creating the sample CSV when needed."""

    if not DATA_PATH.exists():
        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        generate_cases().to_csv(DATA_PATH, index=False)
    return pd.read_csv(DATA_PATH)


def save_cases(df: pd.DataFrame) -> None:
    """Persist case updates to the local CSV store."""

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATA_PATH, index=False)
    st.cache_data.clear()


def metric_card(label: str, value: int | str, help_text: str | None = None) -> None:
    st.metric(label=label, value=value, help=help_text)


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Render shared filters and return the filtered dataset."""

    with st.sidebar:
        st.header("Filters")
        categories = st.multiselect("Category", sorted(df["category"].unique()), default=[])
        priorities = st.multiselect("Priority", PRIORITY_ORDER, default=[])
        statuses = st.multiselect("Status", STATUS_OPTIONS, default=[])
        teams = st.multiselect("Assigned team", sorted(df["assigned_team"].unique()), default=[])

    filtered = df.copy()
    if categories:
        filtered = filtered[filtered["category"].isin(categories)]
    if priorities:
        filtered = filtered[filtered["priority"].isin(priorities)]
    if statuses:
        filtered = filtered[filtered["status"].isin(statuses)]
    if teams:
        filtered = filtered[filtered["assigned_team"].isin(teams)]
    return filtered


def chart_count(df: pd.DataFrame, column: str, title: str, color: str | None = None):
    counts = df[column].value_counts().rename_axis(column).reset_index(name="cases")
    if counts.empty:
        st.info("No cases match the current filters.")
        return
    fig = px.bar(counts, x=column, y="cases", color=color or column, title=title)
    fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig, use_container_width=True)


def dashboard_page(df: pd.DataFrame) -> None:
    st.title("Intelligent Case Management Assistant")
    st.caption("Synthetic public-sector case triage dashboard. No real taxpayer, customer, or personal data.")

    open_cases = df[df["status"] != "Closed"]
    at_risk = df[df["sla_status"] == "At Risk"]
    overdue = df[df["sla_status"] == "Overdue"]

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        metric_card("Total cases", len(df))
    with col2:
        metric_card("Open cases", len(open_cases))
    with col3:
        metric_card("Closed cases", int((df["status"] == "Closed").sum()))
    with col4:
        metric_card("At risk", len(at_risk), "Open cases within two days of SLA deadline.")
    with col5:
        metric_card("Overdue", len(overdue), "Open cases past SLA deadline.")

    left, right = st.columns(2)
    with left:
        chart_count(df, "category", "Cases by Category")
        chart_count(df, "assigned_team", "Cases by Assigned Team")
    with right:
        chart_count(df, "priority", "Cases by Priority")
        chart_count(df, "status", "Open vs Closed and Workflow Status")

    sla_counts = df["sla_status"].value_counts().rename_axis("sla_status").reset_index(name="cases")
    trend = df.copy()
    trend["submission_month"] = pd.to_datetime(trend["submission_date"]).dt.to_period("M").astype(str)
    trend_counts = trend.groupby("submission_month", as_index=False).size().rename(columns={"size": "cases"})

    left, right = st.columns(2)
    with left:
        fig = px.bar(sla_counts, x="sla_status", y="cases", color="sla_status", title="SLA Position")
        fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig, use_container_width=True)
    with right:
        fig = px.line(trend_counts, x="submission_month", y="cases", markers=True, title="Monthly Case Trend")
        fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig, use_container_width=True)


def new_case_page(df: pd.DataFrame) -> None:
    st.title("New Case")
    st.caption("Submit a fictional case description to classify, prioritise, route, and set an SLA.")

    with st.form("new_case_form", clear_on_submit=True):
        customer_type = st.selectbox("Customer type", CUSTOMER_TYPES)
        description = st.text_area(
            "Case description",
            height=150,
            placeholder="Example: Customer reports a failed payment and needs the balance corrected.",
        )
        submitted = st.date_input("Submission date", value=date.today())
        submit = st.form_submit_button("Classify and save case", type="primary")

    if submit:
        if not description.strip():
            st.error("Enter a synthetic case description before submitting.")
            return

        triage = triage_case(description)
        new_row = {
            "case_id": next_case_id(df),
            "customer_type": customer_type,
            "case_description": description.strip(),
            "category": triage.category,
            "priority": triage.priority,
            "assigned_team": triage.assigned_team,
            "status": "New",
            "submission_date": parse_submission_date(submitted),
            "sla_days": triage.sla_days,
            "resolution_notes": "",
        }
        updated = pd.concat([df.drop(columns=[c for c in ["deadline_date", "days_remaining", "sla_status"] if c in df]), pd.DataFrame([new_row])], ignore_index=True)
        save_cases(updated)
        st.success(f"{new_row['case_id']} saved and routed to {triage.assigned_team}.")
        st.dataframe(pd.DataFrame([new_row]), use_container_width=True, hide_index=True)


def case_review_page(df: pd.DataFrame) -> None:
    st.title("Case Review")
    st.caption("Review synthetic cases, update workflow status, and add resolution notes.")

    if df.empty:
        st.info("No cases available.")
        return

    display_columns = [
        "case_id",
        "category",
        "priority",
        "assigned_team",
        "status",
        "submission_date",
        "deadline_date",
        "days_remaining",
        "sla_status",
    ]
    st.dataframe(df[display_columns], use_container_width=True, hide_index=True)

    selected_case = st.selectbox("Select case to update", df["case_id"].tolist())
    selected = df[df["case_id"] == selected_case].iloc[0]

    with st.form("case_update_form"):
        st.write(f"**Description:** {selected['case_description']}")
        new_status = st.selectbox("Status", STATUS_OPTIONS, index=STATUS_OPTIONS.index(selected["status"]))
        resolution_notes = st.text_area("Resolution notes", value=str(selected.get("resolution_notes", "") or ""), height=120)
        update = st.form_submit_button("Save update", type="primary")

    if update:
        base = load_cases()
        mask = base["case_id"] == selected_case
        base.loc[mask, "status"] = new_status
        base.loc[mask, "resolution_notes"] = resolution_notes.strip()
        save_cases(base)
        st.success(f"{selected_case} updated.")


def manager_page(df: pd.DataFrame) -> None:
    st.title("Manager View")
    st.caption("Operational view for workload, SLA exposure, and escalation priorities.")

    open_df = df[df["status"] != "Closed"].copy()
    team_summary = (
        open_df.groupby(["assigned_team", "priority"], as_index=False)
        .size()
        .rename(columns={"size": "open_cases"})
        .sort_values(["assigned_team", "priority"])
    )

    sla_summary = (
        open_df.groupby(["assigned_team", "sla_status"], as_index=False)
        .size()
        .rename(columns={"size": "cases"})
    )

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Open Workload by Team and Priority")
        st.dataframe(team_summary, use_container_width=True, hide_index=True)
    with col2:
        st.subheader("SLA Exposure by Team")
        st.dataframe(sla_summary, use_container_width=True, hide_index=True)

    urgent = open_df[open_df["sla_status"].isin(["At Risk", "Overdue"])].copy()
    priority_rank = {"High": 0, "Medium": 1, "Low": 2}
    sla_rank = {"Overdue": 0, "At Risk": 1}
    urgent["priority_rank"] = urgent["priority"].map(priority_rank).fillna(3)
    urgent["sla_rank"] = urgent["sla_status"].map(sla_rank).fillna(2)
    urgent = urgent.sort_values(
        ["sla_rank", "priority_rank", "days_remaining"],
        ascending=[True, True, True],
    )
    st.subheader("Cases Requiring Attention")
    if urgent.empty:
        st.success("No at-risk or overdue open cases under current filters.")
    else:
        st.dataframe(
            urgent[
                [
                    "case_id",
                    "category",
                    "priority",
                    "assigned_team",
                    "status",
                    "deadline_date",
                    "days_remaining",
                    "sla_status",
                    "case_description",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )


def main() -> None:
    raw_cases = load_cases()
    cases = add_sla_columns(raw_cases)

    page = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "New Case", "Case Review", "Manager View"],
    )
    filtered_cases = apply_filters(cases)

    if page == "Dashboard":
        dashboard_page(filtered_cases)
    elif page == "New Case":
        new_case_page(raw_cases)
    elif page == "Case Review":
        case_review_page(filtered_cases)
    else:
        manager_page(filtered_cases)


if __name__ == "__main__":
    main()
