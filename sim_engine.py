"""Vectorized tournament engine (no Streamlit), kept in its own module so worker processes can import it.

Same rules as the single-tournament simulator in app.py: every player has a C, each round pairs the
remaining players at random, and a battle is a series of flips (both put in the shorter stack,
P(a wins) = 0.5 + (C_a - C_b) / 2) until one player is out."""
import contextlib
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

C_SD = 0.02        # standard deviation of starting Cs
C_STEP = 0.002     # Cs are 0.5 +/- a whole number of steps, i.e. the last digit of 0.xxx is even
START_CHIPS = 1000


def _battle(chips, cs, rows, a, b, rng):
    """One battle for every (tournament, pair) at once: a and b are (T, k) arrays of player ids.
    Same rules as next_round: both put in the shorter stack, flip with P(a) = 0.5 + (C_a - C_b)/2,
    repeat until one player is out. Updates chips; returns (winner ids, loser ids)."""
    ca, cb = chips[rows, a], chips[rows, b]
    p_a = 0.5 + (cs[rows, a] - cs[rows, b]) / 2
    while True:
        active = (ca > 0) & (cb > 0)
        if not active.any():
            break
        stake = np.where(active, np.minimum(ca, cb), 0)
        shift = np.where(rng.random(ca.shape) < p_a, stake, -stake)
        ca, cb = ca + shift, cb - shift
    a_wins = cb == 0
    win, lose = np.where(a_wins, a, b), np.where(a_wins, b, a)
    chips[rows, win] = ca + cb
    chips[rows, lose] = 0
    return win, lose


def other_players_split(n: int, rec_pct: float) -> int:
    """How many of the n - 2 other players (everyone except the hero and the hero's counterpart) are recreational."""
    return int(round((n - 2) * rec_pct / 100))


PRO_EDGE = 0.075  # the non-recreational group's average C is always this much above the recreational group's


def rec_c_for(n: int, n_rec: int) -> float:
    """Recreational players' average C: rises linearly from 0.425 (no recreational players) to 0.5 (all of them).
    With the non-recreational group PRO_EDGE higher, the average C of the n - 2 other players is exactly 0.5."""
    return 0.425 + PRO_EDGE * n_rec / (n - 2)


def pro_c(n: int, n_rec: int, rec_c: float) -> float:
    """The C of the non-recreational group that makes the average C of the n - 2 other players exactly 0.5:
    n_rec * rec_c + n_pro * pro_c = 0.5 * (n - 2). With rec_c from rec_c_for this is rec_c + PRO_EDGE."""
    n_others = n - 2
    if n_rec == n_others:  # nobody is in the non-recreational group
        return rec_c + PRO_EDGE
    return (0.5 * n_others - n_rec * rec_c) / (n_others - n_rec)


def _spread(rng, count: int, size: int) -> np.ndarray:
    """Random C offsets (count, size) in steps of C_STEP, drawn as mirrored +/- pairs (plus a 0 if size is odd),
    so every row averages exactly 0 and a group keeps exactly its centre C as its average."""
    half = size // 2
    e = np.clip(np.round(rng.normal(0, C_SD, (count, half)) / C_STEP), -100, 100) * C_STEP
    return np.concatenate([e, -e, np.zeros((count, size % 2))], axis=1)


