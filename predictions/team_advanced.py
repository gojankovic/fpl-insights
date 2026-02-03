from typing import List, Dict

import numpy as np

from config import DEFAULT_SIMS
from models.monte_carlo import PredictionDistribution
from models.player_model import predict_player_points, get_player_position


def _simulate_with_position_correlation(
    mean: float,
    std: float,
    pos: str,
    n_sims: int,
    shared_noise: Dict[str, np.ndarray],
    pos_corr_weight: Dict[str, float],
) -> np.ndarray:
    if mean <= 0:
        return np.zeros(n_sims)

    corr_w = pos_corr_weight.get(pos, 0.08)
    shared_std = std * corr_w
    idio_std = float(np.sqrt(max(std * std - shared_std * shared_std, 0.0)))

    idio = np.random.normal(loc=mean, scale=idio_std, size=n_sims)
    corr = shared_noise[pos] * shared_std
    return np.clip(idio + corr, 0, None)


def predict_team_points_advanced(
    starting: List[int],
    gw: int,
    captain_id: int | None = None,
    vice_captain_id: int | None = None,
    bench: List[int] | None = None,
    triple_captain: bool = False,
    bench_boost: bool = False,
    n_sims: int | None = None,
) -> PredictionDistribution:
    """
    Advanced team simulation (v1):

    Features:
    - Simulate points for all starting XI
    - Bench players are counted only if bench_boost=True
    - Supports DGW for each player
    - Captain → x2 multiplier
    - Triple captain → x3 multiplier
    - Vice captain replaces captain ONLY if captain has zero points in that simulation
    """

    if n_sims is None:
        n_sims = DEFAULT_SIMS

    # Build the list of all players that contribute points
    all_players = list(starting)
    if bench_boost and bench:
        all_players += list(bench)

    # Precompute shared noise for position-based correlation
    pos_corr_weight = {"GK": 0.15, "DEF": 0.12, "MID": 0.08, "FWD": 0.08}
    shared_noise = {
        "GK": np.random.normal(0, 1, n_sims),
        "DEF": np.random.normal(0, 1, n_sims),
        "MID": np.random.normal(0, 1, n_sims),
        "FWD": np.random.normal(0, 1, n_sims),
    }

    # Simulate every player once
    player_samples: Dict[int, np.ndarray] = {}
    for pid in all_players:
        mean, std = predict_player_points(pid, gw)
        pos = get_player_position(pid)
        samples = _simulate_with_position_correlation(
            mean=mean,
            std=std,
            pos=pos,
            n_sims=n_sims,
            shared_noise=shared_noise,
            pos_corr_weight=pos_corr_weight,
        )
        player_samples[pid] = samples

    # Base sum (all starting players; bench counted only if BB)
    team_samples = np.zeros(n_sims)
    for pid in all_players:
        team_samples += player_samples[pid]

    # Captain / VC logic
    if captain_id is not None and captain_id in player_samples:
        cap_samples = player_samples[captain_id]

        # Default case: captain points
        effective_cap = cap_samples

        if vice_captain_id and vice_captain_id in player_samples:
            vc_samples = player_samples[vice_captain_id]

            # VC replaces captain only if captain has 0 points (means he did not play)
            effective_cap = np.where(cap_samples == 0, vc_samples, cap_samples)

        # Determine multiplier (2x or 3x)
        mult = 3 if triple_captain else 2

        # We already counted cap points once in team_samples,
        # so we add (mult - 1) * effective_cap.
        team_samples += (mult - 1) * effective_cap

    # Build distribution result
    return PredictionDistribution(
        samples=team_samples,
        expected=float(np.mean(team_samples)),
        median=float(np.percentile(team_samples, 50)),
        p25=float(np.percentile(team_samples, 25)),
        p75=float(np.percentile(team_samples, 75)),
        p90=float(np.percentile(team_samples, 90)),
    )
