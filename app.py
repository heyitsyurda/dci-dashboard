"""
DCI Engagement Dashboard.

One Streamlit script, four sections shown as tabs:

    Reports         the headline counts (event attendees, D-Team
                    participants, newsletter subscribers).
    Person Search   look up an individual and see their full history.
    Events          browse every event DCI has hosted.
    D-Teams         browse every D-Team DCI has run.

The Airtable data is loaded once at the top of this file and reused
by every tab, so we hit the API at most once per session per table.
"""

from collections import Counter, defaultdict

import pandas as pd
import streamlit as st

from airtable import (
    load_people,
    load_event_attendance,
    load_events,
    load_dteam_membership,
    load_dteams,
    load_subscribed,
    pick,
)


# -----------------------------------------------------------------------------
# Page config and sidebar
# -----------------------------------------------------------------------------
st.set_page_config(page_title="DCI Engagement Dashboard", layout="wide")

with st.sidebar:
    st.markdown("### DCI Engagement Dashboard")
    st.caption("Deliberative Citizenship Initiative · Davidson College")
    st.divider()
    st.markdown(
        """
        A live view of who DCI is engaging across campus and the
        wider community.

        **Team**
        Yurdanur Yolcu · Cillian Hallinan · Mary Devine
        """
    )


# -----------------------------------------------------------------------------
# Load every table once. The tabs below all read from these variables.
# -----------------------------------------------------------------------------
try:
    with st.spinner("Loading data…"):
        people = load_people()
        attendance = load_event_attendance()
        events = load_events()
        dteam_members = load_dteam_membership()
        dteams = load_dteams()
        subscriptions = load_subscribed()
except KeyError:
    st.error(
        "Airtable token not configured. Add your token to "
        "`.streamlit/secrets.toml` and refresh."
    )
    st.stop()
except Exception as e:
    st.error(f"Couldn't reach Airtable: {e}")
    st.stop()


# -----------------------------------------------------------------------------
# Small helpers used by more than one tab.
# -----------------------------------------------------------------------------
def count_distinct_people(records: list) -> int:
    """How many distinct person_id values appear in this list of records."""
    distinct = set()
    for record in records:
        pid = record["fields"].get("person_id")
        if pid is not None:
            distinct.add(pid)
    return len(distinct)


def format_breakdown(counter: Counter) -> str:
    """Turn a Counter into 'label (count), label (count)' sorted by count."""
    if not counter:
        return ""
    return ", ".join(
        f"{label} ({count})"
        for label, count in sorted(counter.items(), key=lambda x: -x[1])
    )


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
# Tabs
# -----------------------------------------------------------------------------
tab_reports, tab_person, tab_events, tab_dteams = st.tabs(
    ["Reports", "Person Search", "Events", "D-Teams"]
)


# =============================================================================
# Reports tab: the headline counts.
# =============================================================================
with tab_reports:
    st.subheader("People engaging with DCI's work")
    st.caption(
        "Each number counts the distinct people in that part of DCI's "
        "work. Someone who shows up in more than one category is counted "
        "once in each."
    )

    event_attendees = count_distinct_people(attendance)
    dteam_participants = count_distinct_people(dteam_members)
    newsletter_subs = count_distinct_people(subscriptions)
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

    st.markdown(
        f"**Total people on record:** {total_people:,}  \n"
        f"*This is everyone DCI has any record of, across all sources: "
        f"newsletter signups, event check-ins, D-Team rosters, faculty "
        f"and staff lists. It includes people who signed up once and "
        f"never came back, so it is not the same as active community. "
        f"The three counts above are the better picture of who is "
        f"currently engaged.*"
    )

    st.divider()

    st.subheader("How this stays up to date")
    st.markdown(
        """
        This page does not keep its own copy of DCI's data. Each time it
        is opened, the app reads directly from DCI's database and
        recalculates the counts on the fly.

        Whenever the team adds a new event attendee, signs someone up
        for the newsletter, or updates a D-Team roster in the database,
        those changes appear here within a few minutes. Nobody has to
        refresh a report, export a spreadsheet, or hand anything off.
        The DCI team keeps using the same workflow they already use,
        and this page stays in sync.
        """
    )


# =============================================================================
# Person Search tab: look up an individual.
# =============================================================================
with tab_person:
    st.subheader("Person Search")
    st.markdown(
        "Look up any individual and see their full history with DCI. "
        "Useful when Dr. Bullock or a staff member wants to confirm "
        "whether someone has engaged before, in what capacity, and when."
    )

    query = st.text_input(
        "Search by name",
        placeholder="e.g., Yolcu or Yurdanur",
        help="Matches first name, last name, or both. Not case sensitive.",
        key="person_search_query",
    )

    if not query:
        st.info("Type a name above to start searching.")
    else:
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
        else:
            # Build lookups once so we are not scanning every activity
            # table for each match.
            events_by_id = {
                r["fields"].get("event_id"): r["fields"]
                for r in events
                if r["fields"].get("event_id") is not None
            }
            dteams_by_id = {
                r["fields"].get("dteam_id"): r["fields"]
                for r in dteams
                if r["fields"].get("dteam_id") is not None
            }

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
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Events attended", len(person_events))
                    c2.metric("D-Teams joined", len(person_dteams))
                    c3.metric("Newsletter records", len(person_subs))

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

                    if person_subs:
                        st.markdown("**Newsletter**")
                        for row in person_subs:
                            rf = row["fields"]
                            sub_date = rf.get("subscribe_date", "unknown")
                            unsub = rf.get("unsubscribe_date")
                            status_text = (
                                "currently subscribed" if not unsub
                                else f"unsubscribed {unsub}"
                            )
                            st.write(f"- subscribed {sub_date}, {status_text}")

                    if not (person_events or person_dteams or person_subs):
                        st.caption(
                            "This person is on file but has no event, D-Team, "
                            "or newsletter activity recorded."
                        )

            if len(matches) > 25:
                st.caption(
                    f"{len(matches) - 25:,} more match(es) not shown. Refine the "
                    f"search to narrow it down."
                )


