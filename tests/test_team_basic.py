from predictions.team_basic import predict_team_points


def test_team_basic_prediction(db_available, team_ids, gw):
    dist = predict_team_points(team_ids, gw, n_sims=2000)
    summary = dist.summary()
    assert summary["expected"] >= 0
    assert summary["p25"] <= summary["p75"]
