"""Entry point: `streamlit run app.py`. Sets up the page menu; the pages themselves are separate files."""
import streamlit as st

st.set_page_config(page_title="Poker Tournament Simulator", layout="wide")

page = st.navigation([
    st.Page("simulator.py", title="Poker Tournament Variance Simulator", default=True),
    st.Page("many_tournaments.py", title="Survival Effect Simulator"),
    st.Page("about.py", title="About"),
    st.Page("methodology.py", title="Methodology"),
])
page.run()
