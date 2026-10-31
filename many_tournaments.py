"""Survival Adjusted page: every tournament is played out battle by battle, and you are one player with a given C."""
import numpy as np
import pandas as pd
import streamlit as st

from model import (ENTRIES_PER_SECOND, MAX_PLAYER_ENTRIES, PAYOUT_STRUCTURES, bankroll_paths, finish_probs, payouts,
                   solve_C)
from shared_ui import base_inputs, restore_widget_state, run_inputs
from sim_engine import default_workers, hero_finishes_parallel, other_players_split, pro_c, rec_c_for

restore_widget_state()


def carry_over_skill():
    """When the mode is switched, start the new input at the value the old one implied."""
    if "surv_last_C" not in st.session_state:
        return
    if st.session_state.surv_mode == "C":
        st.session_state.surv_C_in = min(max(st.session_state.surv_last_C, 0.001), 0.999)
    else:
        st.session_state.surv_roi_in = max(st.session_state.surv_last_roi_pct, -99.0)


st.title("Survival Adjusted")
st.caption(
    "This experimental tool simulates tournaments by generating players with variable skill levels, and "
    "iteratively battling them to determine finishing position. This attempts to model relative skill dynamics "
    "as the field consolidates."
)

# ---------- Inputs ----------
inputs_col, output_col = st.columns([1, 3], gap="large")
with inputs_col:
    st.subheader("Variables")
    with st.container(border=True):
        X, buyin, structure, start_bankroll = base_inputs("surv")
        mode = st.radio("Specify skill by", ["ROI", "C"], horizontal=True, key="surv_mode", on_change=carry_over_skill,
                        help="Enter either ROI or C. The other one is calculated from it.\n\n"
                             "C = Chance of doubling up")
        roi_pct = C_in = None
        if mode == "ROI":
            roi_pct = st.number_input("ROI (%)", min_value=-99.0, step=1.0, format="%.2f", key="surv_roi_in")
        else:
            C_in = st.number_input("C", min_value=0.001, max_value=0.999, step=0.01, format="%.6f", key="surv_C_in")
        calc_slot = st.empty()  # filled in below once C / ROI have been worked out
        rec_pct = st.number_input("Recreational players (%)", min_value=0.0, max_value=100.0, step=5.0, format="%.1f",
                                  key="surv_rec_pct",
                                  help="Share of the field (apart from you and your counterpart) that are recreational "
                                       "players. Their average C rises linearly from 0.425 (0% recreational) to 0.5 "
                                       "(100%), and everyone else is always 0.075 higher, which keeps the average C of "
                                       "the field at exactly 0.5. 0% gives a single group around 0.5.")
        field_slot = st.container()  # both groups' Cs, filled in below
        n_tournaments, n_sims = run_inputs("surv")
    run_slot = st.container()  # the Run many simulations button goes here, below the box

