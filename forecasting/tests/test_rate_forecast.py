import numpy as np
import pandas as pd
import pytest

from forecasting.models import rate_forecast as rf


def make_df(n=60):
    idx = pd.date_range("2019-01-01", periods=n, freq="MS")
    rng = np.random.default_rng(0)
    return pd.DataFrame(
        {
            "system_occupancy_rate": 95 + np.cumsum(rng.normal(0, 0.1, n)),
            "avg_policy_rate": np.linspace(0.25, 4.0, n),
        },
        index=idx,
    )


def test_lag_shorter_than_horizon_is_rejected():
    with pytest.raises(ValueError):
        rf.rolling_origin(make_df(), lag=2, horizon=3)


def test_exog_lag_is_shifted_back():
    df = make_df()
    f = rf.build_frame(df, 6)
    assert f["rate_lag"].iloc[6] == df["avg_policy_rate"].iloc[0]
    assert f["rate_lag"].iloc[:6].isna().all()


def test_folds_never_use_future_targets():
    res = rf.rolling_origin(make_df(), lag=6, horizon=3, min_train=24)
    assert (res["target"] > res["origin"]).all()
    assert set(res["step"]) == {1, 2, 3}


def test_naive_is_last_value_and_pct_change():
    res = rf.rolling_origin(make_df(), lag=6, horizon=3, min_train=24)
    df = make_df()
    first = res.iloc[0]
    assert first["naive"] == pytest.approx(df.loc[first["origin"], "system_occupancy_rate"])
    assert rf.pct_change(1.1, 1.0) == pytest.approx(10.0)
    assert rf.pct_change(0.9, 1.0) == pytest.approx(-10.0)
