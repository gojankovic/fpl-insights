from models.player_model import predict_player_points
from models.monte_carlo import MonteCarlo


def test_player_model_prediction(db_available, player_id, gw):
    mean, std = predict_player_points(player_id, gw)
    assert mean >= 0
    assert std >= 0

    mc = MonteCarlo(n_sims=2000)
    dist = mc.simulate(mean, std)
    summary = dist.summary()
    assert summary["expected"] >= 0