with output_col:
    # ---------- Reset state whenever a variable changes ----------
    params = (X, buyin, structure, start_bankroll, mode, roi_pct, C_in, rec_pct, n_tournaments, n_sims)
    if st.session_state.get("many_params") != params:
        st.session_state.many_params = params
        st.session_state.many = None

    if PAYOUT_STRUCTURES[structure](X) is None:
        st.error(f"The {structure} structure has no payout data for {X} players yet.")
        st.stop()
    reg_v, _ = payouts(X, buyin, structure, False)

    # Same as the Tournament Variance Simulator: your skill is an ROI or a C, and the other one is worked out
    # from the finish-probability formula using the regular payouts.
    if mode == "ROI":
        roi = roi_pct / 100
        max_roi = reg_v[0] / buyin - 1
        if roi >= max_roi:
            st.error(f"ROI must be below {max_roi * 100:.0f}% (the 1st place payout) for these settings.")
            st.stop()
        C = solve_C(X, buyin, roi, reg_v)
    else:
        C = C_in
    p = finish_probs(C, X)
    p = np.clip(p, 0, None)
    p = p / p.sum()
    formula_roi = p @ reg_v / buyin - 1
    st.session_state.surv_last_C = round(float(C), 6)
    st.session_state.surv_last_roi_pct = round(float(formula_roi) * 100, 2)
    if mode == "ROI":
        calc_slot.metric("C (calculated)", f"{C:.6f}")
    else:
        calc_slot.metric("ROI (calculated)", f"{formula_roi:.2%}")
    st.caption(f"Your C = {C:.6f}, with a counterpart at C = {1 - C:.6f} added to the field.")

    # The other X - 2 players: n_rec recreational players around rec_c, the rest PRO_EDGE higher. rec_c rises with the
    # recreational share so that the average of the whole group is exactly 0.5.
    n_others = X - 2
    n_rec = other_players_split(X, rec_pct)
    rec_c = rec_c_for(X, n_rec)
    other_c = pro_c(X, n_rec, rec_c)
    if n_rec > 0:
        field_slot.metric("Recreational players' C (calculated)", f"{rec_c:.4f}",
                          help="Rises linearly from 0.425 with no recreational players to 0.5 with all of them.")
    if n_rec < n_others:
        field_slot.metric("Other players' C (calculated)", f"{other_c:.4f}",
                          help="Always 0.075 above the recreational players' C.")
    if n_rec > 0:
        st.caption(f"The other {n_others} players: {n_rec} recreational (around C = {rec_c:.3f}) and "
                   f"{n_others - n_rec} around C = {other_c:.4f}.")

    total_tournaments = n_sims * n_tournaments
    entries = total_tournaments * X
    too_slow = entries > MAX_PLAYER_ENTRIES
    st.caption(f"Plays {n_sims:,} runs of {n_tournaments:,} tournaments ({total_tournaments:,} in all).")
    if too_slow:
        st.error(f"Simulations x tournaments per run x players must be {MAX_PLAYER_ENTRIES:,} or fewer. "
                 "Lower one of them.")
    else:
        st.caption(f"{entries:,} player-entries to simulate: roughly {max(1, round(entries / ENTRIES_PER_SECOND))} seconds.")

    # ---------- Run ----------
    if run_slot.button("Run many simulations", type="primary", disabled=too_slow, width="stretch"):
        bar = st.progress(0.0, text=f"0 of {n_sims:,} simulations run")

        def show_progress(done, total):
            """done / total tournaments are finished; a simulation is one run of n_tournaments tournaments."""
            bar.progress(done / total, text=f"{done // n_tournaments:,} of {n_sims:,} simulations run")

        finish = hero_finishes_parallel(X, float(C), total_tournaments, default_workers(),
                                        progress=show_progress, n_rec=n_rec, rec_c=rec_c)
        bar.empty()
        payout = reg_v[finish - 1]
        final = bankroll_paths((payout - buyin).reshape(n_sims, n_tournaments), buyin, start_bankroll)
        st.session_state.many = {
            "c": float(C),
            "field": (f"{n_rec} recreational players around C = {rec_c:.3f} and {n_others - n_rec} around "
                      f"C = {other_c:.4f}" if n_rec else "a single group of players around C = 0.5"),
            "formula_roi": formula_roi,
            "roi": payout.mean() / buyin - 1,
            "std": final[:, -1].std(ddof=1) if n_sims > 1 else 0.0,
            "loss": np.mean(final[:, -1] < start_bankroll),
            "ruin": np.mean(np.minimum(final.min(axis=1), start_bankroll) < buyin),
            "final": final[:, -1],
            "counts": np.bincount(finish, minlength=X + 1)[1:],
        }

    # ---------- Results ----------
    many = st.session_state.many
    if many is None:
        st.info("Press **Run many simulations** to run your simulations.")
        st.stop()

    f = many["final"]
    st.caption(f"Results for C = {many['c']:.6f} (counterpart {1 - many['c']:.6f}), "
               f"{len(f):,} runs of {n_tournaments:,} tournaments. The rest of the field: {many['field']}. "
               f"The finish-probability formula gives an ROI of "
               f"{many['formula_roi']:.2%} for this C; the simulated ROI is in the table below.")
    st.dataframe(
        pd.DataFrame({
            "ROI": [many["roi"]],
            "Std dev": [many["std"]],
            "Probability of loss": [many["loss"]],
            "Risk of ruin": [many["ruin"]],
            "Median bankroll": [np.median(f)],
            "Max bankroll": [f.max()],
            "Min bankroll": [f.min()],
            "Average bankroll": [f.mean()],
        }),
        hide_index=True,
        width="stretch",
        column_config={
            "ROI": st.column_config.NumberColumn(format="percent", help="Average payout / buy-in - 1, over every tournament played"),
            "Std dev": st.column_config.NumberColumn(format="$%.2f", help="Standard deviation of the ending bankroll across runs"),
            "Probability of loss": st.column_config.NumberColumn(format="percent", help="Share of runs ending below the starting bankroll"),
            "Risk of ruin": st.column_config.NumberColumn(format="percent", help="Share of runs where the bankroll dropped below the buy-in"),
            **{c: st.column_config.NumberColumn(format="$%.2f") for c in
               ["Median bankroll", "Max bankroll", "Min bankroll", "Average bankroll"]},
        },
    )
    with st.expander("Probability of finishing in each place", expanded=True):
        probs = many["counts"] / many["counts"].sum()
        st.dataframe(
            pd.DataFrame({
                "Place": np.arange(1, X + 1),
                "Probability": probs * 100,
                "Cumulative (this place or better)": np.cumsum(probs) * 100,
                "Times finished": many["counts"],
                "Payout": reg_v,
            }),
            hide_index=True,
            width="stretch",
            column_config={
                "Probability": st.column_config.NumberColumn(format="%.4f%%"),
                "Cumulative (this place or better)": st.column_config.NumberColumn(format="%.4f%%"),
                "Payout": st.column_config.NumberColumn(format="$%.2f"),
            },
        )
