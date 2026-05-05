"""
Events page: browse every DCI event.

For each event we show:
  - The event name and date
  - How many distinct people attended
  - The ticket type breakdown for that event

The user can search by event name and sort by attendance or date.
"""

from collections import Counter, defaultdict

import pandas as pd
import streamlit as st

from lib.airtable import load_events, load_event_attendance, pick
from lib.ui import render_sidebar


def format_breakdown(counter: Counter) -> str:
    """Turn a Counter into a readable inline string like 'student (40), faculty (5)'."""
    if not counter:
        return ""
    return ", ".join(
        f"{label} ({count})"
        for label, count in sorted(counter.items(), key=lambda x: -x[1])
    )

st.set_page_config(page_title="Events · DCI", layout="wide")
render_sidebar()

st.title("Events")
st.markdown(
    "Every event DCI has hosted, with attendance counts and ticket "
    "type breakdown. Click any row to expand and see details."
)

# -----------------------------------------------------------------------------
# Load.
# -----------------------------------------------------------------------------
try:
    with st.spinner("Loading events…"):
        events = load_events()
        attendance = load_event_attendance()
except Exception as e:
    st.error(f"Couldn't reach Airtable: {e}")
    st.stop()


# -----------------------------------------------------------------------------
# Build per-event aggregates from the attendance table.
#
# We do one pass over attendance and bucket each row by event_id. For
# each event we collect the set of distinct attendees and a Counter
# of ticket types.
# -----------------------------------------------------------------------------
attendees_per_event: dict = defaultdict(set)
tickets_per_event: dict = defaultdict(Counter)

for row in attendance:
    f = row["fields"]
    eid = f.get("event_id")
    pid = f.get("person_id")
    ticket = f.get("ticket_type", "(none)")
    if eid is None:
        continue
    if pid is not None:
        attendees_per_event[eid].add(pid)
    tickets_per_event[eid][ticket] += 1


# -----------------------------------------------------------------------------
# Build a flat table of events with their counts.
# -----------------------------------------------------------------------------
rows = []
for record in events:
    f = record["fields"]
    eid = f.get("event_id")
    name = pick(f, ["name", "event_name", "Name", "title"], default=f"Event {eid}")
    date = pick(f, ["date", "event_date", "Date", "start_date"], default="")
    rows.append(
        {
            "Event": str(name),
            "Date": str(date) if date else "",
            "Attendees": len(attendees_per_event.get(eid, set())),
            "_event_id": eid,
        }
    )

if not rows:
    st.warning("No events found in the Event table.")
    st.stop()

events_df = pd.DataFrame(rows)


# -----------------------------------------------------------------------------
# Filter and sort controls.
# -----------------------------------------------------------------------------
col_search, col_sort = st.columns([3, 1])
with col_search:
    search = st.text_input(
        "Search by event name",
        placeholder="e.g., Davidson Forum",
    )
with col_sort:
    sort_by = st.selectbox(
        "Sort by",
        ["Attendees (high to low)", "Date (newest first)", "Date (oldest first)", "Name (A-Z)"],
    )

filtered = events_df
if search:
    filtered = filtered[filtered["Event"].str.lower().str.contains(search.lower(), na=False)]

if sort_by == "Attendees (high to low)":
    filtered = filtered.sort_values("Attendees", ascending=False)
elif sort_by == "Date (newest first)":
    filtered = filtered.sort_values("Date", ascending=False)
elif sort_by == "Date (oldest first)":
    filtered = filtered.sort_values("Date", ascending=True)
elif sort_by == "Name (A-Z)":
    filtered = filtered.sort_values("Event")

st.caption(f"Showing {len(filtered):,} of {len(events_df):,} event(s).")


# -----------------------------------------------------------------------------
# Render: a table at the top for scanning, then expanders for detail.
# -----------------------------------------------------------------------------
display_df = filtered.drop(columns=["_event_id"])
st.dataframe(display_df, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Event details")

for _, row in filtered.head(50).iterrows():
    eid = row["_event_id"]
    header = f"{row['Event']}  ·  {row['Attendees']:,} attendees"
    if row["Date"]:
        header += f"  ·  {row['Date']}"

    with st.expander(header):
        # Build one short sentence about who came, instead of a row of
        # metric cards. The header already shows attendee count and
        # date, so the expander only needs to add the ticket breakdown.
        ticket_text = format_breakdown(tickets_per_event.get(eid, Counter()))
        if ticket_text:
            st.markdown(f"By ticket type: {ticket_text}.")
        else:
            st.caption("No ticket type details recorded for this event.")

if len(filtered) > 50:
    st.caption(
        f"{len(filtered) - 50:,} more events not expanded below. Use the "
        f"search box to narrow them down."
    )
