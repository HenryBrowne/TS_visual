import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from xgboost import XGBRegressor

ML_MODEL_FACTORIES = {
    "LightGBM": lambda: LGBMRegressor(n_estimators=100, verbosity=-1),
    "XGBoost": lambda: XGBRegressor(n_estimators=100, verbosity=0),
}


def fit_and_forecast_ml(train: pd.DataFrame, test: pd.DataFrame, feature_cols: list[str]) -> dict[str, np.ndarray]:
    X_train = train[feature_cols].to_numpy(dtype=float)
    y_train = train["value"].to_numpy(dtype=float)
    X_test = test[feature_cols].to_numpy(dtype=float)

    predictions = {}
    for name, factory in ML_MODEL_FACTORIES.items():
        model = factory()
        model.fit(X_train, y_train)
        predictions[name] = model.predict(X_test)
    return predictions
