"""Shared model code for the simulator pages (no Streamlit in here).

Finish probabilities (Bill Chen, The Mathematics of Poker), payout structures, mirror mystery bounties,
solving for C from an ROI, and bankroll paths."""
import csv
from functools import lru_cache
from pathlib import Path

import numpy as np

MAX_PLAYER_ENTRIES = 1_000_000_000  # runs x tournaments x players allowed in one "many tournaments" run
ENTRIES_PER_SECOND = 20_000_000     # measured speed with the default number of worker processes, for the time estimate


# ---------- Model (Bill Chen, The Mathematics of Poker) ----------
def finish_probs(C: float, X: int) -> np.ndarray:
    """p_i = C^log2(X/i) - C^log2(X/(i-1)), with the i=1 second term = 0."""
    i = np.arange(1, X + 1)
    upper = C ** np.log2(X / i)
    lower = np.zeros(X)
    lower[1:] = C ** np.log2(X / i[:-1])
    return upper - lower


# ---------- Payout structures ----------
LODGE_CSV = Path(__file__).parent / "lodge_card_club.csv"


@lru_cache(maxsize=None)
def load_lodge_card_club():
    """Read the Lodge Card Club sheet: one column per entrant range.
    Row 1 holds the range ("271-360"), row 2 the number of places paid (informational),
    and rows 3+ the share of the prize pool (in %) paid to 1st, 2nd, 3rd, ...
    Returns a list of (min_entrants, max_entrants, shares as fractions of the pool)."""
    with open(LODGE_CSV, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    tiers = []
    for c in range(1, len(rows[0])):
        lo, hi = (int(s) for s in rows[0][c].split("-"))
        shares = [float(r[c].strip().rstrip("%")) / 100
                  for r in rows[2:] if c < len(r) and r[c].strip()]
        tiers.append((lo, hi, np.array(shares)))
    return tiers


def lodge_card_club_shares(X: int) -> np.ndarray:
    for lo, hi, shares in load_lodge_card_club():
        if lo <= X <= hi:
            return shares
    return None


WSOP_DIR = Path(__file__).parent / "wsop_payouts"


@lru_cache(maxsize=None)
def load_wsop(files):
    """Read WSOP payout calculator exports named wsop_<entries>.csv (columns: Place, Payout).
    Each payout is converted to a share of that file's total payout.
    Returns {entries: shares as fractions of the pool}. `files` is only a cache key."""
    out = {}
    for path, _ in files:
        entries = int(Path(path).stem.split("_")[1])
        payout = []
        with open(path, newline="", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                # "Place" is a single place ("3") or a range ("10 - 13"); the payout is per place
                places = [int(s) for s in r["Place"].split("-")]
                payout += [float(r["Payout"])] * (places[-1] - places[0] + 1)
        out[entries] = np.array(payout) / sum(payout)
    return out


def wsop_shares(X: int) -> np.ndarray:
    """Use the structure of the largest provided entry count that is <= X (None if there is none)."""
    files = tuple(sorted((str(p), p.stat().st_mtime) for p in WSOP_DIR.glob("wsop_*.csv")))
    structures = load_wsop(files)
    eligible = [n for n in structures if n <= X]
    return structures[max(eligible)] if eligible else None


# name -> function returning the share of the pool paid to each place (1st first) for X players
# (or None if the structure has no data for X)
PAYOUT_STRUCTURES = {"Lodge Card Club": lodge_card_club_shares, "WSOP": wsop_shares}
# the largest field either structure has data for (Lodge shows "no payout data" for fields above its own limit)
MAX_PLAYERS = max(max(hi for _, hi, _ in load_lodge_card_club()),
                  max(int(p.stem.split("_")[1]) for p in WSOP_DIR.glob("wsop_*.csv")))


def payouts(X: int, buyin: float, structure: str, mystery: bool):
    """Prize payout per place from the chosen payout structure.

    Mirror mystery bounty: half the pool is paid out as this ladder, the other half
    as n_paid bounties whose dollar values equal the ladder (bounty k = payout k).
    Returns (prize payout per place, n_paid)."""
    pool = X * buyin * (0.5 if mystery else 1.0)
    shares = PAYOUT_STRUCTURES[structure](X)
    n_paid = len(shares)
    v = np.zeros(X)
    v[:n_paid] = pool * shares / shares.sum()
    return v, n_paid


def expected_payouts(v: np.ndarray, n_paid: int, mystery: bool) -> np.ndarray:
    """Expected total payout per finishing place, including expected bounties.

    Bounty assignment: going from last paid place up to 1st, the player in place k
    takes each bounty still available with probability 1/k. A bounty therefore
    reaches a player in place p only if it survived places n_paid..p+1 (probability
    p/n_paid) and is then taken (1/p), i.e. each bounty goes to any given paid
    finisher with probability 1/n_paid, independently of the other bounties and of
    the place. So every paid finisher expects sum(bounties) / n_paid."""
    ev = v.copy()
    if mystery:
        ev[:n_paid] += v[:n_paid].sum() / n_paid
    return ev


def bounty_totals(bounties: np.ndarray, n: int, rng: np.random.Generator) -> np.ndarray:
    """Total bounty money for n paid finishers.

    Each bounty goes to a given finisher independently with probability 1/len(bounties),
    so the number won is Binomial(len, 1/len) and the set is a uniformly random subset."""
    n_b = len(bounties)
    count = rng.binomial(n_b, 1.0 / n_b, size=n)
    total = np.zeros(n)
    for k in range(1, count.max() + 1 if n else 1):
        rows = np.flatnonzero(count == k)
        if len(rows) == 0:
            continue
        pick = rng.integers(0, n_b, size=(len(rows), k))
        while k > 1:  # redraw rows containing a repeated bounty -> uniform distinct subsets
            s = np.sort(pick, axis=1)
            dup = (s[:, 1:] == s[:, :-1]).any(axis=1)
            if not dup.any():
                break
            pick[dup] = rng.integers(0, n_b, size=(int(dup.sum()), k))
        total[rows] = bounties[pick].sum(axis=1)
    return total


def solve_C(X: int, buyin: float, roi: float, v: np.ndarray) -> float:
    """Find C in (0,1) such that sum(p_i * v_i) = buyin * (1 + roi) (bisection)."""
    target = buyin * (1 + roi)
    lo, hi = 1e-12, 1 - 1e-12  # C = 0.5 is average skill; larger C = stronger player
    for _ in range(200):
        mid = (lo + hi) / 2
        ev = float(finish_probs(mid, X) @ v)
        if ev > target:
            hi = mid  # too good -> lower C
        else:
            lo = mid
    return (lo + hi) / 2


def bankroll_paths(net: np.ndarray, buyin: float, start_bankroll: float) -> np.ndarray:
    """Bankroll after each tournament for each run, from per-tournament net results (n_runs, n_tournaments).
    A run stops playing (bankroll stays flat) once it can't cover the buy-in."""
    bankroll = np.empty(net.shape)
    current = np.full(net.shape[0], float(start_bankroll))
    for t in range(net.shape[1]):
        current = current + np.where(current >= buyin, net[:, t], 0.0)
        bankroll[:, t] = current
    return bankroll
