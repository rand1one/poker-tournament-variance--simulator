"""Tournament Variance Simulator page: describe your skill with ROI or C, then simulate bankroll paths from the formula."""
import random
from urllib.parse import urlencode

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from model import MAX_PLAYERS, PAYOUT_STRUCTURES, bankroll_paths, finish_probs, payouts, solve_C
from shared_ui import base_inputs, restore_widget_state, run_inputs

restore_widget_state()

# "Save results in new tab" opens this page with the inputs and the random seed in the web address. Opening such an
# address fills the inputs and replays the same simulation, so the new tab shows exactly the same results.
LINK_FIELDS = {  # address key -> (input key, converter, lowest, highest)
    "fs": ("sim_players", int, 10, MAX_PLAYERS),
    "bi": ("sim_buyin", float, 0.01, None),
    "bk": ("sim_bankroll", float, 0.0, None),
    "nt": ("sim_n_tournaments", int, 1, 10000),
    "ns": ("sim_n_sims", int, 1, 1000),
    "roi": ("sim_roi_in", float, -99.0, None),
    "c": ("sim_C_in", float, 0.001, 0.999),
}


def apply_saved_link():
    """If the page was opened from a saved-results address, fill the inputs and queue the same simulation."""
    q = st.query_params
    if "seed" not in q or st.session_state.get("link_loaded"):
        return
    st.session_state.link_loaded = True
    try:
        values = {}
        for key, (field, convert, low, high) in LINK_FIELDS.items():
            x = convert(q[key])
            x = max(x, low)
            values[field] = min(x, high) if high is not None else x
        if q["st"] not in PAYOUT_STRUCTURES or q["mode"] not in ("ROI", "C"):
            raise ValueError("unknown structure or mode")
        values["sim_structure"], values["sim_mode"] = q["st"], q["mode"]
        seed = int(q["seed"])
    except (KeyError, ValueError):
        st.query_params.clear()
        return
    st.session_state.update(values)
    st.session_state.auto_seed = seed
    st.query_params.clear()


apply_saved_link()


def carry_over_skill():
    """When the mode is switched, start the new input at the value the old one implied."""
    if "last_C" not in st.session_state:
        return
    if st.session_state.sim_mode == "C":
        st.session_state.sim_C_in = min(max(st.session_state.last_C, 0.001), 0.999)
    else:
        st.session_state.sim_roi_in = max(st.session_state.last_roi_pct, -99.0)


def simulate(p, v, buyin, start_bankroll, n_tournaments, n_sims, seed):
    """Bankroll after each tournament for each run, shape (n_sims, n_tournaments).
    A run stops playing (bankroll stays flat) once it can't cover the buy-in. The same seed gives the same runs."""
    rng = np.random.default_rng(seed)
    cdf = np.cumsum(p)
    cdf[-1] = 1.0
    places = np.searchsorted(cdf, rng.random((n_sims, n_tournaments)))
    winnings = v[places]
    return bankroll_paths(winnings - buyin, buyin, start_bankroll)


# ---------- Inputs ----------
st.title("Poker Tournament Variance Simulator")

