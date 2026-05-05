"""
Shared helpers for talking to Airtable.

Why this file exists:
    Every page in this app needs to read the same tables out of the
    same Airtable base. Instead of repeating the connection code on
    every page, we put it here once and import it from each page.

    This is a basic engineering principle called DRY: "Don't Repeat
    Yourself." If we put the connection code on every page and later
    rotated the token, we would have to change it in five files.
    Here, we change it in one.

Caching:
    The `@st.cache_data(ttl=300)` decorator on each loader tells
    Streamlit: "remember this answer for 5 minutes." If two pages
    both call `load_event_attendance()` within 5 minutes, the second
    call returns instantly from memory instead of hitting Airtable
    again. This keeps the app fast and stays well below Airtable's
    rate limits.
"""

import streamlit as st
from pyairtable import Api


# -----------------------------------------------------------------------------
# Connection
# -----------------------------------------------------------------------------
def get_table(table_name: str):
    """Open a handle to one Airtable table inside our base.

    Reads the API token and base ID from `.streamlit/secrets.toml`
    (which is gitignored, so it never lands on GitHub).
    """
    token = st.secrets["AIRTABLE_TOKEN"]
    base_id = st.secrets["AIRTABLE_BASE_ID"]
    api = Api(token)
    return api.table(base_id, table_name)


# -----------------------------------------------------------------------------
# Loaders: one function per table.
#
# Each function pulls every row from one table. We cache the result for
# 5 minutes so we are not hammering Airtable on every page load.
#
# We return the raw list of records (each record is a dict with `id` and
# `fields`). The pages then filter and reshape this data themselves.
# -----------------------------------------------------------------------------

@st.cache_data(ttl=300)
def load_people() -> list:
    """All rows from the People table."""
    return get_table("People").all()


@st.cache_data(ttl=300)
def load_event_attendance() -> list:
    """All rows from Event Attendance (one row per person per event)."""
    return get_table("Event Attendance").all()


@st.cache_data(ttl=300)
def load_dteam_membership() -> list:
    """All rows from D Team Membership."""
    return get_table("D Team Membership").all()


@st.cache_data(ttl=300)
def load_subscribed() -> list:
    """All rows from Subscribed (newsletter signups)."""
    return get_table("Subscribed").all()


@st.cache_data(ttl=300)
def load_events() -> list:
    """All rows from the Event table (one per event)."""
    return get_table("Event").all()


@st.cache_data(ttl=300)
def load_dteams() -> list:
    """All rows from the D Team table (one per D-Team)."""
    return get_table("D Team").all()


# -----------------------------------------------------------------------------
# Field helpers
#
# We do not always know the exact column names in every Airtable table
# (the team has been iterating on the schema). These helpers let pages
# look up a value by trying several candidate field names, so the page
# does not crash if a column was renamed from "name" to "event_name".
# -----------------------------------------------------------------------------

def pick(fields: dict, candidates: list, default=None):
    """Return the first present value from `candidates` in `fields`.

    Example:
        name = pick(record["fields"], ["name", "Name", "event_name"])

    Why: schemas drift. This is a safety net so a renamed field
    does not break the page.
    """
    for key in candidates:
        if key in fields and fields[key] is not None:
            return fields[key]
    return default