def _hero_finishes(n: int, hero_c: float, count: int, rng: np.random.Generator,
                   n_rec: int = 0, rec_c: float = 0.48) -> np.ndarray:
    """Hero's finishing position in `count` independent tournaments of n players.

    Each tournament's field is the hero (C = hero_c), the hero's counterpart (C = 1 - hero_c), and
    n - 2 more players. Of those, n_rec are recreational players spread around rec_c and the rest are
    spread around the C that keeps the average at 0.5 (pro_c); with n_rec = 0 that is a single group
    around 0.5. Each group is spread as in _spread.
    All tournaments have the same number of players left after every round, so they run in lock-step."""
    n_others = n - 2
    others = np.concatenate([
        rec_c + _spread(rng, count, n_rec),
        pro_c(n, n_rec, rec_c) + _spread(rng, count, n_others - n_rec),
    ], axis=1)
    cs = np.concatenate([np.full((count, 1), hero_c), np.full((count, 1), 1 - hero_c), others], axis=1)
    chips = np.full((count, n), START_CHIPS, dtype=np.int64)
    position = np.zeros((count, n), dtype=np.int64)
    alive = np.tile(np.arange(n), (count, 1))            # (count, m): ids of the players still in
    t_idx = np.arange(count)
    rows = t_idx[:, None]
    m = n
    while m > 1:
        order = np.take_along_axis(alive, np.argsort(rng.random((count, m)), axis=1), axis=1)
        pairs = m // 2
        winners, losers = _battle(chips, cs, rows, order[:, 0:2 * pairs:2], order[:, 1:2 * pairs:2], rng)
        position[rows, losers] = (m - np.arange(pairs))[None, :]   # k-th loser of the round finishes (m - k)th
        if m % 2:  # the leftover player battles a random winner of this round
            j = rng.integers(0, pairs, size=count)
            w2, l2 = _battle(chips, cs, rows, order[:, -1:], winners[t_idx, j][:, None], rng)
            position[t_idx, l2[:, 0]] = m - pairs
            winners[t_idx, j] = w2[:, 0]
        alive, m = winners, pairs
    position[t_idx, alive[:, 0]] = 1
    return position[:, 0]  # the hero is player 0


def hero_finishes(n: int, hero_c: float, count: int, rng: np.random.Generator,
                  n_rec: int = 0, rec_c: float = 0.48) -> np.ndarray:
    """_hero_finishes in chunks so the arrays stay a manageable size."""
    chunk = max(1, 1_000_000 // n)
    return np.concatenate([_hero_finishes(n, hero_c, min(chunk, count - s), rng, n_rec, rec_c)
                           for s in range(0, count, chunk)])


def _job(args):
    n, hero_c, count, seed, n_rec, rec_c = args
    return hero_finishes(n, hero_c, count, np.random.default_rng(seed), n_rec, rec_c)


def default_workers() -> int:
    """All logical processors but two, so the computer stays usable while a run is going."""
    return max(1, (os.cpu_count() or 2) - 2)


def hero_finishes_parallel(n, hero_c, count, workers, progress=None, n_rec=0, rec_c=0.48):
    """Hero's finishing positions in `count` tournaments, split across `workers` processes.

    Each job gets its own random stream (SeedSequence.spawn), so results are independent.
    `progress(tournaments_finished, count)` is called as jobs finish. Small runs stay in this process.
    n_rec of the n - 2 other players are recreational, with C around rec_c (see _hero_finishes)."""
    per_job = max(1, 2_000_000 // n)
    sizes = [min(per_job, count - s) for s in range(0, count, per_job)]
    seeds = np.random.SeedSequence().spawn(len(sizes))
    jobs = [(n, hero_c, size, seed, n_rec, rec_c) for size, seed in zip(sizes, seeds)]
    if workers <= 1 or len(jobs) < 2 or n * count < 5_000_000:
        out, finished = [], 0
        for size, job in zip(sizes, jobs):
            out.append(_job(job))
            finished += size
            if progress:
                progress(finished, count)
        return np.concatenate(out)
    results = [None] * len(jobs)
    with _workers_skip_main_script():
        pool = ProcessPoolExecutor(max_workers=workers)
        try:
            futures = {pool.submit(_job, job): k for k, job in enumerate(jobs)}
            finished = 0
            for fut in as_completed(futures):
                results[futures[fut]] = fut.result()
                finished += sizes[futures[fut]]
                if progress:
                    progress(finished, count)
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
    return np.concatenate(results)


@contextlib.contextmanager
def _workers_skip_main_script():
    """On Windows, worker processes re-import the parent's main script. Under Streamlit that script
    is app.py, so every worker would run the whole app page on start-up. Hiding __file__ while the
    workers are started and running stops that; they only need this module."""
    main = sys.modules["__main__"]
    had_file, old_file = hasattr(main, "__file__"), getattr(main, "__file__", None)
    main.__file__ = None
    try:
        yield
    finally:
        if had_file:
            main.__file__ = old_file
        else:
            del main.__file__
