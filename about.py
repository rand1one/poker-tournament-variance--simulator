"""The About page. Everything below is plain text, so it is easy to edit."""
import streamlit as st

from shared_ui import restore_widget_state, soft_links

restore_widget_state()  # keeps the simulator inputs alive while you read this page
soft_links()
st.html(  # section titles only slightly bigger than the body text
    """<style>
    [data-testid="stMarkdownContainer"] h2 { font-size: 1rem !important; font-weight: 700 !important;
                                              line-height: 1.4 !important; padding: 0.6rem 0 0.1rem !important; }
    </style>"""
)

st.title("About this simulator")

st.markdown(
    """
## Why I built this

This simulator was created with the intention to offer a better way to study the effects of field size and payout structure
on return on investment (ROI) in multitable poker tournaments. Poker players have long believed larger field sizes and steeper payout structures benefited the return on
investment of professionals, *ceteris paribus*, but the extent of this effect has been a matter of significant
disagreement. Empirical data is poor because of the large sample size needed and validity concerns due to changing
environments. This app attempts to offer a novel way to parse these questions using a theoretical framework.

## The theory of doubling up

This framework relies on the utility of one's "chance of doubling up" (C), first described in Bill Chen's book
*The Mathematics of Poker*[¹](#notes). Chen reasoned that C could be thought of as a way to quantify a player's relative
skill, as well as a tool that could inform whether one should risk their chips in marginal situations. Chen said that if
you computed your C, you could decline to risk all your chips in situations where your chances of doubling up were less
than C. Example: if you hold QQ and are deciding whether to call an opponent who has gone all in with AK offsuit, you
must have a C exceeding 56% to fold[²](#notes)[³](#notes). Of course you would never be able to be this precise, but knowledge of
your C would give you a better sense of how aggressive you should be in passing on edges.

Chen extends the utility of C by reasoning that it could be used to compute the *effective tournament size*, which is a
number that takes in payout information and field size to represent the extent to which a tournament rewards skill.
Chen starts with the assumption that a prize pool that is distributed only to the 1st place finisher is the most
rewarding to players that are the most skilled. He then details a method of converting any tournament payout structure
into a winner-take-all one. In his words (p. 318):

> We call this the effective tournament size - essentially what we're doing is quantifying the degree to which the
> structured payouts reduce the opportunity to apply skill. We can say that as a close approximation, a tournament of 256
> players where the first and second prizes are equal has the same latitude for skill as a 128-player tournament where
> it's winner-take-all.

## Natural selection: Poker Edition

One of the key assumptions Chen makes for the validity of C is its consistency throughout the tournament.
Any attempt to assess how C may change over the course of a tournament takes on enormous complexity. However, this change may be
significant, since better players are more likely to remain after a large portion of the field is eliminated. The skill
of the final table of a tournament is generally of a much higher average skill than a table at the start of the
tournament.

I call this the *survival effect* and make an attempt at assessing how significant it is in the [Survival Effect Simulator](/many_tournaments).
I describe the details of this on the [methodology page](/methodology), but essentially I am simulating a
tournament by generating a field of players and C values for each, then sequentially having them play a series of 2
player matches until someone wins. I am far less confident on the validity of this model and am sure there are better
ways people may think of for how to quantitatively capture the survival effect.

This site provides a way to study these concepts, and extends Chen's ideas towards answering questions that have
practical relevance to game selection for professionals. For details on the mathematics behind Chen's ideas, and this
simulator's extension of them, please visit the [methodology page](/methodology).

*100% of the code for this project was generated using Claude Code. All words and ideas on this and the
methodology pages are my own.*
"""
)

st.subheader("Notes", anchor="notes")
st.markdown(
    """
1. Bill Chen and Jerrod Ankenman, *The Mathematics of Poker* (ConJelCo, 2006). Page numbers below refer to this book.
2. QQ has a 56% chance of winning against AKo.
3. Counterintuitively, you should almost always call in this situation even if you are very skilled. If you don't
   believe me play around with the simulator and see for yourself ;)
"""
)
