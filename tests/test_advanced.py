from predictions.team_advanced import predict_team_points_advanced


def test_team_advanced_prediction(db_available, team_ids, bench_ids, gw, captain_id, vice_id):
    dist = predict_team_points_advanced(
        starting=team_ids,
        gw=gw,
        captain_id=captain_id,
        vice_captain_id=vice_id,
        bench=bench_ids,
        triple_captain=False,
        bench_boost=False,
        n_sims=2000,
    )

    summary = dist.summary()
    assert summary["expected"] >= 0
    assert summary["p25"] <= summary["p75"]
