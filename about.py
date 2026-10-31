"""The About page. Everything below is plain text, so it is easy to edit."""
import streamlit as st

from shared_ui import restore_widget_state

restore_widget_state()  # keeps the simulator inputs alive while you read this page

st.title("About this simulator")

st.header("Why I built this")
st.markdown(
    """
The idea for this simulator is years in the making. In his [podcast](https://www.youtube.com/watch?v=bhOkvOcVmOg&t=737s),
Daniel Cates references Bill Chen's book *The Mathematics of Poker*, saying that Bill makes a mathematical argument that
you should take a flip of QQ vs AKo on hand 1 of the WSOP main event (56%-44%). This is very counterintuitive and Selbst
herself was incredulous. Given Chen’s mathematics background, I was intrigued at the possibility he was right. In the book,
Chen has a section titled "Poker Tournaments: The Theory of Doubling Up". In it he posits a mathematical way to model
tournament performance as a function of a player's odds of reaching 2x their current chip stack. The math behind this is
detailed on the [methodology page](/methodology) and is the foundation for how this simulator works. The key component of
this is the derivation of C which is the chance a player has at reaching 2x their stack, or “doubling up”. The utility of C
is that it standardizes player skill relative to the field, and therefore can be used to isolate the effects of field size
and payout structure on ROI.

Do larger tournament field sizes confer a greater ROI? Does a payout structure that is less top heavy decrease ROI? Does
increasing the % of player paid from 12% to 15% decrease ROI The consensus answers to these questions are yes, but previously
there hasn’t been a way to measure the extent of these effects. Studying poker empirically is difficult due to the sample size
needed, and fuzziness of the validity of data. and it is difficult to get a sample of results that is large enough, and valid
for the questions I am trying to answer. This simulator attempts to fix that by using theoretical methods.
"""
)

st.divider()
st.info(
    "I used Claude for 100% of the code on this project, and several design choices. "
    "All words on the \"About\" and \"Methodology\" pages are my own."
)
