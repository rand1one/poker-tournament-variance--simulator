"""The Methodology page. Everything below is plain text and formulas, so it is easy to edit."""
import streamlit as st

from shared_ui import restore_widget_state, soft_links

restore_widget_state()  # keeps the simulator inputs alive while you read this page
soft_links()

st.title("Methodology")

with st.container(border=True):
    st.markdown("**Contents**")
    st.markdown(
        "1. [Using the Chance of Doubling Up as a Skill Proxy](#using-c)\n"
        "2. [Modeling the Survival Effect](#survival-effects)"
    )

st.header("Using the Chance of Doubling Up as a Skill Proxy", anchor="using-c")
st.markdown(
    """
Imagine you are playing an equally skilled 128 person tournament where all the prize money is given to first place.
The number of doubles needed to win all the chips is given by log₂(128) = 7. Assuming the likelihood of doubling at any
point is 0.5, your chances of getting 7 doubles is 0.5<sup>7</sup> = 0.0078.

Now imagine you are more skilled than the other players, and in fact, you are likely to reach 2x your initial stack 55%
of the time! We assume this advantage stays constant throughout the tournament, such that given any stack Y, your chance
of getting to a stack of 2Y is 55%. We will use **C** to denote this percentage: the chance of doubling up.

If we use the 128 person tournament example, we can use the equation C<sup>d</sup> = W to find your chances of winning,
where *d* is the number of doubles needed (log₂ of the field size) and *W* is the chance of winning.
""",
    unsafe_allow_html=True,
)
st.latex(r"0.55^{\log_2 128} = W = 0.0152")
st.markdown(
    """
So with a C of 0.55, you can expect to win this tournament 1.52% of the time, nearly double your chances of winning with
a C of 0.5.

To find your expected value (EV), you simply multiply your chance of finishing 1st by the payout. In this example, a
1.52% chance of winning the tournament gives an EV of 1.52% × 128 = 1.95 buy-ins, or an ROI of 95%.

In reality, tournaments are rarely winner take all. Most tournaments pay 10-15% of the field, and the payout size drops
the further from 1st your finishing position is. If we know the payout structure, we can still find the relationship
between C and ROI by calculating the odds of finishing in each position and multiplying each by its payout.
This is expressed in the sum:
"""
)
st.latex(r"\text{EV} = \sum_{i=1}^{X} p_i \, v_i")
st.markdown(
    """
where p<sub>i</sub> is the probability of finishing in position *i*, v<sub>i</sub> is the payout received for
finishing in position *i*, and *X* is the field size.

**How do we calculate p<sub>i</sub>?** Chen makes the following assumption:
""",
    unsafe_allow_html=True,
)
st.markdown(
    """
> The chance of a player's finishing in place N is equal to his chance of doubling up to a stack size of 1/N of the
> chips in play, less his chance of finishing in a higher place.
>
> So a player's chance of finishing first is his chance of doubling up to all of the chips in the tournament. His chance
> of finishing second, then, is his chance of doubling up to half the chips in the tournament less his chance of
> finishing first. His chance of finishing third is his chance of doubling up to a third of the chips in the tournament,
> less this chance of finishing first or second, and so on. This series does in fact sum to one: even though it's true
> that it's not required that a player double up to 1/N chips in order to finish Nth, this approximation is a
> reasonable one.
>
> — Bill Chen, *The Mathematics of Poker*
"""
)
st.latex(r"p_i = C^{\log_2 (X / i)} - C^{\log_2 (X / (i-1))}")
st.markdown(
    """
For 1st place (*i* = 1) the second term is 0, since nobody finishes better than 1st.

**Example.** For an equally skilled 128 person tournament, to find the chance of finishing 6th we need the chance of
finishing 6th or better, minus the chance of finishing 5th or better:
"""
)
st.latex(r"p_6 = 0.5^{\log_2 (128 / 6)} - 0.5^{\log_2 (128 / 5)}")
st.markdown(
    """
Now that we have this formula, we can calculate C for any tournament where we know the field size, payout structure,
and our ROI.


"""
)



st.header("Modeling the Survival Effect", anchor="survival-effects")
st.markdown(
    """
The Survival Effect Simulator is an attempt to mitigate the limitation that assuming C remains constant throughout the
tournament presents. In his book, Chen takes C to be constant throughout any given tournament. This makes using C much easier, but limits its validity. In reality, as a tournament progresses, players with
higher Cs are more likely to remain in the field. This is commonly observed in the fact that as you get deeper in the
tournament, the average player is better than at hand 1. If a player has a C of .55 at the beginning of a tournament, on average it will decrease as the field consolidates.

If we know we have a certain ROI in a tournament with 1000 players, and are wondering how our ROI will change in a field
with 10000 players with an identical skill distribution, we can get a clean answer using the math above. However, the
survival effect is going to be stronger in the larger field, since there is additional opportunity to exert edge.
Measuring this effect precisely is impractical, but my model makes an initial attempt at an empirical assessment.

The survival simulator generates players each with initial C values and chip stacks, then has them engage in heads up
matches where one player wins and doubles up and the other loses and is eliminated. Each player's chance of winning their
match is determined by their own C and their opponent's C. This requires shifting each player's C so that the two
players' Cs average 0.5. If a player with a C of 0.55 was facing a player with a C of 0.51, the chances of winning the
match would be 0.52 and 0.48, respectively. After all players have finished their match, the process is repeated until
there is a winner. To determine finishing position in each round, the matches are played in random order. So with 8
players left, 4 matches would occur this round, and the loser of the first match would get 8th, and the loser of the 4th
match would get 5th.

Thus far I have described how the play of the tournament functions, but we must decide how to assign reasonable Cs to
generated players, that is, how is skill level distributed in poker tournaments? There are 2 reasonable models: normally
distributed, or professional/recreational. The former assumes skill is normally distributed around 0.5. The advantages of
this are that it is simple and consistent. The downside is that this is unlikely to be representative of many actual
tournaments. The reality is more likely to be bimodal, with the peaks representing professionals and recreational
players. While more accurate, there is no good data on the expected proportions, and it is highly variable depending on
the tournament. In the most competitive, highest-stakes tournaments, there may be only 10% recreational players, whereas
in a tournament like the Main Event, it is likely >75%. I decided to add the option of both.

For the rec/pro model, I assumed a difference of 0.075 in average C values between the two groups. The average C value of
recreationals changes linearly depending on the % entered, and may be anywhere from 0.425 to 0.5, with the professional
mean being 0.075 points higher. The specific group means change depending on the proportion chosen. The remaining
fraction of professionals is then generated around a C that makes the field average to 0.5. Example: If 80% recreationals
is inputted, the 80% recreationals have a mean C of 0.485 and the 20% professionals have a mean C of 0.56.

Real tournaments are much messier than this match play format, but I believe that this model captures the majority of
the survival effect as it relates to field size.
"""
)
