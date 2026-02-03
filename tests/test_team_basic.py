from predictions.team_basic import predict_team_points


if __name__ == "__main__":
    # test with any 11 players
    sample_team = [366, 8, 261, 407, 16, 119, 237, 414, 283, 249, 430]
    gw = 16

    dist = predict_team_points(sample_team, gw)
    print(dist.summary())