# =============================================================================
# Events tab: every event with attendance counts.
# =============================================================================
with tab_events:
    st.subheader("Events")
    st.markdown(
        "Every event DCI has hosted, with attendance counts and ticket "
        "type breakdown. Click any row to expand and see details."
    )

    # Aggregate attendance by event.
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

    rows = []
    for record in events:
        f = record["fields"]
        eid = f.get("event_id")
        name = pick(f, ["name", "event_name", "Name", "title"], default=f"Event {eid}")
        date = pick(f, ["date", "event_date", "Date", "start_date"], default="")
        rows.append({
            "Event": str(name),
            "Date": str(date) if date else "",
            "Attendees": len(attendees_per_event.get(eid, set())),
            "_event_id": eid,
        })

    if not rows:
        st.warning("No events found in the Event table.")
    else:
        events_df = pd.DataFrame(rows)

        col_search, col_sort = st.columns([3, 1])
        with col_search:
            search = st.text_input(
                "Search by event name",
                placeholder="e.g., Davidson Forum",
                key="event_search",
            )
        with col_sort:
            sort_by = st.selectbox(
                "Sort by",
                ["Attendees (high to low)", "Date (newest first)",
                 "Date (oldest first)", "Name (A-Z)"],
                key="event_sort",
            )

        filtered = events_df
        if search:
            filtered = filtered[
                filtered["Event"].str.lower().str.contains(search.lower(), na=False)
            ]

        if sort_by == "Attendees (high to low)":
            filtered = filtered.sort_values("Attendees", ascending=False)
        elif sort_by == "Date (newest first)":
            filtered = filtered.sort_values("Date", ascending=False)
        elif sort_by == "Date (oldest first)":
            filtered = filtered.sort_values("Date", ascending=True)
        elif sort_by == "Name (A-Z)":
            filtered = filtered.sort_values("Event")

        st.caption(f"Showing {len(filtered):,} of {len(events_df):,} event(s).")

        st.dataframe(
            filtered.drop(columns=["_event_id"]),
            use_container_width=True,
            hide_index=True,
        )

        st.divider()
        st.subheader("Event details")

        for _, row in filtered.head(50).iterrows():
            eid = row["_event_id"]
            header = f"{row['Event']}  ·  {row['Attendees']:,} attendees"
            if row["Date"]:
                header += f"  ·  {row['Date']}"

            with st.expander(header):
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


# =============================================================================
# D-Teams tab: every D-Team with role and status breakdown.
# =============================================================================
with tab_dteams:
    st.subheader("D-Teams")
    st.markdown(
        "DCI's small-group deliberation format. Each D-Team brings a "
        "small cohort of students, faculty, staff, or community members "
        "together over multiple rounds to deliberate on a contested topic."
    )

    # Aggregate membership by D-Team.
    participants_per_team: dict = defaultdict(set)
    rounds_per_team: dict = defaultdict(Counter)
    status_per_team: dict = defaultdict(Counter)
    roles_per_team: dict = defaultdict(Counter)

    for row in dteam_members:
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

    rows = []
    for record in dteams:
        f = record["fields"]
        did = f.get("dteam_id")
        name = pick(f, ["name", "dteam_name", "Name", "title"], default=f"D-Team {did}")
        date = pick(f, ["date", "start_date", "Date"], default="")
        rows.append({
            "D-Team": str(name),
            "Date": str(date) if date else "",
            "Participants": len(participants_per_team.get(did, set())),
            "Rounds": len(rounds_per_team.get(did, Counter())),
            "_dteam_id": did,
        })

    if not rows:
        st.warning("No D-Teams found in the D Team table.")
    else:
        dteams_df = pd.DataFrame(rows)

        col_search, col_sort = st.columns([3, 1])
        with col_search:
            search = st.text_input(
                "Search by D-Team name",
                placeholder="e.g., Free Speech, Climate, Immigration",
                key="dteam_search",
            )
        with col_sort:
            sort_by = st.selectbox(
                "Sort by",
                ["Participants (high to low)", "Date (newest first)",
                 "Date (oldest first)", "Name (A-Z)"],
                key="dteam_sort",
            )

        filtered = dteams_df
        if search:
            filtered = filtered[
                filtered["D-Team"].str.lower().str.contains(search.lower(), na=False)
            ]

        if sort_by == "Participants (high to low)":
            filtered = filtered.sort_values("Participants", ascending=False)
        elif sort_by == "Date (newest first)":
            filtered = filtered.sort_values("Date", ascending=False)
        elif sort_by == "Date (oldest first)":
            filtered = filtered.sort_values("Date", ascending=True)
        elif sort_by == "Name (A-Z)":
            filtered = filtered.sort_values("D-Team")

        st.caption(f"Showing {len(filtered):,} of {len(dteams_df):,} D-Team(s).")

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
