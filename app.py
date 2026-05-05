"""
DCI Engagement Dashboard, main entry point.

This is a Streamlit app. Mental model:
  - You write a normal Python script, top to bottom.
  - Every call like st.title(...) draws something on the page.
  - When the user interacts (clicks, types), Streamlit re-runs the
    whole script and re-draws.

Multi-page setup:
  - Each `.py` file inside `pages/` shows up as its own page in the
    sidebar nav. Streamlit handles the routing automatically.
  - Shared connection / loader code lives in `lib/airtable.py`,
    so each page imports from one place instead of duplicating it.
"""

import streamlit as st

from lib.airtable import (
    load_people,
    load_event_attendance,
    load_dteam_membership,
    load_subscribed,
)
from lib.ui import render_sidebar

# -----------------------------------------------------------------------------
# Page config, has to be the FIRST Streamlit call.
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="DCI Engagement Dashboard",
    layout="wide",
)


# -----------------------------------------------------------------------------
# Helpers that turn raw records into the counts we want.
#
# We pull the full table from cache (so other pages can reuse it) and
# count distinct person_ids here. Walking 20K records in pure Python
# takes a fraction of a second, so this is fine.
# -----------------------------------------------------------------------------
def count_distinct_people(records: list) -> int:
    """Count distinct person_id values across a list of Airtable records."""
    distinct = set()
    for record in records:
        pid = record["fields"].get("person_id")
        if pid is not None:
            distinct.add(pid)
    return len(distinct)


# -----------------------------------------------------------------------------
# Sidebar (shared across every page, defined once in lib/ui.py).
# -----------------------------------------------------------------------------
render_sidebar()

# -----------------------------------------------------------------------------
# Header
# -----------------------------------------------------------------------------
st.title("DCI Engagement Dashboard")
st.markdown(
    "The Deliberative Citizenship Initiative creates opportunities for "
    "Davidson students, faculty, staff, and members of the wider community "
    "to engage with one another on difficult and contentious issues. "
    "This page is a live look at who is taking part in that work, "
    "across events, D-Teams, and the newsletter."
)

st.divider()

# -----------------------------------------------------------------------------
# Headline KPIs, counted per activity, not as one summed total.
#
# Each number means a different thing. Showing them separately avoids
# the misleading "we have 20,080 DCI people" framing. The People table
# is the union of every source DCI has ever pulled from (event
# registrations, newsletter signups, faculty lists), so a single total
# inflates the real reach.
# -----------------------------------------------------------------------------
st.subheader("People engaging with DCI's work")
st.caption(
    "Each number counts the distinct people in that part of DCI's work. "
    "Someone who shows up in more than one category is counted once in each."
)

try:
    with st.spinner("Pulling data from Airtable…"):
        people = load_people()
        event_records = load_event_attendance()
        dteam_records = load_dteam_membership()
        sub_records = load_subscribed()

    event_attendees = count_distinct_people(event_records)
    dteam_participants = count_distinct_people(dteam_records)
    newsletter_subs = count_distinct_people(sub_records)
    total_people = len(people)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="Event attendees", value=f"{event_attendees:,}")
        st.caption("Distinct people who attended at least one DCI event.")

    with col2:
        st.metric(label="D-Team participants", value=f"{dteam_participants:,}")
        st.caption("Distinct people who joined at least one D-Team.")

    with col3:
        st.metric(label="Newsletter subscribers", value=f"{newsletter_subs:,}")
        st.caption("Distinct people on the DCI newsletter.")

    st.divider()

    # Total in People table, kept for transparency, framed as plumbing
    # rather than a headline.
    st.markdown(
        f"**Total people on record:** {total_people:,}  \n"
        f"*This is everyone DCI has any record of, across all sources: "
        f"newsletter signups, event check-ins, D-Team rosters, faculty "
        f"and staff lists. It includes people who signed up once and "
        f"never came back, so it is not the same as active community. "
        f"The three counts above are the better picture of who is "
        f"currently engaged.*"
    )

except KeyError:
    st.error(
        "Airtable token not configured. "
        "Add your token to `.streamlit/secrets.toml` and refresh."
    )
except Exception as e:
    st.error(f"Couldn't reach Airtable: {e}")

st.divider()

# -----------------------------------------------------------------------------
# How this stays up to date.
#
# This is the section that explains the data flow in plain English.
# It matters because Dr. Bullock and the DCI team need to trust that
# the numbers are real and current, not a stale snapshot.
# -----------------------------------------------------------------------------
st.subheader("How this stays up to date")
st.markdown(
    """
    This page does not keep its own copy of DCI's data. Each time it is
    opened, the app reads directly from DCI's database and recalculates
    the counts on the fly.

    Whenever the team adds a new event attendee, signs someone up for
    the newsletter, or updates a D-Team roster in the database, those
    changes appear here within a few minutes. Nobody has to refresh a
    report, export a spreadsheet, or hand anything off. The DCI team
    keeps using the same workflow they already use, and this page stays
    in sync.
    """
)

st.divider()

# -----------------------------------------------------------------------------
# Pointer to the other pages (Streamlit auto-builds a sidebar nav from
# everything in `pages/`, but spelling it out here makes the dashboard
# feel intentional).
# -----------------------------------------------------------------------------
st.subheader("What you can do here")
st.markdown(
    """
    Use the pages in the left sidebar to dig deeper.

    - **Reports.** Trends over time: attendance by year, top events,
      newsletter growth.
    - **Person search.** Look up any individual and see their full
      history with DCI: every event, every D-Team, newsletter status.
    - **Events.** Browse every event with attendance counts and ticket
      type breakdown.
    - **D-Teams.** Browse every D-Team with members, rounds, and status.
    """
)

st.caption(
    "Built on top of DCI's existing records. The data shown here is live, "
    "not a snapshot."
)
