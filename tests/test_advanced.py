from predictions.team_advanced import predict_team_points_advanced


if __name__ == "__main__":
    starting = [366, 8, 261, 407, 16, 119, 237, 414, 283, 249, 430]  # player ids
    bench = [470, 242, 72, 347]
    gw = 16

    dist = predict_team_points_advanced(
        starting=starting,
        gw=gw,
        captain_id=430,
        vice_captain_id=16,
        bench=bench,
        triple_captain=False,
        bench_boost=False,
    )

    print(dist.summary())
