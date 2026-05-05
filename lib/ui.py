"""
Shared UI helpers used by every page.

Why this exists:
    The sidebar (DCI branding, team names) should appear on every
    page, identically. Instead of copy-pasting that block into five
    files, it lives here once and every page calls render_sidebar().

    If we ever change the team list, the project description, or the
    branding, we change this file and every page updates.
"""

import streamlit as st


def render_sidebar() -> None:
    """Draw the DCI branding block in the sidebar on the current page."""
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
