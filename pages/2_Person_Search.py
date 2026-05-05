"""
Person Search page.

Type a name, see every interaction DCI has on file for that person:
events attended, D-Teams joined, newsletter status.

How it works:
  1. We pull the People table once (cached for 5 min).
  2. We filter in Python by case-insensitive name match.
  3. For each match, we filter the activity tables by their person_id
     and render the results in expanders.

Why filter in Python and not in Airtable's API?
  Airtable formula filters are slow and fragile for substring matches.
  20K rows in memory is small enough that pure-Python filtering is
  faster and simpler. The cache means we only pay the load cost once
  every 5 minutes.
"""

import streamlit as st

from lib.airtable import (
    load_people,
    load_event_attendance,
    load_events,
    load_dteam_membership,
    load_dteams,
    load_subscribed,
    pick,
)
from lib.ui import render_sidebar

st.set_page_config(page_title="Person Search · DCI", layout="wide")
render_sidebar()

st.title("Person Search")
st.markdown(
    "Look up any individual and see their full history with DCI. "
    "Useful when Dr. Bullock or a staff member wants to confirm "
    "whether someone has engaged before, in what capacity, and when."
)

query = st.text_input(
    "Search by name",
    placeholder="e.g., Yolcu or Yurdanur",
    help="Matches first name, last name, or both. Not case sensitive.",
)

if not query:
    st.info("Type a name above to start searching.")
    st.stop()


# -----------------------------------------------------------------------------
# Load everything we need (all cached, so this is cheap on repeat searches).
# -----------------------------------------------------------------------------
try:
    with st.spinner("Loading data…"):
        people = load_people()
        attendance = load_event_attendance()
        events = load_events()
        dteam_members = load_dteam_membership()
        dteams = load_dteams()
        subscriptions = load_subscribed()
except Exception as e:
    st.error(f"Couldn't reach Airtable: {e}")
    st.stop()


# -----------------------------------------------------------------------------
# Filter People by name match.
# -----------------------------------------------------------------------------
q = query.lower().strip()

matches = []
for record in people:
    f = record["fields"]
    first = str(pick(f, ["first_name", "First Name", "firstname"], default="")).lower()
    last = str(pick(f, ["last_name", "Last Name", "lastname"], default="")).lower()
    full = f"{first} {last}".strip()
    if q in first or q in last or q in full:
        matches.append(record)

st.caption(f"Found {len(matches):,} match(es). Showing the first 25.")

if not matches:
    st.warning(
        "No people match that name. Try a shorter search "
        "(e.g., just a last name) or check spelling."
    )
    st.stop()


# -----------------------------------------------------------------------------
# Build lookup tables once, so we are not scanning O(N) for each match.
# -----------------------------------------------------------------------------

# event_id -> event fields
events_by_id = {
    r["fields"].get("event_id"): r["fields"]
    for r in events
    if r["fields"].get("event_id") is not None
}

# dteam_id -> dteam fields
dteams_by_id = {
    r["fields"].get("dteam_id"): r["fields"]
    for r in dteams
    if r["fields"].get("dteam_id") is not None
}

# person_id -> list of attendance rows
attendance_by_person: dict = {}
for row in attendance:
    pid = row["fields"].get("person_id")
    if pid is not None:
        attendance_by_person.setdefault(pid, []).append(row)

dteam_by_person: dict = {}
for row in dteam_members:
    pid = row["fields"].get("person_id")
    if pid is not None:
        dteam_by_person.setdefault(pid, []).append(row)

subs_by_person: dict = {}
for row in subscriptions:
    pid = row["fields"].get("person_id")
    if pid is not None:
        subs_by_person.setdefault(pid, []).append(row)


# -----------------------------------------------------------------------------
# Render each match as an expander.
# -----------------------------------------------------------------------------
for match in matches[:25]:
    f = match["fields"]
    first = pick(f, ["first_name", "First Name", "firstname"], default="")
    last = pick(f, ["last_name", "Last Name", "lastname"], default="")
    name = f"{first} {last}".strip() or "(no name)"
    pid = f.get("person_id")

    person_events = attendance_by_person.get(pid, [])
    person_dteams = dteam_by_person.get(pid, [])
    person_subs = subs_by_person.get(pid, [])

    header = f"{name}  ·  {len(person_events)} event(s), {len(person_dteams)} D-Team(s)"

    with st.expander(header):
        # Quick metric row
        c1, c2, c3 = st.columns(3)
        c1.metric("Events attended", len(person_events))
        c2.metric("D-Teams joined", len(person_dteams))
        c3.metric("Newsletter records", len(person_subs))

        # Events list
        if person_events:
            st.markdown("**Events**")
            for row in person_events:
                rf = row["fields"]
                eid = rf.get("event_id")
                event_fields = events_by_id.get(eid, {})
                ev_name = pick(
                    event_fields,
                    ["name", "event_name", "Name", "title"],
                    default=f"Event {eid}",
                )
                ev_date = pick(event_fields, ["date", "event_date", "Date"])
                ticket = rf.get("ticket_type", "")
                role = rf.get("role", "")
                bits = [str(ev_name)]
                if ev_date:
                    bits.append(str(ev_date))
                if ticket:
                    bits.append(f"ticket: {ticket}")
                if role:
                    bits.append(f"role: {role}")
                st.write("- " + "  ·  ".join(bits))

        # D-Teams list
        if person_dteams:
            st.markdown("**D-Teams**")
            for row in person_dteams:
                rf = row["fields"]
                did = rf.get("dteam_id")
                dt_fields = dteams_by_id.get(did, {})
                dt_name = pick(
                    dt_fields,
                    ["name", "dteam_name", "Name", "title"],
                    default=f"D-Team {did}",
                )
                dt_date = pick(dt_fields, ["date", "start_date", "Date"])
                status = rf.get("status", "")
                round_no = rf.get("round", "")
                role = rf.get("role", "")
                bits = [str(dt_name)]
                if dt_date:
                    bits.append(str(dt_date))
                if round_no:
                    bits.append(f"round: {round_no}")
                if role:
                    bits.append(f"role: {role}")
                if status:
                    bits.append(f"status: {status}")
                st.write("- " + "  ·  ".join(bits))

        # Subscription history
        if person_subs:
            st.markdown("**Newsletter**")
            for row in person_subs:
                rf = row["fields"]
                sub_date = rf.get("subscribe_date", "unknown")
                unsub = rf.get("unsubscribe_date")
                status_text = "currently subscribed" if not unsub else f"unsubscribed {unsub}"
                st.write(f"- subscribed {sub_date}, {status_text}")

        # If they have nothing, say so plainly.
        if not (person_events or person_dteams or person_subs):
            st.caption(
                "This person is on file but has no event, D-Team, or "
                "newsletter activity recorded."
            )

if len(matches) > 25:
    st.caption(
        f"{len(matches) - 25:,} more match(es) not shown. Refine the "
        f"search to narrow it down."
    )
