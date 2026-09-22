import pandas as pd
from statsforecast import StatsForecast
from statsforecast.models import AutoARIMA, AutoETS, Theta

STATS_MODEL_NAMES = {"AutoARIMA": "ARIMA", "AutoETS": "ETS", "Theta": "Theta"}


def fit_and_forecast_stats(train_df: pd.DataFrame, horizon: int, freq: str) -> pd.DataFrame:
    """train_df must have columns unique_id, ds, y.

    Returns a DataFrame with columns unique_id, ds, ARIMA, ETS, Theta.
    """
    sf = StatsForecast(models=[AutoARIMA(), AutoETS(), Theta()], freq=freq, n_jobs=1)
    forecasts = sf.forecast(df=train_df, h=horizon)
    return forecasts.rename(columns=STATS_MODEL_NAMES)
