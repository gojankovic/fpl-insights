from predictions.predict_team import predict_team


def test_predict_team_api_advanced(db_available, team_ids, bench_ids, gw, captain_id, vice_id):
    dist = predict_team(
        starting=team_ids,
        gw=gw,
        mode="advanced",
        bench=bench_ids,
        captain_id=captain_id,
        vice_captain_id=vice_id,
        n_sims=1500,
    )
    summary = dist.summary()
    assert summary["expected"] >= 0


def test_predict_team_api_basic(db_available, team_ids, gw):
    dist = predict_team(
        starting=team_ids,
        gw=gw,
        mode="basic",
        n_sims=1500,
    )
    summary = dist.summary()
    assert summary["expected"] >= 0
