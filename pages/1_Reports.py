"""
Reports page.

Right now this page is intentionally minimal. We had charts here
(attendance by year, D-Team participation by year, top events) but
during testing we noticed that the date columns on older events and
D-Teams in the database are not fully populated, which made every
year-based chart collapse into a single bar for 2026. Rather than
ship a misleading chart in front of Dr. Bullock, we hid the trends
section until the underlying dates can be backfilled.

The home page already shows the headline counts that do not depend
on dates (event attendees, D-Team participants, newsletter
subscribers), and the Events and D-Teams pages let you drill into
specific events and teams.
"""

import streamlit as st

from lib.ui import render_sidebar

st.set_page_config(page_title="Reports · DCI", layout="wide")
render_sidebar()

st.title("Reports")

st.markdown(
    """
    Trend reports will live on this page: attendance by year,
    growth in D-Team participation, and the events that drew the
    most engagement.

    Right now we are holding off on the year-based charts. The date
    columns for older events and D-Teams in the database are not
    fully populated, so any chart grouped by year collapses into the
    current year and would misrepresent DCI's actual history.

    Once the date fields are backfilled (either by re-running the
    import with the correct dates, or by editing the older rows in
    Airtable), the trend charts will go back on this page without
    any code changes here. The data is already plumbed through.

    In the meantime:

    - The **home page** shows the headline counts that do not depend
      on dates: event attendees, D-Team participants, newsletter
      subscribers.
    - The **Events** page lists every event with attendance counts,
      sortable and searchable.
    - The **D-Teams** page does the same for every D-Team.
    - **Person Search** lets you look up any individual and see their
      full history with DCI.
    """
)

st.caption(
    "Built on top of DCI's existing records. The data shown here is live, "
    "not a snapshot."
)
