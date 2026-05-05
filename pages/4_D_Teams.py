"""
D-Teams page: browse every D-Team.

For each D-Team we show:
  - Name and date
  - How many distinct people participated
  - Round breakdown
  - Status breakdown (active, completed, etc.)
"""

from collections import Counter, defaultdict

import pandas as pd
import streamlit as st

from lib.airtable import load_dteams, load_dteam_membership, pick
from lib.ui import render_sidebar


def format_breakdown(counter: Counter) -> str:
    """Turn a Counter into a readable inline string like 'a (5), b (3)'."""
    if not counter:
        return ""
    return ", ".join(
        f"{label} ({count})"
        for label, count in sorted(counter.items(), key=lambda x: -x[1])
    )

st.set_page_config(page_title="D-Teams · DCI", layout="wide")
render_sidebar()

st.title("D-Teams")
st.markdown(
    "DCI's small-group deliberation format. Each D-Team brings a "
    "small cohort of students, faculty, staff, or community members "
    "together over multiple rounds to deliberate on a contested topic."
)


# -----------------------------------------------------------------------------
# Load.
# -----------------------------------------------------------------------------
try:
    with st.spinner("Loading D-Teams…"):
        dteams = load_dteams()
        members = load_dteam_membership()
except Exception as e:
    st.error(f"Couldn't reach Airtable: {e}")
    st.stop()


# -----------------------------------------------------------------------------
# Aggregate membership by D-Team.
# -----------------------------------------------------------------------------
participants_per_team: dict = defaultdict(set)
rounds_per_team: dict = defaultdict(Counter)
status_per_team: dict = defaultdict(Counter)
roles_per_team: dict = defaultdict(Counter)

for row in members:
    f = row["fields"]
    did = f.get("dteam_id")
    pid = f.get("person_id")
    if did is None:
        continue
    if pid is not None:
        participants_per_team[did].add(pid)
    if f.get("round"):
        rounds_per_team[did][f["round"]] += 1
    if f.get("status"):
        status_per_team[did][f["status"]] += 1
    if f.get("role"):
        roles_per_team[did][f["role"]] += 1


# -----------------------------------------------------------------------------
# Flat table of D-Teams.
# -----------------------------------------------------------------------------
rows = []
for record in dteams:
    f = record["fields"]
    did = f.get("dteam_id")
    name = pick(f, ["name", "dteam_name", "Name", "title"], default=f"D-Team {did}")
    date = pick(f, ["date", "start_date", "Date"], default="")
    rows.append(
        {
            "D-Team": str(name),
            "Date": str(date) if date else "",
            "Participants": len(participants_per_team.get(did, set())),
            "Rounds": len(rounds_per_team.get(did, Counter())),
            "_dteam_id": did,
        }
    )

if not rows:
    st.warning("No D-Teams found in the D Team table.")
    st.stop()

dteams_df = pd.DataFrame(rows)


# -----------------------------------------------------------------------------
# Filter / sort controls.
# -----------------------------------------------------------------------------
col_search, col_sort = st.columns([3, 1])
with col_search:
    search = st.text_input(
        "Search by D-Team name",
        placeholder="e.g., Free Speech, Climate, Immigration",
    )
with col_sort:
    sort_by = st.selectbox(
        "Sort by",
        ["Participants (high to low)", "Date (newest first)", "Date (oldest first)", "Name (A-Z)"],
    )

filtered = dteams_df
if search:
    filtered = filtered[filtered["D-Team"].str.lower().str.contains(search.lower(), na=False)]

if sort_by == "Participants (high to low)":
    filtered = filtered.sort_values("Participants", ascending=False)
elif sort_by == "Date (newest first)":
    filtered = filtered.sort_values("Date", ascending=False)
elif sort_by == "Date (oldest first)":
    filtered = filtered.sort_values("Date", ascending=True)
elif sort_by == "Name (A-Z)":
    filtered = filtered.sort_values("D-Team")

st.caption(f"Showing {len(filtered):,} of {len(dteams_df):,} D-Team(s).")


# -----------------------------------------------------------------------------
# Render.
# -----------------------------------------------------------------------------
st.dataframe(
    filtered.drop(columns=["_dteam_id"]),
    use_container_width=True,
    hide_index=True,
)

st.divider()
st.subheader("D-Team details")

for _, row in filtered.head(50).iterrows():
    did = row["_dteam_id"]
    header = f"{row['D-Team']}  ·  {row['Participants']:,} participant(s)"
    if row["Rounds"]:
        header += f"  ·  {row['Rounds']} round(s)"
    if row["Date"]:
        header += f"  ·  {row['Date']}"

    with st.expander(header):
        # The header already shows participant count, rounds, and
        # date. Inside the expander, just narrate the role and status
        # breakdowns as plain sentences, no metric cards.
        roles_text = format_breakdown(roles_per_team.get(did, Counter()))
        if roles_text:
            st.markdown(f"By role: {roles_text}.")

        status_text = format_breakdown(status_per_team.get(did, Counter()))
        if status_text:
            st.markdown(f"By status: {status_text}.")

        if not (roles_text or status_text):
            st.caption("No additional details recorded for this D-Team.")

if len(filtered) > 50:
    st.caption(
        f"{len(filtered) - 50:,} more D-Teams not expanded below. Use "
        f"the search box to narrow them down."
    )
