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
    "sim": {"mode": "ROI", "roi_in": 20.0, "C_in": 0.52},  # Tournament Variance Simulator
    "surv": {"mode": "ROI", "roi_in": 20.0, "C_in": 0.52,                    # Survival Effect Simulator
             "rec_pct": 0.0},
}


def restore_widget_state():
    """Call first on every page, before any widget is created."""
    st.html(  # no - / + buttons on number boxes
        """<style>
        [data-testid="stNumberInputStepUp"], [data-testid="stNumberInputStepDown"] { display: none !important; }
        /* label on the left, a smaller box on the right */
        [data-testid="stNumberInput"], [data-testid="stSelectbox"], [data-testid="stRadio"] {
            display: flex !important; flex-direction: row !important; flex-wrap: wrap !important;
            align-items: center !important;
            justify-content: space-between !important; gap: 0.5rem !important;
        }
        [data-testid="stNumberInput"] > [data-testid="stWidgetLabel"],
        [data-testid="stSelectbox"] > [data-testid="stWidgetLabel"],
        [data-testid="stRadio"] > [data-testid="stWidgetLabel"] {
            flex: 1 1 auto; min-width: 3.5rem; margin-bottom: 0 !important; word-break: normal; overflow-wrap: normal;
        }
        [data-testid="stNumberInput"] > [data-testid="stWidgetLabel"] p,
        [data-testid="stSelectbox"] > [data-testid="stWidgetLabel"] p,
        [data-testid="stRadio"] > [data-testid="stWidgetLabel"] p { font-size: 0.75rem !important; }
        [data-testid="stNumberInput"] > div:not([data-testid="stWidgetLabel"]) { flex: 0 0 5rem; width: 5rem; }
        [data-testid="stSelectbox"] > div:not([data-testid="stWidgetLabel"]) { flex: 0 0 5rem; width: 5rem; }
        [data-testid="stRadio"] label p { font-size: 0.8rem !important; }
        /* hide the "Press Enter to apply" hint inside number boxes */
        [data-testid="InputInstructions"] { display: none !important; }
        /* the whole Variables box is white */
        .st-key-inputs_box { background-color: #ffffff !important; }
        /* plain white input boxes */
        [data-testid="stNumberInputContainer"], [data-testid="stNumberInput"] [data-baseweb="input"],
        [data-testid="stNumberInput"] input, [data-testid="stSelectbox"] [data-baseweb="select"] div,
        [data-testid="stSelectbox"] [data-baseweb="select"] {
            background-color: #ffffff !important;
        }
        [data-testid="stSelectbox"] * { background-color: #ffffff !important; }
        [data-testid="stRadio"] label:has(input:not(:checked)) div { background-color: #ffffff !important; }
        /* radio circles: white, with the selected one marked by a dark dot instead of a colored fill */
        [data-testid="stRadio"] label:has(input:checked) > div > div:first-child { background-color: #ffffff !important; }
        [data-testid="stRadio"] label:has(input:checked) > div > div:first-child > div { background-color: #3a2f25 !important; }
        [data-testid="stRadio"] label:has(input:checked) > div > div:last-child { background-color: transparent !important; }
        /* calculated values: small, with the number to the right of its label */
        [data-testid="stMetric"] { width: 100% !important; min-height: 40px !important; }  /* as tall as an input row */
        [data-testid="stMetric"] > div {
            display: flex !important; flex-direction: row !important; align-items: center !important;
            justify-content: space-between !important; gap: 0.5rem !important; width: 100% !important;
        }
        [data-testid="stMetricLabel"] { flex: 1 1 auto; min-width: 0; }
        [data-testid="stMetricLabel"] * { overflow: visible !important; text-overflow: clip !important; white-space: normal !important; }
        [data-testid="stMetricLabel"] p {
            font-size: 0.72rem !important; white-space: normal !important; overflow: visible !important;
            text-overflow: clip !important; word-break: normal !important; overflow-wrap: normal !important;
        }
        /* same width and inner offset as the number boxes, so the calculated numbers line up with the typed ones */
        [data-testid="stMetricValue"] { flex: 0 0 5rem; width: 5rem; box-sizing: border-box; padding-left: 13px; }
        [data-testid="stMetricValue"] > div { font-size: 0.85rem !important; line-height: 1.4 !important; }
        [data-testid="stRadio"] > div:not([data-testid="stWidgetLabel"]) { flex: 0 0 auto; }
        [data-testid="stNumberInput"] input, [data-testid="stSelectbox"] [data-baseweb="select"] {
            font-size: 0.85rem !important; min-height: 2rem !important;
        }
        </style>"""
    )
    for prefix, extra in PAGE_DEFAULTS.items():
        for key, value in {**BASE_DEFAULTS, **extra}.items():
            full = f"{prefix}_{key}"
            st.session_state.setdefault(full, value)
            st.session_state[full] = st.session_state[full]


def soft_links():
    """Text links with no underline, in a color only slightly different from the body text."""
    st.html(
        """<style>
        [data-testid="stMarkdownContainer"] a {
            text-decoration: none !important;
            color: color-mix(in srgb, currentColor 78%, #9a5b2e 22%) !important;
        }
        </style>"""
    )


def base_inputs(prefix):
    """Players, buy-in, payout structure and starting bankroll. Returns (X, buyin, structure, start_bankroll)."""
    X = st.number_input("Field size", min_value=10, max_value=MAX_PLAYERS, step=1, key=f"{prefix}_players")
    buyin = st.number_input("Buy-in ($)", min_value=0.01, step=1.0, key=f"{prefix}_buyin")
    structure = st.selectbox("Payout structure", list(PAYOUT_STRUCTURES), key=f"{prefix}_structure")
    start_bankroll = st.number_input("Bankroll ($)", min_value=0.0, step=100.0, key=f"{prefix}_bankroll")
    return int(X), buyin, structure, start_bankroll


def run_inputs(prefix):
    """Tournaments per run and number of simulations. Returns (n_tournaments, n_sims)."""
    n_tournaments = st.number_input("Tournaments per run", min_value=1, max_value=10000, step=10,
                                    key=f"{prefix}_n_tournaments")
    n_sims = st.number_input("Simulations", min_value=1, max_value=1000, step=1, key=f"{prefix}_n_sims")
    return int(n_tournaments), int(n_sims)
