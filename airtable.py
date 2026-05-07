"""
Airtable data layer.

Everything that talks to Airtable lives in this file. The UI in app.py
imports from here. Each loader is cached for 5 minutes so repeated
reads inside one session are free.

The Airtable token is read from .streamlit/secrets.toml locally, or
from the Streamlit Cloud secrets vault when deployed. Either way it
never appears in the code or the GitHub repo.
"""

import streamlit as st
from pyairtable import Api


def get_table(table_name: str):
    """Open a handle to one table in the DCI Airtable base."""
    token = st.secrets["AIRTABLE_TOKEN"]
    base_id = st.secrets["AIRTABLE_BASE_ID"]
    api = Api(token)
    return api.table(base_id, table_name)


# Each loader pulls one full table and caches the result for 5 minutes.
# We return the raw list of records (each record is a dict with `id`
# and `fields`). The UI filters and shapes the data itself.

@st.cache_data(ttl=300)
def load_people() -> list:
    return get_table("People").all()


@st.cache_data(ttl=300)
def load_event_attendance() -> list:
    return get_table("Event Attendance").all()


@st.cache_data(ttl=300)
def load_dteam_membership() -> list:
    return get_table("D Team Membership").all()


@st.cache_data(ttl=300)
def load_subscribed() -> list:
    return get_table("Subscribed").all()


@st.cache_data(ttl=300)
def load_events() -> list:
    return get_table("Event").all()


@st.cache_data(ttl=300)
def load_dteams() -> list:
    return get_table("D Team").all()


def pick(fields: dict, candidates: list, default=None):
    """Return the first non-empty value among the candidate field names.

    Airtable column names sometimes differ between tables (Name vs name
    vs event_name), so the UI looks each candidate up in order and
    takes the first hit.
    """
    for key in candidates:
        if key in fields and fields[key] is not None:
            return fields[key]
    return default
