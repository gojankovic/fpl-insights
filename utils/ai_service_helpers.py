from utils.ai_transfer_validator import validate_transfer_suggestion


def sanitize_llm_transfer_output(llm_json, squad_state, candidate_pool):
    """
    Ensures LLM output is valid. If invalid, we return an error structure.
    """

    if "suggested_transfers" not in llm_json:
        return {
            "error": "LLM did not return suggested_transfers",
            "raw": llm_json
        }

    suggestions = llm_json["suggested_transfers"]
    if not suggestions:
        return {
            "error": "LLM returned an empty transfer suggestion",
            "raw": llm_json
        }

    sug = suggestions[0]
    ok, reason = validate_transfer_suggestion(squad_state, sug, candidate_pool)

    if not ok:
        return {
            "error": f"Invalid suggestion: {reason}",
            "raw": llm_json
        }

    return {
        "json": llm_json,
        "error": None
    }