inputs_col, output_col = st.columns([1.15, 3], gap="large")
with inputs_col:
    with st.container(border=True, key="inputs_box"):
        X, buyin, structure, start_bankroll = base_inputs("sim")
        mode = st.radio("Skill by", ["ROI", "C"], horizontal=True, key="sim_mode", on_change=carry_over_skill,
                        label_visibility="collapsed")
        st.html(  # a "What's this?" note that shows a tooltip on hover
            """<style>
            .whatsthis { position: relative; display: inline-block; font-size: 0.75rem; color: #7a4a25;
                         cursor: help; border-bottom: 1px dotted #7a4a25; }
            .whatsthis .tip { display: none; position: absolute; left: 0; top: 100%; width: 13rem;
                              background: #3a2f25; color: #ffffff; padding: 0.5rem 0.6rem; font-size: 0.75rem;
                              line-height: 1.35; z-index: 1000; cursor: default; }
            .whatsthis .tip a { color: #ffffff; text-decoration: underline; }
            .whatsthis:hover .tip { display: block; }
            </style>
            <span class="whatsthis">What's this?<span class="tip">Choose ROI or read the
            <a href="/about" target="_self">About</a> page to understand C</span></span>"""
        )
        # ROI is always above C. The one you pick is an input in its row, the other is calculated in its row.
        roi_slot = st.container()
        c_slot = st.container()
        calc_slot = st.container()  # effective tournament size, filled in below once C / ROI have been worked out
        roi_pct = C_in = None
        if mode == "ROI":
            roi_pct = roi_slot.number_input("ROI (%)", min_value=-99.0, step=1.0, format="%.2f", key="sim_roi_in")
        else:
            C_in = c_slot.number_input("C", min_value=0.001, max_value=0.999, step=0.01, format="%.6f", key="sim_C_in")
        n_tournaments, n_sims = run_inputs("sim")
    run_slot = st.container()  # the Run simulation button goes here, below the box

