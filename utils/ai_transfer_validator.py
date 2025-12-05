def validate_transfer_suggestion(
    squad_state,
    suggestion,
    candidate_pool
):
    """
    Validate a single transfer suggestion coming from the LLM.
    Returns (True, "") if valid, otherwise (False, reason).
    """

    # Extract
    out_id = suggestion.get("out_id")
    in_id = suggestion.get("in_id")

    squad = squad_state["squad"]
    bank = squad_state["bank"]
    club_counts = dict(squad_state["club_counts"])

    # Find outgoing/incoming players
    outgoing = next((p for p in squad if p["id"] == out_id), None)
    incoming = next((p for p in candidate_pool if p["id"] == in_id), None)

    if outgoing is None:
        return False, f"Outgoing player {out_id} not found in squad."

    if incoming is None:
        return False, f"Incoming player {in_id} not found in candidate pool."

    # Cannot buy player already owned
    owned_ids = {p["id"] for p in squad}
    if in_id in owned_ids:
        return False, f"Incoming player {incoming['name']} is already owned."

    # Position constraint
    if outgoing["pos"] != incoming["pos"]:
        return False, f"Position mismatch: {outgoing['pos']} → {incoming['pos']}"

    # Budget check
    if incoming["price"] > outgoing.get("price", 0) + bank:
        return False, (
            f"Budget violation: need {incoming['price']} but only have "
            f"{outgoing.get('price', 0) + bank}"
        )

    # Club limit
    in_team = incoming["team"]
    if in_team:
        if club_counts.get(in_team, 0) >= 3:
            return False, f"Club limit exceeded for {in_team}"

    # Injury/suspension
    if incoming.get("injury"):
        return False, f"Cannot buy injured player {incoming['name']}."

    if incoming.get("suspended"):
        return False, f"Cannot buy suspended player {incoming['name']}."

    # Expected minutes check
    if incoming.get("expected_minutes", 0) < 45:
        return False, f"Incoming player {incoming['name']} has low expected minutes."

    return True, ""
