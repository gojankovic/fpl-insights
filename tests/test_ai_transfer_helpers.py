from utils.ai_service_helpers import sanitize_llm_transfer_output


def _base_state():
    return {
        "free_transfers": 1,
        "allowed_extra": 1,
        "bank": 0.5,
        "club_counts": {"ARS": 2, "LIV": 2, "CHE": 2},
        "squad": [
            {"id": 1, "name": "A", "team": "ARS", "pos": "MID", "price": 7.0},
            {"id": 2, "name": "B", "team": "LIV", "pos": "DEF", "price": 5.0},
            {"id": 3, "name": "C", "team": "CHE", "pos": "FWD", "price": 7.5},
        ],
    }


def _pool():
    return [
        {
            "id": 101,
            "name": "N1",
            "team": "MCI",
            "pos": "MID",
            "price": 7.2,
            "status": "a",
        },
        {
            "id": 102,
            "name": "N2",
            "team": "TOT",
            "pos": "DEF",
            "price": 5.1,
            "status": "a",
        },
    ]


def test_sanitize_accepts_valid_multi_transfer_sequence():
    llm_json = {
        "gameweek": 25,
        "suggested_transfers": [
            {"out_id": 1, "in_id": 101, "reason": "upgrade mid"},
            {"out_id": 2, "in_id": 102, "reason": "upgrade def"},
        ],
        "hit_cost": 4,
        "rationale": "Two moves with one free transfer",
    }

    result = sanitize_llm_transfer_output(llm_json, _base_state(), _pool())
    assert result["error"] is None
    assert result["json"]["hit_cost"] == 4


def test_sanitize_rejects_wrong_hit_cost():
    llm_json = {
        "gameweek": 25,
        "suggested_transfers": [
            {"out_id": 1, "in_id": 101, "reason": "upgrade mid"},
            {"out_id": 2, "in_id": 102, "reason": "upgrade def"},
        ],
        "hit_cost": 0,
        "rationale": "incorrect hit math",
    }

    result = sanitize_llm_transfer_output(llm_json, _base_state(), _pool())
    assert "Invalid hit_cost" in result["error"]
