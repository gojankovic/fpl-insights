from typing import Dict, Any, List, Tuple


def _find_in_squad(squad_state: Dict[str, Any], player_id: int) -> Dict[str, Any] | None:
    """
    Find a player dict in current squad by ID.
    """
    for p in squad_state["squad"]:
        if p["id"] == player_id:
            return p
    return None


def _find_in_pool(candidate_pool: List[Dict[str, Any]], player_id: int) -> Dict[str, Any] | None:
    """
    Find a player dict in candidate pool by ID.
    """
    for p in candidate_pool:
        if p["id"] == player_id:
            return p
    return None


def validate_transfer_suggestion(
    squad_state: Dict[str, Any],
    suggestion: Dict[str, Any],
    candidate_pool: List[Dict[str, Any]],
) -> Tuple[bool, str]:
    """
    Validate a single transfer suggestion from the LLM.

    Checks:
    - outgoing player must be in squad
    - incoming player must be in candidate_pool
    - positions must match
    - cannot buy player already owned
    - respect 3-per-club rule after transfer
    - respect budget: out_price + bank >= in_price
    """
    out_id = suggestion.get("out_id")
    in_id = suggestion.get("in_id")

    if out_id is None or in_id is None:
        return False, "out_id or in_id is missing."
    if out_id == in_id:
        return False, "out_id and in_id cannot be the same player."

    out_player = _find_in_squad(squad_state, out_id)
    if out_player is None:
        return False, f"Outgoing player {out_id} is not in squad."

    in_player = _find_in_pool(candidate_pool, in_id)
    if in_player is None:
        return False, f"Incoming player {in_id} not found in candidate pool."

    # Position check
    if out_player.get("pos") != in_player.get("pos"):
        return False, "Positions must match (GK→GK, DEF→DEF, MID→MID, FWD→FWD)."

    # Already owned check
    owned_ids = {p["id"] for p in squad_state["squad"]}
    if in_id in owned_ids:
        return False, "Cannot buy a player that is already owned."

    # 3-per-club rule
    club_counts = dict(squad_state.get("club_counts", {}))
    out_team = out_player.get("team")
    in_team = in_player.get("team")

    new_count = club_counts.get(in_team, 0)
    if in_team == out_team:
        # same club: count unchanged
        pass
    else:
        # remove one from out_team, add one to in_team
        if out_team is not None:
            club_counts[out_team] = max(0, club_counts.get(out_team, 0) - 1)
        club_counts[in_team] = club_counts.get(in_team, 0) + 1
        new_count = club_counts[in_team]

    if new_count > 3:
        return False, f"Transfer breaks 3-per-club rule for {in_team}."

    # Budget check
    bank = float(squad_state.get("bank", 0.0))

    out_price = out_player.get("price")
    in_price = in_player.get("price")

    if out_price is None or in_price is None:
        return False, "Missing price information for players."
    try:
        out_price = float(out_price)
        in_price = float(in_price)
    except (TypeError, ValueError):
        return False, "Invalid numeric values for player prices."

    if in_price > out_price + bank + 1e-6:
        return False, (
            f"Not enough budget: {in_price} > {out_price} + bank({bank})."
        )

    return True, "OK"


def apply_transfer_suggestion(
    squad_state: Dict[str, Any],
    suggestion: Dict[str, Any],
    candidate_pool: List[Dict[str, Any]],
) -> Tuple[bool, str]:
    """
    Apply a previously validated transfer to squad_state in-place.
    This lets callers validate multi-transfer sequences correctly.
    """
    out_id = suggestion.get("out_id")
    in_id = suggestion.get("in_id")

    out_idx = None
    for i, p in enumerate(squad_state["squad"]):
        if p["id"] == out_id:
            out_idx = i
            break
    if out_idx is None:
        return False, f"Outgoing player {out_id} is not in squad."

    out_player = squad_state["squad"][out_idx]
    in_player = _find_in_pool(candidate_pool, in_id)
    if in_player is None:
        return False, f"Incoming player {in_id} not found in candidate pool."

    out_price = float(out_player.get("price", 0.0))
    in_price = float(in_player.get("price", 0.0))
    squad_state["bank"] = float(squad_state.get("bank", 0.0)) + out_price - in_price

    out_team = out_player.get("team")
    in_team = in_player.get("team")
    club_counts = squad_state.setdefault("club_counts", {})
    if out_team is not None:
        club_counts[out_team] = max(0, club_counts.get(out_team, 0) - 1)
    if in_team is not None:
        club_counts[in_team] = club_counts.get(in_team, 0) + 1

    squad_state["squad"][out_idx] = {
        "id": in_player.get("id"),
        "name": in_player.get("name"),
        "team": in_player.get("team"),
        "pos": in_player.get("pos"),
        "price": in_player.get("price"),
        "status": in_player.get("status"),
        "chance_of_playing_next_round": in_player.get("chance_of_playing_next_round"),
        "injury": in_player.get("injury", in_player.get("status") == "i"),
        "suspended": in_player.get("suspended", in_player.get("status") == "s"),
        "rotation_risk": in_player.get("rotation_risk", "unknown"),
        "expected_minutes": in_player.get("expected_minutes", 0),
        "recent_form": in_player.get("recent_form", in_player.get("form_last3", 0.0)),
    }
    return True, "OK"
