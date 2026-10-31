"""Input widgets used by the simulator pages.

Each page has its own copy of every input, told apart by a key prefix ("sim" or "surv"), so the pages do not
share values. Streamlit forgets a widget's value when you leave the page that shows it, so
restore_widget_state() re-stores them at the top of every page, and values survive page switches."""
import streamlit as st

from model import MAX_PLAYERS, PAYOUT_STRUCTURES

BASE_DEFAULTS = {
    "players": 100,
    "buyin": 10.0,
    "structure": "Lodge Card Club",
    "bankroll": 1000.0,
    "n_tournaments": 100,
    "n_sims": 10,
}
PAGE_DEFAULTS = {
    "sim": {"mystery": False, "mode": "ROI", "roi_in": 20.0, "C_in": 0.52},  # Tournament Variance Simulator
    "surv": {"mode": "ROI", "roi_in": 20.0, "C_in": 0.52,                    # Survival Adjusted
             "rec_pct": 0.0},
}


def restore_widget_state():
    """Call first on every page, before any widget is created."""
    for prefix, extra in PAGE_DEFAULTS.items():
        for key, value in {**BASE_DEFAULTS, **extra}.items():
            full = f"{prefix}_{key}"
            st.session_state.setdefault(full, value)
            st.session_state[full] = st.session_state[full]


def base_inputs(prefix):
    """Players, buy-in, payout structure and starting bankroll. Returns (X, buyin, structure, start_bankroll)."""
    X = st.number_input("Number of players", min_value=10, max_value=MAX_PLAYERS, step=1, key=f"{prefix}_players")
    buyin = st.number_input("Buy-in ($)", min_value=0.01, step=1.0, key=f"{prefix}_buyin")
    structure = st.selectbox("Payout structure", list(PAYOUT_STRUCTURES), key=f"{prefix}_structure")
    start_bankroll = st.number_input("Starting bankroll ($)", min_value=0.0, step=100.0, key=f"{prefix}_bankroll")
    return int(X), buyin, structure, start_bankroll


def run_inputs(prefix):
    """Tournaments per run and number of simulations. Returns (n_tournaments, n_sims)."""
    n_tournaments = st.number_input("Tournaments per run", min_value=1, max_value=10000, step=10,
                                    key=f"{prefix}_n_tournaments")
    n_sims = st.number_input("Number of simulations", min_value=1, max_value=1000, step=1, key=f"{prefix}_n_sims")
    return int(n_tournaments), int(n_sims)