with output_col:
    # ---------- Reset state whenever a variable changes ----------
    params = (X, buyin, structure, start_bankroll, mode, roi_pct, C_in, n_tournaments, n_sims)
    if st.session_state.get("params") != params:
        st.session_state.params = params
        st.session_state.bankrolls = None

    # ---------- Model setup ----------
    if PAYOUT_STRUCTURES[structure](X) is None:
        st.error(f"The {structure} structure has no payout data for {X} players yet.")
        st.stop()
    v, _ = payouts(X, buyin, structure, False)
    if mode == "ROI":
        roi = roi_pct / 100
        max_roi = v[0] / buyin - 1
        if roi >= max_roi:
            st.error(f"ROI must be below {max_roi * 100:.0f}% (the 1st place payout) for these settings.")
            st.stop()
        C = solve_C(X, buyin, roi, v)
    else:
        C = C_in

    p = finish_probs(C, X)
    p = np.clip(p, 0, None)
    p = p / p.sum()
    implied_roi = p @ v / buyin - 1
    st.session_state.last_C = round(float(C), 6)
    st.session_state.last_roi_pct = round(float(implied_roi) * 100, 2)

    if mode == "ROI":
        c_slot.metric("C (calculated)", f"{C:.6f}")
    else:
        roi_slot.metric("ROI (calculated)", f"{implied_roi:.2%}")

    # Effective tournament size k: (2C)^log2(k) = 1 + ROI, so k = 2^(ln(1 + ROI) / ln(2C)).
    # Undefined at C = 0.5 (2C = 1); shown as n/a there.
    if abs(2 * C - 1) < 1e-9 or implied_roi <= -1:
        calc_slot.metric("Effective tournament size", "n/a",
                         help="Solves (2C)^log2(k) = 1 + ROI for k. Undefined when C = 0.5.")
    else:
        eff_size = 2 ** (np.log(1 + implied_roi) / np.log(2 * C))
        calc_slot.metric("Effective tournament size", f"{eff_size:,.1f}",
                         help="Solves (2C)^log2(k) = 1 + ROI for k: the winner-take-all field size that would "
                              "give this C the same ROI.")

    too_big = n_sims * n_tournaments > 250_000
    if too_big:
        st.error("Simulations x tournaments per run must be 250,000 or fewer so the graph stays responsive.")

    clicked = run_slot.button("Run", type="primary", disabled=too_big, width="stretch")
    auto_seed = st.session_state.pop("auto_seed", None)  # set when this page was opened from a saved-results address
    if clicked or (auto_seed is not None and not too_big):
        seed = random.randrange(2**32) if clicked else auto_seed
        st.session_state.sim_seed = seed
        st.session_state.bankrolls = simulate(p, v, buyin, start_bankroll, n_tournaments, n_sims, seed)

    if st.session_state.bankrolls is not None:
        link = "?" + urlencode({
            "fs": X, "bi": buyin, "st": structure, "bk": start_bankroll, "mode": mode,
            "roi": st.session_state.sim_roi_in, "c": st.session_state.sim_C_in,
            "nt": n_tournaments, "ns": n_sims, "seed": st.session_state.sim_seed,
        })
        run_slot.html(
            f'<a href="{link}" target="_blank" rel="noopener" style="color:#7a4a25; text-decoration:underline; '
            f'font-size:0.8rem;">Save results in new tab</a>'
        )

    # ---------- Graph ----------
    bankrolls = st.session_state.bankrolls
    if bankrolls is not None:
        runs, length = bankrolls.shape
        final = bankrolls[:, -1]

        # what the model expects: every tournament played at the expected ROI (ignores runs stopping when broke)
        expected_end = start_bankroll + n_tournaments * buyin * implied_roi

        # Eleven lines for real runs, picked by ranking the runs on their final bankroll: the one that ended
        # lowest (Worst run), the 10th, 20th, ... 90th percentile, and the one that ended highest (Best run).
        # Plus the median bankroll at each tournament, and the expected value (EV) path.
        ranked = np.argsort(final, kind="stable")
        picks = [(0, "Worst run")] + [(q, f"{q}th percentile") for q in range(10, 100, 10)] + [(100, "Best run")]
        run_colors = ["#440154", "#482475", "#414487", "#355f8d", "#2a788e", "#21918c",
                      "#22a884", "#44bf70", "#7ad151", "#bddf26", "#fde725"]  # viridis: Min ... Max
        steps = np.arange(1, length + 1)
        lines = [
            pd.DataFrame({"Tournament": steps, "Line": label,
                          "Bankroll": bankrolls[ranked[int(round(q / 100 * (runs - 1)))]]})
            for q, label in picks
        ]
        lines.append(pd.DataFrame({"Tournament": steps, "Line": "Median bankroll",
                                   "Bankroll": np.median(bankrolls, axis=0)}))
        lines.append(pd.DataFrame({"Tournament": steps, "Line": "Expected value (EV)",
                                   "Bankroll": start_bankroll + steps * buyin * implied_roi}))
        long_df = pd.concat(lines)

        # legend order, top to bottom: Best run, 90th percentile, ... , 10th percentile, Worst run, then the median and EV
        run_labels = [label for _, label in picks]
        key_order = run_labels[::-1] + ["Median bankroll", "Expected value (EV)"]
        colors = dict(zip(run_labels, run_colors)) | {"Median bankroll": "red", "Expected value (EV)": "#ff8c00"}
        widths = {label: 1.8 for label in run_labels} | {"Median bankroll": 3, "Expected value (EV)": 2.5}
        dashes = {label: [1, 0] for label in run_labels} | {"Median bankroll": [1, 0], "Expected value (EV)": [6, 4]}
        chart = (
            alt.Chart(long_df)
            .mark_line()
            .encode(
                x=alt.X("Tournament:Q", title="Tournaments played"),
                y=alt.Y("Bankroll:Q", title="Bankroll ($)"),
                color=alt.Color("Line:N", sort=key_order,
                                scale=alt.Scale(domain=key_order, range=[colors[k] for k in key_order]),
                                legend=alt.Legend(title="Line", symbolType="stroke", symbolStrokeWidth=3)),
                strokeWidth=alt.StrokeWidth("Line:N", legend=None,
                                            scale=alt.Scale(domain=key_order, range=[widths[k] for k in key_order])),
                strokeDash=alt.StrokeDash("Line:N", legend=None,
                                          scale=alt.Scale(domain=key_order, range=[dashes[k] for k in key_order])),
                tooltip=["Line", "Tournament", alt.Tooltip("Bankroll:Q", format="$,.2f")],
            )
            .properties(height=450)
        )
        st.altair_chart(chart, width="stretch")

        st.subheader("Final bankroll distribution")
        if runs < 2 or final.min() == final.max():
            st.caption("Needs at least two simulations that end at different bankrolls to draw a histogram.")
        else:
            # histogram: how many simulations ended in each bankroll range (bin)
            edges = np.histogram_bin_edges(final, bins=int(np.clip(np.sqrt(runs), 5, 60)))
            counts, _ = np.histogram(final, bins=edges)
            hist_df = pd.DataFrame({
                "From": edges[:-1],
                "To": edges[1:],
                "Simulations": counts,
                "Zero": 0,
            })
            dist_chart = (
                alt.Chart(hist_df)
                .mark_bar(stroke="white", strokeWidth=1)
                .encode(
                    x=alt.X("From:Q", title="Ending bankroll ($)"),
                    x2="To:Q",
                    y=alt.Y("Simulations:Q", title="Number of simulations"),
                    y2="Zero:Q",  # each bar is a rectangle from 0 up to its count
                    tooltip=[alt.Tooltip("From:Q", format="$,.0f", title="From"),
                             alt.Tooltip("To:Q", format="$,.0f", title="To"), "Simulations"],
                )
                .properties(height=300)
            )
            st.altair_chart(dist_chart, width="stretch")

        st.subheader("Results")
        q1, q3 = np.percentile(final, [25, 75])

        def with_result(bankroll):
            """'$1,194.46 (+$194.46)': an ending bankroll followed by its profit or loss vs the starting bankroll."""
            gain = bankroll - start_bankroll
            return f"${bankroll:,.2f} ({'+' if gain >= 0 else '-'}${abs(gain):,.2f})"

        # A tournament was played if the bankroll before it could cover the buy-in. Observed ROI is total profit
        # over total buy-ins paid, across every tournament actually played in every run.
        before = np.concatenate([np.full((runs, 1), float(start_bankroll)), bankrolls[:, :-1]], axis=1)
        buyins_paid = (before >= buyin).sum() * buyin
        observed_roi = f"{(final - start_bankroll).sum() / buyins_paid:.2%}" if buyins_paid > 0 else "n/a"

        # One table, one statistic per row. Values are pre-formatted strings because the rows mix dollars and percents.
        rows = {
            "Min": f"${final.min():,.2f}",
            "25th percentile (Q1)": f"${q1:,.2f}",
            "Median": f"${np.median(final):,.2f}",
            "75th percentile (Q3)": f"${q3:,.2f}",
            "Max": f"${final.max():,.2f}",
            "Average (profit/loss)": with_result(final.mean()),
            "Expected result (profit/loss)": with_result(expected_end),
            "Observed ROI": observed_roi,
            "Std dev of ending bankroll": f"${(final.std(ddof=1) if runs > 1 else 0.0):,.2f}",
            "Risk of ruin": f"{np.mean(np.minimum(bankrolls.min(axis=1), start_bankroll) < buyin):.2%}",
            "Likelihood of loss": f"{np.mean(final < start_bankroll):.2%}",
        }
        st.dataframe(
            pd.DataFrame({"Statistic": list(rows), "Value": list(rows.values())}),
            hide_index=True,
            width="content",
            height=(len(rows) + 1) * 35 + 3,  # show every row without a scrollbar
            column_config={
                "Statistic": st.column_config.TextColumn(width=240),
                "Value": st.column_config.TextColumn(width=180),
            },
        )

    # ---------- Finish probability table ----------
    if bankrolls is not None:  # only once a simulation has been run
        with st.expander("Probability of finishing in each place"):
            prob_df = pd.DataFrame({
                "Place": np.arange(1, X + 1),
                "Probability": p * 100,
                "Cumulative (this place or better)": np.cumsum(p) * 100,
                "Payout": v,
            })
            st.dataframe(
                prob_df,
                hide_index=True,
                width="stretch",
                column_config={
                    "Probability": st.column_config.NumberColumn(format="%.4f%%"),
                    "Cumulative (this place or better)": st.column_config.NumberColumn(format="%.4f%%"),
                    "Payout": st.column_config.NumberColumn(format="$%.2f"),
                },
            )
