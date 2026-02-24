from utils.ai_service_helpers import sanitize_llm_transfer_output


def _base_state():
    return {
        "free_transfers": 1,
        "allowed_extra": 1,
        "bank": 0.5,
        "club_counts": {"ARS": 2, "LIV": 2, "CHE": 2},
        "squad": [
            {
                "id": 1,
                "name": "A",
                "team": "ARS",
                "pos": "MID",
                "price": 7.0,
                "status": "a",
                "expected_minutes": 85,
                "predicted_points_gw": 6.2,
                "fixture_adjusted_points": 6.5,
            },
            {
                "id": 2,
                "name": "B",
                "team": "LIV",
                "pos": "DEF",
                "price": 5.0,
                "status": "a",
                "expected_minutes": 85,
                "predicted_points_gw": 5.5,
                "fixture_adjusted_points": 5.7,
            },
            {
                "id": 3,
                "name": "C",
                "team": "CHE",
                "pos": "FWD",
                "price": 7.5,
                "status": "a",
                "expected_minutes": 80,
                "predicted_points_gw": 5.1,
                "fixture_adjusted_points": 5.3,
            },
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
            "predicted_points_gw": 7.1,
            "fixture_adjusted_points": 7.4,
        },
        {
            "id": 102,
            "name": "N2",
            "team": "TOT",
            "pos": "DEF",
            "price": 5.1,
            "status": "a",
            "predicted_points_gw": 5.8,
            "fixture_adjusted_points": 6.0,
        },
        {
            "id": 103,
            "name": "N3",
            "team": "WHU",
            "pos": "MID",
            "price": 7.0,
            "status": "a",
            "predicted_points_gw": 5.2,
            "fixture_adjusted_points": 5.4,
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


def test_sanitize_rejects_non_improving_transfer_for_healthy_player():
    llm_json = {
        "gameweek": 25,
        "suggested_transfers": [
            {"out_id": 1, "in_id": 103, "reason": "side move"},
        ],
        "hit_cost": 0,
        "rationale": "not an upgrade",
    }

    result = sanitize_llm_transfer_output(llm_json, _base_state(), _pool())
    assert "incoming projection must improve" in result["error"]


def test_sanitize_allows_non_improving_transfer_for_forced_sell():
    state = _base_state()
    state["squad"][0]["status"] = "i"

    llm_json = {
        "gameweek": 25,
        "suggested_transfers": [
            {"out_id": 1, "in_id": 103, "reason": "injured sell"},
        ],
        "hit_cost": 0,
        "rationale": "forced move",
    }

    result = sanitize_llm_transfer_output(llm_json, state, _pool())
    assert result["error"] is None
